"""上下文压缩 — 微压缩（工具结果清理）和全量/增量压缩（LLM 摘要）。"""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

from src.ai.utils.llm_utils import build_llm_chain

logger = logging.getLogger(__name__)

# ── 模块级函数（无状态，纯函数） ─────────────────────────────────


def extract_message_content(msg: Any) -> str:
    """提取消息文本内容。

    Args:
        msg: LangChain BaseMessage 或兼容对象。

    Returns:
        消息的纯文本内容。
    """
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [item.get("text", "") for item in content if isinstance(item, dict)]
        return " ".join(texts)
    return str(content)


def format_messages_to_text(messages: list[Any]) -> str:
    """将消息列表格式化为对话文本。

    Args:
        messages: 消息列表（LangChain BaseMessage 或兼容对象）。

    Returns:
        格式化的对话文本，每行格式为 [消息#N] type: content。
    """
    lines = []
    for i, msg in enumerate(messages):
        msg_type = getattr(msg, "type", "unknown")
        content = extract_message_content(msg)
        lines.append(f"[消息#{i}] {msg_type}: {content}")
    return "\n".join(lines)


# 标准摘要章节列表
STANDARD_SECTIONS: list[str] = [
    "Primary Request and Intent",
    "Key Concepts and Ideas",
    "Files and Code Sections",
    "Errors and Fixes",
    "Problem Solving",
    "Important User Messages",
    "Pending Tasks and TODOs",
    "Current Work",
    "Next Step",
]


def validate_summary_sections(summary: str) -> dict[str, bool]:
    """验证摘要是否包含所有标准章节。

    Args:
        summary: 摘要文本。

    Returns:
        各章节是否存在映射。
    """
    return {section: f"## {section}" in summary for section in STANDARD_SECTIONS}


class MicroCompact:
    """微压缩 — 轻量级工具结果清理，无需 LLM。

    从最旧的消息开始，将工具调用结果替换为 [已清理]，
    保留最近 keep_recent 个工具结果不清理。
    同时截断过长的工具结果。
    """

    def __init__(self, keep_recent: int = 4, max_tool_result_chars: int = 4000) -> None:
        self._keep_recent = keep_recent
        self._max_tool_result_chars = max_tool_result_chars

    def compact(self, messages: list[Any]) -> list[Any]:
        """执行微压缩，返回新消息列表（不修改原列表）。

        Args:
            messages: 消息列表（LangChain BaseMessage 或兼容对象）。

        Returns:
            清理后的新消息列表。
        """
        if not messages:
            return messages

        tool_indices = [
            i for i, msg in enumerate(messages) if self._is_tool_result(msg)
        ]

        if len(tool_indices) <= self._keep_recent:
            return messages

        to_clean = tool_indices[: len(tool_indices) - self._keep_recent]

        result = list(messages)
        for idx in to_clean:
            result[idx] = self._clean_message(messages[idx])

        cleaned = len(to_clean)
        if cleaned > 0:
            logger.debug("微压缩：清理了 %d 个工具结果", cleaned)

        result = self._truncate_large_tools(result)

        return result

    @staticmethod
    def _is_tool_result(msg: Any) -> bool:
        """判断消息是否为工具调用结果。"""
        msg_type = getattr(msg, "type", "")
        if msg_type == "tool":
            return True
        if msg_type == "tool" or hasattr(msg, "tool_call_id"):
            return True
        return False

    @staticmethod
    def _clean_message(msg: Any) -> Any:
        """将工具结果消息内容替换为 [已清理]。"""
        from copy import copy

        new_msg = copy(msg)
        if isinstance(new_msg.content, str):
            new_msg.content = "[已清理]"
        elif isinstance(new_msg.content, list):
            new_msg.content = [{"type": "text", "text": "[已清理]"}]
        return new_msg

    def _truncate_large_tools(self, messages: list[Any]) -> list[Any]:
        """截断过长的工具结果。"""
        from copy import copy

        result = list(messages)
        truncated_count = 0

        for i, msg in enumerate(result):
            if not self._is_tool_result(msg):
                continue

            content = getattr(msg, "content", "")
            if isinstance(content, str) and len(content) > self._max_tool_result_chars:
                new_msg = copy(msg)
                new_msg.content = (
                    content[: self._max_tool_result_chars]
                    + f"\n...(已截断，原始长度 {len(content)} 字符)"
                )
                result[i] = new_msg
                truncated_count += 1
            elif isinstance(content, list):
                for j, item in enumerate(content):
                    if isinstance(item, dict) and "text" in item:
                        text = item["text"]
                        if len(text) > self._max_tool_result_chars:
                            new_msg = copy(msg)
                            new_content = list(content)
                            new_content[j] = {
                                **item,
                                "text": text[: self._max_tool_result_chars]
                                + f"\n...(已截断，原始长度 {len(text)} 字符)",
                            }
                            new_msg.content = new_content
                            result[i] = new_msg
                            truncated_count += 1
                            break

        if truncated_count > 0:
            logger.debug("微压缩：截断了 %d 个过长工具结果", truncated_count)

        return result


