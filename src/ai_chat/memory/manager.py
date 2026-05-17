"""ConversationMemory — 管理 token 感知的上下文压缩 + 长期摘要的高层编排器。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from langchain_core.messages import BaseMessage, SystemMessage

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.config.settings import settings
from src.ai_chat.llm.model_metadata import get_model_context_size
from src.ai_chat.llm.token_utils import (
    count_text_tokens,
    estimate_message_tokens,
    extract_prompt_tokens,
    extract_total_tokens,
)
from src.ai_chat.memory.factory import memory_factory
from src.ai_chat.memory.models import (
    MemoryConfig,
    MemoryProvider,
    Session,
    message_to_record,
    record_to_message,
)

logger = get_logger(__name__)


# ======================================================================
# 上下文管理数据类
# ======================================================================


@dataclass
class ContextInfo:
    """上下文状态快照，描述当前会话的 token 使用和压缩情况。

    Attributes:
        model_name: 当前关联的模型名称
        context_window: 模型上下文窗口大小（token）
        context_tokens: 当前已使用的 token 数
        threshold_tokens: 压缩触发阈值（token）
        usage_percent: 使用百分比 (0.0~100.0)
        total_messages: 会话总消息数
        recent_messages: 近期窗口内消息数
        has_summary: 是否存在摘要
        summary_length: 摘要文本长度（字符数）
    """

    model_name: Optional[str]
    context_window: int
    context_tokens: int
    threshold_tokens: int
    usage_percent: float
    total_messages: int
    recent_messages: int
    has_summary: bool
    summary_length: int


@dataclass
class ContextMessage:
    """带 token 详情的上下文消息。

    Attributes:
        role: 消息角色（human/ai/system/tool）
        content: 消息文本内容
        token_count: 该消息的 token 数（来自 metadata 或 tiktoken 估算）
    """

    role: str
    content: str
    token_count: int


def memory_config_from_settings() -> MemoryConfig:
    """从全局 Settings 构建 MemoryConfig。"""
    from src.ai_chat.config import settings

    return MemoryConfig(
        backend=settings.memory_backend,
        persist_path=settings.memory_persist_path or None,
        max_short_term_messages=settings.memory_max_short_term_messages,
        summary_model=settings.memory_summary_model or None,
        summary_token_limit=settings.memory_summary_token_limit,
        enable_summary=settings.memory_enable_summary,
    )


def _resolve_backend(backend: str) -> str:
    """解析存储后端名称，未注册时回退到默认值。

    Args:
        backend: 期望的后端名称。

    Returns:
        可用的后端名称。
    """
    if backend and backend in memory_factory._registry:
        return backend
    default = memory_config_from_settings().backend
    if backend:
        logger.warning("存储后端 '%s' 未注册，回退到默认 '%s'", backend, default)
    return default


def _estimate_tokens(
    store: MemoryProvider, session_id: str, config: MemoryConfig
) -> int:
    """估算会话上下文 token 数（共享逻辑）。

    优先级:
    1. LLM 最近一次返回的 prompt_tokens（最精确）
    2. 从消息 metadata["token_count"] 累加，缺失消息用 tiktoken 估算
    """
    session = store.get_session(session_id)
    last_prompt = (session.metadata or {}).get("last_prompt_tokens")
    if last_prompt:
        logger.debug("使用 LLM 报告的 prompt_tokens: %d", last_prompt)
        return last_prompt

    total = 0
    if config.enable_summary:
        summary = store.load_summary(session_id)
        if summary:
            total += count_text_tokens(summary) + 4

    records = store.get_messages(session_id, limit=config.max_short_term_messages)
    for rec in records:
        tc = (rec.metadata or {}).get("token_count")
        if tc:
            total += tc
        else:
            total += estimate_message_tokens(record_to_message(rec))

    logger.debug("估算上下文 token 数: %d (摘要 + %d 条消息)", total, len(records))
    return total


def _build_context_info(
    store: MemoryProvider,
    session_id: str,
    config: MemoryConfig,
    model_name: str | None,
) -> ContextInfo:
    """构建上下文状态快照（共享逻辑）。"""
    context_window = get_model_context_size(model_name) if model_name else 0
    threshold_ratio = settings.model_context_threshold
    threshold_tokens = int(context_window * threshold_ratio)
    context_tokens = _estimate_tokens(store, session_id, config)
    usage_percent = (context_tokens / context_window * 100) if context_window > 0 else 0.0

    total_messages = store.count_messages(session_id)
    recent_messages = min(config.max_short_term_messages, total_messages)
    summary = store.load_summary(session_id)

    return ContextInfo(
        model_name=model_name,
        context_window=context_window,
        context_tokens=context_tokens,
        threshold_tokens=threshold_tokens,
        usage_percent=round(usage_percent, 1),
        total_messages=total_messages,
        recent_messages=recent_messages,
        has_summary=summary is not None,
        summary_length=len(summary) if summary else 0,
    )



class ConversationMemory:
    """单会话的上下文记忆管理器。

    支持 token 感知的上下文压缩：
    - 当传入 model_name 时，根据模型上下文窗口大小和 token 阈值触发压缩
    - 未传入 model_name 时，回退到传统消息条数判断
    - 每条消息的 token 数通过 tiktoken 精确计数并存入 metadata
    - LLM 返回的 prompt_tokens 会被记录为最精确的上下文大小指标

    通过 backend 参数指定存储后端名称，内部通过 memory_factory 创建对应 provider。
    backend 为空或未注册时使用 settings.memory_backend 默认值。

    Usage::

        memory = ConversationMemory(model_name="gpt-4o")
        memory = ConversationMemory(backend="in_memory")
        history = memory.load_history()
        memory.save_interaction(human_msg, ai_msg, token_usage=response.usage)
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        config: Optional[MemoryConfig] = None,
        *,
        backend: str = "",
        model_name: Optional[str] = None,
    ) -> None:
        self._model_name = model_name
        self._config = config or memory_config_from_settings()
        backend_name = _resolve_backend(backend or self._config.backend)
        self._store: MemoryProvider = memory_factory.create(backend_name, self._config)
        if session_id:
            try:
                self._session = self._store.get_session(session_id)
            except Exception:
                self._session = self._store.create_session(session_id)
        else:
            self._session = self._store.create_session()

        if model_name:
            logger.debug("ConversationMemory 初始化: session=%s, model=%s", self.session_id[:8], model_name)

    @property
    def session_id(self) -> str:
        return self._session.session_id

    @property
    def session(self) -> Session:
        return self._session

    def load_history(self) -> list[BaseMessage]:
        """加载 LLM 上下文：[摘要 SystemMessage?] + 最近 N 条消息。"""
        messages: list[BaseMessage] = []

        if self._config.enable_summary:
            summary = self._store.load_summary(self.session_id)
            if summary:
                messages.append(
                    SystemMessage(content=f"之前的对话摘要：\n{summary}")
                )

        total = self._store.count_messages(self.session_id)
        limit = min(self._config.max_short_term_messages, total)
        offset = total - limit if total > self._config.max_short_term_messages else 0
        records = self._store.get_messages(self.session_id, limit=limit, offset=offset)
        for rec in records:
            messages.append(record_to_message(rec))

        logger.debug("加载历史: session=%s, 摘要=%s, 消息数=%d, 总记录=%d",
                     self.session_id[:8], "有" if messages and isinstance(messages[0], SystemMessage) else "无",
                     len(messages), total)
        return messages

    def save_interaction(
        self,
        human_message: BaseMessage,
        ai_message: BaseMessage,
        *,
        token_usage: Optional[dict] = None,
    ) -> None:
        """持久化一轮对话并触发 token 感知的压缩检查。

        Args:
            human_message: 用户消息
            ai_message: AI 响应消息
            token_usage: LLM 返回的 usage 字典（含 prompt_tokens/completion_tokens），
                         用于精确记录 token 消耗
        """
        # 用 tiktoken 估算每条消息的 token 数
        human_tokens = estimate_message_tokens(human_message)

        # AI 消息优先使用 LLM 返回的 completion token 数，否则用 tiktoken 估算
        ai_tokens = extract_total_tokens(token_usage)
        if ai_tokens is not None:
            # total_tokens 包含 prompt + completion，取 completion 部分更精确
            completion = token_usage.get("completion_tokens") or token_usage.get("output_tokens")
            if completion is not None:
                ai_tokens = completion
        else:
            ai_tokens = estimate_message_tokens(ai_message)

        # 记录 LLM 返回的 prompt_tokens（最精确的上下文大小指标）
        prompt_tokens = extract_prompt_tokens(token_usage)
        if prompt_tokens is not None:
            self._store.update_session_metadata(
                self.session_id, {"last_prompt_tokens": prompt_tokens}
            )

        self._store.add_message(
            message_to_record(human_message, self.session_id, token_count=human_tokens)
        )
        self._store.add_message(
            message_to_record(ai_message, self.session_id, token_count=ai_tokens)
        )
        self._store.update_session_timestamp(self.session_id)

        logger.info("保存对话: session=%s, human_tokens=%d, ai_tokens=%d, prompt_tokens=%s",
                     self.session_id[:8], human_tokens, ai_tokens, prompt_tokens)

        if self._config.enable_summary:
            self._maybe_summarize()

    def save_message(self, message: BaseMessage, *, token_count: Optional[int] = None) -> None:
        """持久化单条消息。

        Args:
            message: 消息对象
            token_count: 可选的 token 数，不提供时用 tiktoken 估算
        """
        if token_count is None:
            token_count = estimate_message_tokens(message)
        self._store.add_message(
            message_to_record(message, self.session_id, token_count=token_count)
        )
        self._store.update_session_timestamp(self.session_id)

    def clear(self) -> None:
        """删除当前会话及所有数据。"""
        self._store.delete_session(self.session_id)

    def get_message_count(self) -> int:
        return self._store.count_messages(self.session_id)

    def get_summary(self) -> Optional[str]:
        return self._store.load_summary(self.session_id)

    # ── 上下文管理 API ──────────────────────────────────

    def get_context_info(self) -> ContextInfo:
        """返回当前上下文的完整状态快照。

        包含 token 使用量、模型窗口大小、压缩阈值、消息统计等信息，
        供上层调用方（Web UI、Agent 等）展示上下文状态。
        """
        return _build_context_info(self._store, self.session_id, self._config, self._model_name)

    def force_compress(self) -> Optional[str]:
        """手动触发上下文压缩（忽略阈值检查）。

        立即对超出短期窗口的旧消息生成摘要，追加到已有摘要中。
        即使当前 token 数未达阈值也会执行。

        Returns:
            生成的摘要文本，无旧消息可压缩时返回 None
        """
        total = self._store.count_messages(self.session_id)
        if total <= self._config.max_short_term_messages:
            logger.info("手动压缩: 消息数(%d)未超出窗口(%d)，无需压缩", total, self._config.max_short_term_messages)
            return None

        overflow_count = total - self._config.max_short_term_messages
        old_records = self._store.get_messages(
            self.session_id, limit=overflow_count, offset=0
        )
        old_messages = [record_to_message(r) for r in old_records]
        summary = self._generate_summary(old_messages)
        if summary:
            existing = self._store.load_summary(self.session_id) or ""
            combined = f"{existing}\n\n---\n\n{summary}" if existing else summary
            self._store.save_summary(self.session_id, combined)
            logger.info("手动压缩完成: 压缩 %d 条旧消息，摘要长度=%d", overflow_count, len(summary))
        return summary

    def set_model(self, model_name: str) -> None:
        """动态切换关联的模型名称。

        影响上下文窗口大小和压缩阈值的计算。下次 _maybe_summarize
        和 get_context_info 调用时将使用新模型。
        """
        old_model = self._model_name
        self._model_name = model_name
        logger.info("切换模型: %s -> %s", old_model, model_name)

    def get_context_messages(self) -> list[ContextMessage]:
        """返回带 token 详情的上下文消息列表。

        包含摘要（如有）和近期窗口内的消息，每条消息附带 token 数。
        用于展示上下文详情或调试。
        """
        result: list[ContextMessage] = []

        # 摘要作为 system 消息
        if self._config.enable_summary:
            summary = self._store.load_summary(self.session_id)
            if summary:
                result.append(ContextMessage(
                    role="system",
                    content=summary,
                    token_count=count_text_tokens(summary) + 4,
                ))

        # 近期消息
        total = self._store.count_messages(self.session_id)
        limit = min(self._config.max_short_term_messages, total)
        offset = total - limit if total > self._config.max_short_term_messages else 0
        records = self._store.get_messages(self.session_id, limit=limit, offset=offset)
        for rec in records:
            tc = (rec.metadata or {}).get("token_count")
            if tc is None:
                tc = estimate_message_tokens(record_to_message(rec))
            result.append(ContextMessage(
                role=rec.role,
                content=rec.content,
                token_count=tc,
            ))

        return result

    def reset_context(self) -> None:
        """清除会话的所有消息和摘要，但保留会话本身。

        与 clear() 不同：clear() 删除整个会话，reset_context() 只清空内容。
        重置后 session_id 不变，可以继续使用。
        """
        self._store.reset_context(self.session_id)
        logger.info("重置上下文: session=%s，消息和摘要已清空，会话保留", self.session_id[:8])

    def trim_messages(self, keep_count: int) -> int:
        """手动裁剪旧消息，只保留最近 keep_count 条。

        被删除的消息不会被摘要，直接丢弃。如需保留信息，应先调用
        force_compress() 再 trim_messages()。

        Args:
            keep_count: 保留的最近消息条数

        Returns:
            被删除的消息数量
        """
        deleted = self._store.delete_messages_before(self.session_id, keep_count)
        logger.info("裁剪消息: session=%s, 保留 %d 条, 删除 %d 条",
                     self.session_id[:8], keep_count, deleted)
        return deleted

    def _estimate_context_tokens(self) -> int:
        """估算当前上下文的总 token 数。"""
        return _estimate_tokens(self._store, self.session_id, self._config)

    def _maybe_summarize(self) -> None:
        """当上下文 token 数超过模型阈值的 80% 时触发压缩。

        有 model_name 时使用 token 感知路径；否则回退到传统消息条数判断。
        """
        if self._model_name:
            # token 感知路径
            context_tokens = self._estimate_context_tokens()

            limit = get_model_context_size(self._model_name)
            threshold = int(limit * settings.model_context_threshold)

            if context_tokens < threshold:
                logger.debug("上下文未达阈值: %d/%d (%.0f%%)",
                             context_tokens, limit, context_tokens / limit * 100)
                return

            logger.info(
                "上下文 token 数(%d)超过模型 '%s' 阈值(%d, %.0f%%)，触发压缩",
                context_tokens, self._model_name, threshold,
                settings.model_context_threshold * 100,
            )
        else:
            # 回退：传统消息条数判断
            total = self._store.count_messages(self.session_id)
            threshold_count = self._config.max_short_term_messages * 2
            if total < threshold_count:
                return

        # 压缩逻辑：对超出窗口的旧消息生成摘要
        total = self._store.count_messages(self.session_id)
        overflow_count = max(
            total - self._config.max_short_term_messages,
            total // 2,  # token 触发时至少压缩一半
        )
        old_records = self._store.get_messages(
            self.session_id, limit=overflow_count, offset=0
        )
        old_messages = [record_to_message(r) for r in old_records]
        summary = self._generate_summary(old_messages)
        if summary:
            existing = self._store.load_summary(self.session_id) or ""
            combined = f"{existing}\n\n---\n\n{summary}" if existing else summary
            self._store.save_summary(self.session_id, combined)
            logger.info("压缩完成: 压缩 %d 条旧消息，摘要长度=%d", overflow_count, len(summary))

    def _generate_summary(self, messages: list[BaseMessage]) -> Optional[str]:
        """通过 ConversationSummaryChain 生成对话摘要。"""
        from src.ai_chat.chains.summary_chain import ConversationSummaryChain

        chain = ConversationSummaryChain(
            model_name=self._config.summary_model,
            token_limit=self._config.summary_token_limit,
        )
        return chain.invoke(messages)


