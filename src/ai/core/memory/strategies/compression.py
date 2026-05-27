"""压缩策略 — 使用 LLM 压缩旧对话，生成文件位置引用。"""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage

from src.ai.core.memory.history import ChatHistoryManager
from src.ai.core.memory.history_store import FileHistoryStore
from src.ai.core.memory.llm_utils import build_llm_chain
from src.ai.utils.obj import Obj
from .base import BaseMemoryStrategy

logger = logging.getLogger(__name__)

_COMPRESS_SYSTEM = """你是一个专业的对话分析与压缩专家。你的任务是将对话历史压缩为结构化摘要，同时保留关键信息的可追溯性。

## 核心原则

1. **信息保真**：绝不捏造、推测或概括不存在的内容
2. **来源可追溯**：每条关键信息必须标注来源 [消息#编号]
3. **结构清晰**：使用分类组织信息，便于快速检索

## 必须保留的信息类型

- **决策与结论**：达成的共识、选择的方案、最终决定
- **技术细节**：代码位置、配置参数、API 端点、错误信息
- **待办事项**：未完成的任务、承诺的后续动作
- **关键数据**：数值、ID、路径、名称等具体信息
- **问题与解决方案**：遇到的问题及对应的解决方法

## 可以省略的信息

- 礼貌性对话（问候、感谢）
- 重复或冗余的表述
- 已被后续消息否定或更新的旧信息
- 过于细节的推理过程（只保留结论）

## 输出格式

```
## 主题
[一句话概括对话主题]

## 关键决策
- 决策内容 [消息#编号]

## 技术细节
- 具体细节 [消息#编号]

## 待办事项
- 任务描述 [消息#编号]

## 重要上下文
- 背景信息 [消息#编号]
```

## 规则

- 使用中文输出
- 每个标注必须是实际存在的消息编号
- 如果信息不足以分类，放入"重要上下文"
- 不要添加任何开场白或结束语
- 直接输出结构化内容"""


class CompressionStrategy(BaseMemoryStrategy):
    """压缩策略。

    当消息数超过阈值时，使用 LLM 压缩旧消息为带文件引用的摘要。
    摘要和原始消息均持久化到文件系统，支持通过引用回读原文。
    """

    def __init__(
        self,
        history_manager: ChatHistoryManager,
        file_store: FileHistoryStore,
        llm: BaseChatModel,
        *,
        max_messages: int = 30,
        keep_recent: int = 10,
    ) -> None:
        super().__init__(history_manager)
        self._file_store = file_store
        self._llm = llm
        self._max_messages = max_messages
        self._keep_recent = keep_recent

        self._compress_chain = build_llm_chain(self._llm, _COMPRESS_SYSTEM, "{input}")

    @property
    def strategy_name(self) -> str:
        return "compression"

    def build_context_messages(
        self,
        session_id: str | None,
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> list[BaseMessage]:
        """构建上下文消息列表（同步）。"""
        result: list[BaseMessage] = []
        if system_prompt:
            result.append(SystemMessage(content=system_prompt))

        if session_id:
            summary_data = self._file_store.read_summary(session_id)
            if summary_data:
                ref_text = FileHistoryStore.format_file_references(
                    summary_data.get("file_references", [])
                )
                summary_content = f"## 之前的对话摘要\n\n{summary_data['summary']}"
                if ref_text:
                    summary_content += f"\n\n{ref_text}"
                result.append(SystemMessage(content=summary_content))

            total = self._file_store.message_count(session_id)
            offset = max(0, total - self._keep_recent)
            recent = self._file_store.read_messages(session_id, offset=offset)
            result.extend(recent)

        return result

    async def abuild_context_messages(
        self,
        session_id: str | None,
        system_prompt: str,
        *,
        max_tokens: int | None = None,
    ) -> list[BaseMessage]:
        """构建上下文消息列表（异步，含自动压缩）。"""
        if session_id:
            total = self._file_store.message_count(session_id)
            if total > self._max_messages:
                await self._acompress(session_id)

        return self.build_context_messages(
            session_id, system_prompt, max_tokens=max_tokens
        )

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        """添加消息到历史记录（同时写入 SQL 和文件）。"""
        self._history.add_message(session_id, message)
        self._file_store.append_message(session_id, message)

    async def aadd_message(self, session_id: str, message: BaseMessage) -> None:
        """添加消息到历史记录（异步）。"""
        self.add_message(session_id, message)

    async def _acompress(self, session_id: str) -> None:
        """压缩旧消息为带文件引用的摘要。"""
        summary_data = self._file_store.read_summary(session_id)
        existing_summary = summary_data["summary"] if summary_data else ""
        existing_end = summary_data["compressed_range"][1] if summary_data else 0

        total = self._file_store.message_count(session_id)
        compress_end = total - self._keep_recent

        if compress_end <= existing_end:
            return

        records = self._file_store.read_records(
            session_id, offset=existing_end, limit=compress_end - existing_end
        )
        if not records:
            return

        conversation_lines = []
        for r in records:
            idx = r.get("index", 0)
            content = r.get("content", "")
            conversation_lines.append(f"[消息#{idx}] {r['type']}: {content}")
        conversation_text = "\n".join(conversation_lines)

        if existing_summary:
            input_text = (
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
        else:
            input_text = (
                "# 任务：对话压缩\n\n"
                "## 待压缩对话内容\n"
                f"{conversation_text}\n\n"
                "## 要求\n"
                "1. 按照系统提示的格式输出结构化摘要\n"
                "2. 为每条关键信息标注来源 [消息#编号]\n"
                "3. 压缩率目标：保留 20-30% 的关键内容"
            )

        try:
            new_summary = await self._compress_chain.ainvoke({"input": input_text})

            file_refs = [
                {
                    "index": r.get("index", 0),
                    "timestamp": r.get("timestamp", ""),
                    "snippet": Obj.safe_content_str(r)[:80],
                }
                for r in records
            ]

            self._file_store.save_summary(
                session_id,
                new_summary,
                compressed_range=(0, compress_end),
                file_references=file_refs,
            )
            logger.info(
                "会话 %s 压缩完成：压缩了 %d 条消息，保留最近 %d 条",
                session_id,
                len(records),
                self._keep_recent,
            )
        except Exception:
            logger.warning("压缩失败，保留原始消息", exc_info=True)

    def read_original(self, session_id: str, message_index: int) -> str | None:
        """根据文件引用回读原始消息内容。"""
        records = self._file_store.read_records(
            session_id, offset=message_index, limit=1
        )
        if records:
            return records[0].get("content")
        return None