class FullCompact:
    """对话压缩器 — 支持全量和增量两种模式。

    - 全量压缩（compact_full）：9 章节标准结构
    - 增量压缩（compact_incremental）：将新增消息合并到已有摘要

    Args:
        llm: 用于压缩的 LLM 实例。
        prompt_service: 提示词服务（从 DB 获取提示词模板）。
        keep_recent: 保留最近的消息数量（默认 10）。
    """

    # 向后兼容：引用模块级常量
    STANDARD_SECTIONS: list[str] = STANDARD_SECTIONS

    def __init__(
        self, llm: BaseChatModel, prompt_service: object, keep_recent: int = 10
    ) -> None:
        self._llm = llm
        self._keep_recent = keep_recent

        base = self._get_template(prompt_service, "memory.compress_base")
        if not base:
            from src.ai.exception.prompt_exception import PromptNotFoundError

            raise PromptNotFoundError(
                "DB 中未找到 memory.compress_base 模板",
                context={"missing": ["memory.compress_base"]},
            )

        full_fmt = self._get_template(prompt_service, "memory.full_compress_format")
        if not full_fmt:
            from src.ai.exception.prompt_exception import PromptNotFoundError

            raise PromptNotFoundError(
                "DB 中未找到 memory.full_compress_format 模板",
                context={"missing": ["memory.full_compress_format"]},
            )

        incr_fmt = self._get_template(
            prompt_service, "memory.compress_incremental_format"
        )
        if not incr_fmt:
            from src.ai.exception.prompt_exception import PromptNotFoundError

            raise PromptNotFoundError(
                "DB 中未找到 memory.compress_incremental_format 模板",
                context={"missing": ["memory.compress_incremental_format"]},
            )

        self._full_chain = build_llm_chain(self._llm, base + "\n" + full_fmt, "{input}")
        self._incremental_chain = build_llm_chain(
            self._llm, base + "\n" + incr_fmt, "{input}"
        )

    # ── 全量压缩 ──────────────────────────────────────────

    async def compact_full(
        self,
        messages: list[Any],
        existing_summary: str = "",
    ) -> tuple[str, list[dict[str, Any]]]:
        """全量压缩：9 章节标准结构。

        Args:
            messages: 待压缩的消息列表（LangChain BaseMessage）。
            existing_summary: 已有的摘要文本（增量压缩时传入）。

        Returns:
            (summary_text, file_references) — 摘要文本和文件引用列表。
        """
        if not messages:
            return existing_summary, []

        conversation_text = format_messages_to_text(messages)
        input_text = self._build_input(conversation_text, existing_summary)

        try:
            summary = await self._full_chain.ainvoke({"input": input_text})
            file_refs = [
                {
                    "index": i,
                    "type": getattr(msg, "type", "unknown"),
                    "snippet": extract_message_content(msg)[:80],
                }
                for i, msg in enumerate(messages)
            ]
            return summary, file_refs
        except Exception:
            logger.warning("全量压缩失败", exc_info=True)
            return existing_summary, []

    # ── 增量压缩 ──────────────────────────────────────────

    async def compact_incremental(
        self,
        records: list[dict[str, Any]],
        existing_summary: str = "",
    ) -> str:
        """增量压缩：将新增消息合并到已有摘要。

        Args:
            records: 待压缩的消息记录列表（FileHistoryStore 格式）。
            existing_summary: 已有的摘要文本。

        Returns:
            合并后的摘要文本。
        """
        if not records:
            return existing_summary

        conversation_lines = []
        for r in records:
            idx = r.get("index", 0)
            content = r.get("content", "")
            conversation_lines.append(f"[消息#{idx}] {r['type']}: {content}")
        conversation_text = "\n".join(conversation_lines)

        input_text = self._build_input(conversation_text, existing_summary)

        try:
            return await self._incremental_chain.ainvoke({"input": input_text})
        except Exception:
            logger.warning("增量压缩失败", exc_info=True)
            return existing_summary

    # ── 内部方法 ──────────────────────────────────────────

    @staticmethod
    def _build_input(conversation_text: str, existing_summary: str) -> str:
        """构建 LLM 输入文本。"""
        if existing_summary:
            return (
                "# 任务：增量摘要合并\n\n"
                "## 已有摘要\n"
                f"{existing_summary}\n\n"
                "## 新增对话内容\n"
                f"{conversation_text}\n\n"
                "## 要求\n"
                "1. 将新增内容与已有摘要合并\n"
                "2. 保留已有摘要中的有效信息和来源标注\n"
                "3. 为新增内容添加来源标注 [消息#编号]\n"
                "4. 去除重复信息，保留最新版本\n"
                "5. 按照系统提示的格式输出"
            )
        return (
            "# 任务：对话压缩\n\n"
            "## 待压缩对话内容\n"
            f"{conversation_text}\n\n"
            "## 要求\n"
            "1. 按照系统提示的格式输出结构化摘要\n"
            "2. 为每条关键信息标注来源 [消息#编号]\n"
            "3. 压缩率目标：保留 20-30% 的关键内容"
        )

    @staticmethod
    def _format_messages(messages: list[Any]) -> str:
        """将消息列表格式化为对话文本。"""
        return format_messages_to_text(messages)

    @staticmethod
    def _extract_content(msg: Any) -> str:
        """提取消息文本内容。"""
        return extract_message_content(msg)

    @staticmethod
    def _get_template(prompt_service: object, prompt_key: str) -> str:
        """从 prompt_service 获取模板原始内容。"""
        template = prompt_service.get_template(prompt_key)  # type: ignore[attr-defined]
        if template is None:
            return ""
        return template.template

    @classmethod
    def validate_sections(cls, summary: str) -> dict[str, bool]:
        """验证摘要是否包含所有标准章节。"""
        return validate_summary_sections(summary)
