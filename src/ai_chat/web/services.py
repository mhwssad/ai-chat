"""Web 层服务函数。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from src.ai_chat.config import settings
from src.ai_chat.chains import chain_factory, chain_manager
from src.ai_chat.chains.models import ChainRecord
from src.ai_chat.workflows import workflow_manager
from src.ai_chat.workflows.models import WorkflowRecord
from src.ai_chat.memory import memory_factory
from src.ai_chat.memory.models import MessageRecord, Session
from src.ai_chat.graphs.memory_agent import MemoryAgent
from src.ai_chat.graphs.unified_agent import UnifiedAgent


AgentName = Literal["memory", "unified"]


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    href: str


@dataclass(frozen=True)
class AgentOption:
    value: AgentName
    label: str
    description: str


@dataclass(frozen=True)
class SessionView:
    session_id: str
    title: str
    updated_at: str
    message_count: int


@dataclass(frozen=True)
class MessageView:
    role: str
    content: str
    created_at: str


SUPPORTED_AGENTS: tuple[AgentName, ...] = ("memory", "unified")


def get_nav_items() -> list[NavItem]:
    return [
        NavItem("chat", "聊天", "/chat"),
        NavItem("chains", "调用链", "/chains"),
        NavItem("workflows", "工作流", "/workflows"),
        NavItem("tools", "工具", "/tools"),
        NavItem("memory", "记忆", "/memory"),
        NavItem("mcp", "MCP", "/mcp"),
        NavItem("skills", "技能", "/skills"),
    ]


def get_agent_options() -> list[AgentOption]:
    return [
        AgentOption("memory", "MemoryAgent", "持久记忆的多轮对话"),
        AgentOption("unified", "UnifiedAgent", "记忆 + 工具 + RAG 的统一代理"),
    ]


def normalize_agent_name(agent_name: Optional[str]) -> AgentName:
    if agent_name in SUPPORTED_AGENTS:
        return agent_name
    return "memory"


def default_model_name() -> str:
    return settings.model_name


def list_recent_sessions(limit: int = 12) -> list[SessionView]:
    store = memory_factory.create()
    sessions = store.list_sessions(limit=limit)
    return [
        SessionView(
            session_id=session.session_id,
            title=session.title or "无标题",
            updated_at=session.updated_at.strftime("%Y-%m-%d %H:%M"),
            message_count=store.count_messages(session.session_id),
        )
        for session in sessions
    ]


def load_session_messages(session_id: str) -> list[MessageView]:
    store = memory_factory.create()
    records = store.get_messages(session_id)
    return [_record_to_view(record) for record in records]


def ensure_session_exists(session_id: str) -> Session:
    store = memory_factory.create()
    return store.get_session(session_id)


def create_chat_session(agent_name: AgentName, model_name: str) -> str:
    agent = create_chat_agent(agent_name=agent_name, model_name=model_name, session_id=None)
    return agent.session_id


def send_chat_message(
    agent_name: AgentName,
    model_name: str,
    session_id: str,
    message: str,
) -> str:
    ensure_session_exists(session_id)
    agent = create_chat_agent(agent_name=agent_name, model_name=model_name, session_id=session_id)
    return agent.invoke(message)


def create_chat_agent(agent_name: AgentName, model_name: str, session_id: Optional[str]):
    if agent_name == "memory":
        return MemoryAgent(model_name=model_name, session_id=session_id)
    return UnifiedAgent(model_name=model_name, session_id=session_id)


def placeholder_copy(page_key: str) -> tuple[str, str]:
    mapping = {
        "chains": ("调用链", "这个页面会接入摘要、翻译、抽取和优化等调用链能力。"),
        "tools": ("工具", "这个页面会接入工具列表、详情与执行能力。"),
        "memory": ("记忆", "这个页面会接入会话摘要、历史记录与管理能力。"),
        "mcp": ("MCP", "这个页面会接入 MCP 状态查看与工具加载能力。"),
        "skills": ("技能", "这个页面会接入技能列表、说明与触发信息。"),
    }
    return mapping.get(page_key, ("页面", "该页面正在建设中。"))


# ── Chains 服务 ──────────────────────────────────────


@dataclass(frozen=True)
class ChainTypeOption:
    value: str
    label: str


@dataclass(frozen=True)
class ChainView:
    id: int
    name: str
    chain_type: str
    model_name: str
    description: str
    tags: str
    is_active: bool


def get_chain_type_options() -> list[ChainTypeOption]:
    """返回工厂注册的所有链类型。"""
    type_labels = {
        "chat": "对话",
        "summarize": "摘要",
        "translate": "翻译",
        "extraction": "抽取",
        "refine": "精炼",
        "rag": "RAG 检索增强",
        "code_review": "代码审查",
    }
    info = chain_factory.get_registry_info()
    return [
        ChainTypeOption(value=item["name"], label=type_labels.get(item["name"], item["name"]))
        for item in info
    ]


def list_saved_chains(limit: int = 50) -> list[ChainView]:
    """列出所有持久化链配置。"""
    records = chain_manager.list_chains(limit=limit)
    return [_chain_record_to_view(r) for r in records]


def create_chain_from_form(
    name: str,
    chain_type: str,
    model_name: str = "",
    description: str = "",
    tags: str = "",
) -> ChainRecord:
    """从表单数据创建持久化链配置。"""
    return chain_manager.create_chain(
        name=name,
        chain_type=chain_type,
        model_name=model_name,
        description=description,
        tags=tags,
    )


def invoke_chain_by_name(name: str, input_text: str) -> str:
    """按名称执行链。"""
    return chain_manager.invoke(name, input=input_text)


def delete_chain_by_name(name: str) -> None:
    """按名称删除链配置。"""
    chain_manager.delete_chain(name)


def _chain_record_to_view(record: ChainRecord) -> ChainView:
    return ChainView(
        id=record.id or 0,
        name=record.name,
        chain_type=record.chain_type,
        model_name=record.model_name,
        description=record.description,
        tags=record.tags,
        is_active=record.is_active,
    )


def _record_to_view(record: MessageRecord) -> MessageView:
    return MessageView(
        role=record.role,
        content=record.content,
        created_at=record.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    )


# ── Workflows 服务 ──────────────────────────────────────


@dataclass(frozen=True)
class WorkflowView:
    id: int
    name: str
    description: str
    node_count: int
    edge_count: int
    is_active: bool


def list_saved_workflows(limit: int = 50) -> list[WorkflowView]:
    """列出所有持久化工作流配置。"""
    records = workflow_manager.list_workflows(limit=limit)
    return [_workflow_record_to_view(r) for r in records]


def create_workflow_from_form(
    name: str,
    description: str = "",
    model_name: str = "",
    nodes_json: str = "[]",
    edges_json: str = "[]",
    tags: str = "",
) -> WorkflowRecord:
    """从表单数据创建持久化工作流配置。"""
    import json
    from src.ai_chat.workflows.models import EdgeConfig, NodeConfig
    nodes = [NodeConfig(**n) for n in json.loads(nodes_json)]
    edges = [EdgeConfig(**e) for e in json.loads(edges_json)]
    return workflow_manager.create_workflow(
        name=name,
        description=description,
        model_name=model_name,
        nodes=nodes,
        edges=edges,
        tags=tags,
    )


def invoke_workflow_by_name(name: str, input_text: str) -> str:
    """按名称执行工作流。"""
    return workflow_manager.invoke(name, input_text)


def delete_workflow_by_name(name: str) -> None:
    """按名称删除工作流配置。"""
    workflow_manager.delete_workflow(name)


def _workflow_record_to_view(record: WorkflowRecord) -> WorkflowView:
    return WorkflowView(
        id=record.id or 0,
        name=record.name,
        description=record.description,
        node_count=len(record.nodes),
        edge_count=len(record.edges),
        is_active=record.is_active,
    )