# ======================================================================
# 多会话管理
# ======================================================================


@dataclass
class SessionDetail:
    """会话详情 — 包含消息统计和摘要状态。

    用于列表展示和详情页，避免上层 N+1 查询。

    Attributes:
        session_id: 会话唯一标识
        title: 会话标题
        created_at: 创建时间
        updated_at: 最后更新时间
        message_count: 会话中的消息总数
        has_summary: 是否存在长期摘要
        model_name: 关联的模型名称（从 session metadata 读取）
        last_prompt_tokens: 最近一次 LLM 调用的 prompt_tokens
    """

    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    has_summary: bool = False
    model_name: Optional[str] = None
    last_prompt_tokens: Optional[int] = None


class SessionManager:
    """多会话管理器 — 封装 MemoryProvider 提供会话列表、搜索、批量操作。

    与 ConversationMemory（单会话）互补，SessionManager 负责跨会话的高层操作，
    无需为每个会话创建独立的 ConversationMemory 实例。

    通过 backend 参数指定存储后端名称，内部通过 memory_factory 创建对应 provider。
    backend 为空或未注册时使用 settings.memory_backend 默认值。

    Usage::

        mgr = SessionManager()
        mgr = SessionManager(backend="in_memory")
        sessions = mgr.list_sessions(limit=10)
    """

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        *,
        backend: str = "",
    ) -> None:
        self._config = config or memory_config_from_settings()
        backend_name = _resolve_backend(backend or self._config.backend)
        self._store: MemoryProvider = memory_factory.create(backend_name, self._config)
        logger.debug("SessionManager 初始化: backend=%s", backend_name)

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[SessionDetail]:
        """列出会话，附带消息统计和摘要状态。

        按 updated_at 降序排列，支持分页。
        使用批量查询避免 N+1 问题。
        """
        sessions = self._store.list_sessions(limit=limit, offset=offset)
        details = self._build_details_batch(sessions)
        logger.debug("列出会话: %d 条 (offset=%d)", len(details), offset)
        return details

    def count_sessions(self) -> int:
        """返回会话总数。"""
        return self._store.count_sessions()

    def search_sessions(
        self, keyword: str, limit: int = 50, offset: int = 0
    ) -> list[SessionDetail]:
        """按标题关键词模糊搜索会话。"""
        sessions = self._store.search_sessions(keyword, limit=limit, offset=offset)
        details = self._build_details_batch(sessions)
        logger.debug("搜索 '%s': %d 条结果", keyword, len(details))
        return details

    def get_session_detail(self, session_id: str) -> SessionDetail:
        """获取单个会话的完整详情。

        Raises:
            SessionNotFoundException: 会话不存在时
        """
        session = self._store.get_session(session_id)
        detail = self._build_details_batch([session])[0]
        logger.debug("获取会话详情: %s", session_id[:8])
        return detail

    def rename_session(self, session_id: str, title: str) -> None:
        """重命名会话标题。"""
        self._store.update_session_title(session_id, title)
        logger.info("重命名会话: %s -> '%s'", session_id[:8], title)

    def delete_session(self, session_id: str) -> None:
        """删除单个会话及其所有数据。"""
        self._store.delete_session(session_id)
        logger.info("删除会话: %s", session_id[:8])

    def delete_sessions(self, session_ids: list[str]) -> int:
        """批量删除会话，返回实际删除的数量。"""
        deleted = 0
        for sid in session_ids:
            try:
                self._store.delete_session(sid)
                deleted += 1
            except Exception as e:
                logger.warning("删除会话失败: %s, 原因: %s", sid[:8], e)
        logger.info("批量删除: %d/%d 个会话", deleted, len(session_ids))
        return deleted

    def get_session_context_info(
        self, session_id: str, model_name: Optional[str] = None
    ) -> ContextInfo:
        """获取会话的上下文状态快照，无需创建 ConversationMemory。"""
        return _build_context_info(self._store, session_id, self._config, model_name)

    def reset_session(self, session_id: str) -> None:
        """清空会话的所有消息和摘要，但保留会话本身。"""
        self._store.reset_context(session_id)
        logger.info("重置会话: %s，消息和摘要已清空", session_id[:8])

    def _build_details_batch(self, sessions: list[Session]) -> list[SessionDetail]:
        """批量构建 SessionDetail，使用批量查询避免 N+1 问题。"""
        if not sessions:
            return []
        ids = [s.session_id for s in sessions]
        counts = self._store.batch_count_messages(ids)
        summaries = self._store.batch_has_summaries(ids)
        details: list[SessionDetail] = []
        for s in sessions:
            metadata = s.metadata or {}
            details.append(SessionDetail(
                session_id=s.session_id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=counts.get(s.session_id, 0),
                has_summary=summaries.get(s.session_id, False),
                model_name=metadata.get("model_name"),
                last_prompt_tokens=metadata.get("last_prompt_tokens"),
            ))
        return details

