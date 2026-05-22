"""Memory 模块 — SQLModel 表模型、传输模型、ABC 与转换函数。

本模块定义了 Memory 存储层的全部数据结构:
- 数据库表模型（SessionTable, MessageTable, SummaryTable）— SQLModel ORM 映射
- 传输模型（Session, MessageRecord, MemoryConfig）— 纯 Pydantic，不映射表
- 存储后端策略接口（MemoryProvider ABC）
- LangChain BaseMessage 与 MessageRecord 之间的双向转换函数
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON, Index
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from pydantic import BaseModel
from sqlmodel import SQLModel, Field


# ======================================================================
# 异常
# ======================================================================


class MemoryProviderNotFoundException(Exception):
    """请求的存储后端未注册时抛出。"""

    def __init__(self, name: str, supported: list[str]) -> None:
        self.name = name
        self.supported = supported
        super().__init__(f"存储后端 '{name}' 未注册。已注册：{supported}")


class SessionNotFoundException(Exception):
    """操作的会话不存在时抛出。"""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"会话 '{session_id}' 不存在")


# ======================================================================
# 数据库表模型（SQLModel table=True = Pydantic + SQLAlchemy）
# ======================================================================


class SessionTable(SQLModel, table=True):
    """会话表 — 存储会话元信息。

    Attributes:
        session_id: 会话唯一标识（主键），为空时自动生成 UUID
        title: 会话标题
        created_at: 创建时间
        updated_at: 最后更新时间
        metadata_: JSON 扩展字段，存储 last_prompt_tokens 等
    """

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_updated_at", "updated_at"),
        Index("ix_sessions_status", "status"),
    )

    session_id: str = Field(primary_key=True)
    title: str = Field(default="")
    current_model: Optional[str] = Field(default=None, index=True)
    message_count: int = Field(default=0)
    status: str = Field(default="active")
    last_error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata_: dict = Field(default={}, sa_column=Column("metadata", JSON))


class MessageTable(SQLModel, table=True):
    """消息表 — 存储会话中的每条消息。

    Attributes:
        id: 自增主键
        session_id: 所属会话（外键关联 sessions 表）
        role: 消息角色（human/ai/system/tool）
        content: 消息文本内容
        created_at: 创建时间
        metadata_: JSON 扩展字段，存储 token_count 等
    """

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_session_id", "session_id"),
        Index("ix_messages_status", "status"),
        Index("ix_messages_model", "model"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessions.session_id")
    role: str
    content: str
    model: Optional[str] = Field(default=None)
    status: str = Field(default="completed")
    error_type: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata_: dict = Field(default={}, sa_column=Column("metadata", JSON))


class SummaryTable(SQLModel, table=True):
    """摘要表 — 存储会话的长期对话摘要。

    每个会话最多一条摘要记录，压缩时追加更新。

    Attributes:
        session_id: 关联的会话 ID（主键 + 外键）
        summary: 摘要文本（多次压缩以 --- 分隔拼接）
        updated_at: 最后更新时间
    """

    __tablename__ = "summaries"

    session_id: str = Field(primary_key=True, foreign_key="sessions.session_id")
    summary: str
    updated_at: datetime = Field(default_factory=datetime.now)


# ======================================================================
# 对外传输模型（纯 Pydantic，不映射表）
# ======================================================================


class Session(BaseModel):
    """会话传输对象。"""

    session_id: str
    title: str = ""
    current_model: Optional[str] = None
    message_count: int = 0
    status: str = "active"
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = {}


class MessageRecord(BaseModel):
    """消息记录传输对象。

    在存储层和业务层之间传递，与数据库表解耦。
    metadata 中可包含 token_count（tiktoken 计数）等扩展信息。
    """

    id: Optional[int] = None
    session_id: str = ""
    role: str = ""
    content: str = ""
    model: Optional[str] = None
    status: str = "completed"
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = {}


class MemoryConfig(BaseModel):
    """存储后端配置。

    Attributes:
        backend: 存储后端名称，'sqlite' 或 'in_memory'
        persist_path: 数据持久化路径（仅 sqlite 使用），None 时使用默认路径
        max_short_term_messages: 短期上下文窗口保留的最大消息条数
        summary_model: 生成摘要时使用的 LLM 模型名称，None 时使用全局默认
        summary_token_limit: 摘要生成的最大 token 数（提示词中的约束）
        enable_summary: 是否启用自动摘要压缩
    """

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
    """存储后端策略接口。

    所有存储后端（SQLite、内存等）均须实现此接口。
    方法涵盖会话生命周期管理、消息 CRUD 和摘要存取。
    """

    @abstractmethod
    def create_session(self, session_id: Optional[str] = None) -> Session:
        """创建会话。session_id 为空时自动生成 UUID。"""

    @abstractmethod
    def get_session(self, session_id: str) -> Session:
        """获取会话，不存在则抛出 SessionNotFoundException。"""

    @abstractmethod
    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[Session]:
        """列出会话，按 updated_at 降序排列。"""

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """删除会话及其所有消息和摘要。"""

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
        """保存或更新会话摘要（upsert 语义）。"""

    @abstractmethod
    def load_summary(self, session_id: str) -> Optional[str]:
        """加载会话摘要，不存在则返回 None。"""

    @abstractmethod
    def update_session_timestamp(self, session_id: str) -> None:
        """更新会话的 updated_at 为当前时间。"""

    @abstractmethod
    def update_session_metadata(self, session_id: str, metadata: dict) -> None:
        """合并更新会话的 metadata 字段（不覆盖已有字段）。

        用于存储 last_prompt_tokens 等 token 追踪信息。
        """

    @abstractmethod
    def delete_messages_before(self, session_id: str, keep_count: int) -> int:
        """删除旧消息，只保留最近 keep_count 条。

        用于手动裁剪上下文，返回被删除的消息数量。
        """

    @abstractmethod
    def reset_context(self, session_id: str) -> None:
        """清除会话的所有消息和摘要，但保留会话本身。"""

    @abstractmethod
    def count_sessions(self) -> int:
        """返回会话总数。"""

    @abstractmethod
    def search_sessions(self, keyword: str, limit: int = 50, offset: int = 0) -> list[Session]:
        """按标题关键词搜索会话，按 updated_at 降序。"""

    @abstractmethod
    def update_session_title(self, session_id: str, title: str) -> None:
        """更新会话标题。"""

    @abstractmethod
    def batch_count_messages(self, session_ids: list[str]) -> dict[str, int]:
        """批量统计多个会话的消息数量。

        Returns:
            {session_id: count} 字典，未找到的会话计数为 0。
        """

    @abstractmethod
    def batch_has_summaries(self, session_ids: list[str]) -> dict[str, bool]:
        """批量检查多个会话是否有摘要。

        Returns:
            {session_id: has_summary} 字典。
        """


# ======================================================================
# 转换函数 — LangChain BaseMessage ↔ MessageRecord
# ======================================================================

# LangChain 消息类型 -> 字符串角色标识
_ROLE_MAP_LC_TO_STR = {
    "human": "human",
    "ai": "ai",
    "system": "system",
    "tool": "tool",
}

# 字符串角色标识 -> LangChain 消息类型
_ROLE_MAP_STR_TO_CLS = {
    "human": HumanMessage,
    "ai": AIMessage,
    "system": SystemMessage,
    "tool": ToolMessage,
}


def record_to_message(record: MessageRecord) -> BaseMessage:
    """MessageRecord → LangChain BaseMessage。

    根据 role 字段映射到对应的 LangChain 消息类型，
    metadata 作为 additional_kwargs 传递。
    """
    cls = _ROLE_MAP_STR_TO_CLS.get(record.role, HumanMessage)
    return cls(content=record.content, additional_kwargs=record.metadata)


def message_to_record(msg: BaseMessage, session_id: str, *, token_count: Optional[int] = None) -> MessageRecord:
    """LangChain BaseMessage → MessageRecord。

    Args:
        msg: LangChain 消息对象
        session_id: 目标会话 ID
        token_count: 该消息的 token 数，存入 metadata["token_count"]。
                     用于 token 感知的上下文压缩判断。
    """
    role = _ROLE_MAP_LC_TO_STR.get(msg.type, "human")
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    metadata = dict(getattr(msg, "additional_kwargs", {}))
    if token_count is not None:
        metadata["token_count"] = token_count
    return MessageRecord(
        session_id=session_id,
        role=role,
        content=content,
        metadata=metadata,
    )


# ── 表模型 ↔ 传输模型 转换（仅供存储后端内部使用）───────────


def _table_to_session(row: SessionTable) -> Session:
    """SessionTable ORM 行 → Session 传输对象。"""
    return Session(
        session_id=row.session_id,
        title=row.title,
        current_model=row.current_model,
        message_count=row.message_count,
        status=row.status,
        last_error=row.last_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
        metadata=row.metadata_,
    )


def _table_to_message_record(row: MessageTable) -> MessageRecord:
    """MessageTable ORM 行 → MessageRecord 传输对象。"""
    return MessageRecord(
        id=row.id,
        session_id=row.session_id,
        role=row.role,
        content=row.content,
        model=row.model,
        status=row.status,
        error_type=row.error_type,
        error_message=row.error_message,
        created_at=row.created_at,
        metadata=row.metadata_,
    )
