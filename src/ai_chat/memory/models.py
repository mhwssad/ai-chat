"""Memory 模块 — 基类、数据类与异常定义。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


# ======================================================================
# 异常
# ======================================================================


class MemoryProviderNotFoundException(Exception):
    """请求的存储后端未注册。"""

    def __init__(self, name: str, supported: list[str]) -> None:
        self.name = name
        self.supported = supported
        super().__init__(f"存储后端 '{name}' 未注册。已注册：{supported}")


class SessionNotFoundException(Exception):
    """操作的会话不存在。"""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"会话 '{session_id}' 不存在")


# ======================================================================
# 数据类
# ======================================================================


@dataclass
class MessageRecord:
    """单条消息记录。"""

    id: Optional[int] = None
    session_id: str = ""
    role: str = ""  # "human", "ai", "system", "tool"
    content: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class Session:
    """单个会话。"""

    session_id: str
    title: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryConfig:
    """存储后端配置。"""

    backend: str = "sqlite"
    persist_path: Optional[str] = None
    max_short_term_messages: int = 20
    summary_model: Optional[str] = None
    summary_token_limit: int = 1000
    enable_summary: bool = True


# ======================================================================
# 存储后端策略接口
# ======================================================================


class MemoryProvider(ABC):
    """存储后端策略接口。"""

    @abstractmethod
    def create_session(self, session_id: Optional[str] = None) -> Session:
        """创建会话。session_id 为空时自动生成 UUID。"""

    @abstractmethod
    def get_session(self, session_id: str) -> Session:
        """获取会话，不存在则抛出 SessionNotFoundException。"""

    @abstractmethod
    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[Session]:
        """列出会话，按 updated_at 降序。"""

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """删除会话及其所有消息。"""

    @abstractmethod
    def add_message(self, record: MessageRecord) -> MessageRecord:
        """持久化单条消息，返回填充了 id 的记录。"""

    @abstractmethod
    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[MessageRecord]:
        """加载消息，按 id 升序（时间顺序）。"""

    @abstractmethod
    def count_messages(self, session_id: str) -> int:
        """返回会话中的消息总数。"""

    @abstractmethod
    def save_summary(self, session_id: str, summary: str) -> None:
        """保存或更新会话摘要。"""

    @abstractmethod
    def load_summary(self, session_id: str) -> Optional[str]:
        """加载会话摘要，不存在则返回 None。"""


# ======================================================================
# 转换函数 — LangChain BaseMessage ↔ MessageRecord
# ======================================================================

_ROLE_MAP_LC_TO_STR = {
    "human": "human",
    "ai": "ai",
    "system": "system",
    "tool": "tool",
}

_ROLE_MAP_STR_TO_CLS = {
    "human": HumanMessage,
    "ai": AIMessage,
    "system": SystemMessage,
    "tool": ToolMessage,
}


def record_to_message(record: MessageRecord) -> BaseMessage:
    """MessageRecord → LangChain BaseMessage。"""
    cls = _ROLE_MAP_STR_TO_CLS.get(record.role, HumanMessage)
    return cls(content=record.content, additional_kwargs=record.metadata)


def message_to_record(msg: BaseMessage, session_id: str) -> MessageRecord:
    """LangChain BaseMessage → MessageRecord。"""
    role = _ROLE_MAP_LC_TO_STR.get(msg.type, "human")
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    return MessageRecord(
        session_id=session_id,
        role=role,
        content=content,
        metadata=getattr(msg, "additional_kwargs", {}),
    )
