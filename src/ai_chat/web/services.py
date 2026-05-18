"""Web 层服务函数。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from pathlib import Path

from src.ai_chat.config import settings
from src.ai_chat.chains import chain_factory, chain_manager
from src.ai_chat.chains.models import ChainRecord
from src.ai_chat.workflows import workflow_manager
from src.ai_chat.workflows.models import WorkflowRecord
from src.ai_chat.memory import memory_factory
from src.ai_chat.memory.manager import SessionManager, ContextInfo, SessionDetail
from src.ai_chat.memory.models import MessageRecord, Session
from src.ai_chat.graphs.memory_agent import MemoryAgent
from src.ai_chat.graphs.unified_agent import UnifiedAgent
from src.ai_chat.tools.registry import tool_registry, ToolType, ToolRecord
from src.ai_chat.mcp.config import mcp_settings
from src.ai_chat.mcp.client import mcp_client_manager
from src.ai_chat.skills.registry import skill_registry
from src.ai_chat.skills.models import SkillConfig


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
    import uuid
    session_id = str(uuid.uuid4())
    agent = create_chat_agent(agent_name=agent_name, model_name=model_name, session_id=session_id)
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


async def async_send_chat_message(
    agent_name: AgentName,
    model_name: str,
    session_id: str,
    message: str,
) -> str:
    """异步发送聊天消息，直接在事件循环中调用 agent.ainvoke()。"""
    ensure_session_exists(session_id)
    agent = create_chat_agent(agent_name=agent_name, model_name=model_name, session_id=session_id)
    return await agent.ainvoke(message)


def create_chat_agent(agent_name: AgentName, model_name: str, session_id: Optional[str]):
    if agent_name == "memory":
        return MemoryAgent(model_name=model_name, session_id=session_id)
    return UnifiedAgent(model_name=model_name, session_id=session_id)



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


# ── Tools 服务 ────────────────────────────────────────


TOOL_TYPE_LABELS: dict[ToolType, str] = {
    ToolType.SYSTEM: "系统",
    ToolType.CUSTOM: "自定义",
    ToolType.MCP: "MCP",
}


@dataclass(frozen=True)
class ToolView:
    """工具视图模型。"""
    name: str
    tool_type: str
    tool_type_label: str
    description: str
    source_module: str
    loaded: bool
    lazy_loaded: bool
    version: str
    author: str


@dataclass(frozen=True)
class ToolGroupView:
    """按类型分组的工具视图。"""
    type_label: str
    tools: list[ToolView]


def list_tools_grouped() -> list[ToolGroupView]:
    """按 ToolType 分组列出所有已注册工具。"""
    groups: dict[ToolType, list[ToolView]] = {tt: [] for tt in ToolType}
    for record in tool_registry._tools.values():
        groups[record.tool_type].append(_tool_record_to_view(record))
    result = []
    for tt in ToolType:
        if groups[tt]:
            result.append(ToolGroupView(
                type_label=TOOL_TYPE_LABELS.get(tt, tt.value),
                tools=groups[tt],
            ))
    return result


def get_tool_detail(name: str) -> ToolView | None:
    """获取单个工具的详情视图。"""
    if not tool_registry.has(name):
        return None
    return _tool_record_to_view(tool_registry.get_record(name))


def load_system_tools_action() -> int:
    """加载系统工具。"""
    return tool_registry.load_system_tools()


def scan_tools_action() -> int:
    """扫描工具包发现新工具。"""
    return tool_registry.scan("src.ai_chat.tools")


def _tool_record_to_view(record: ToolRecord) -> ToolView:
    return ToolView(
        name=record.tool.name,
        tool_type=record.tool_type.value,
        tool_type_label=TOOL_TYPE_LABELS.get(record.tool_type, record.tool_type.value),
        description=record.description or "",
        source_module=record.source_module or "",
        loaded=record.loaded,
        lazy_loaded=record.lazy_loaded,
        version=record.version,
        author=record.author or "",
    )


# ── Memory 服务 ───────────────────────────────────────


@dataclass(frozen=True)
class SessionDetailView:
    """会话详情视图模型。"""
    session_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    has_summary: bool
    model_name: str
    last_prompt_tokens: int | None


@dataclass(frozen=True)
class ContextInfoView:
    """上下文状态视图模型。"""
    model_name: str
    context_window: int
    context_tokens: int
    threshold_tokens: int
    usage_percent: float
    total_messages: int
    recent_messages: int
    has_summary: bool
    summary_length: int


def _session_manager() -> SessionManager:
    return SessionManager()


def list_memory_sessions(limit: int = 50) -> list[SessionDetailView]:
    """列出所有会话。"""
    details = _session_manager().list_sessions(limit=limit)
    return [_session_detail_to_view(d) for d in details]


def search_memory_sessions(keyword: str) -> list[SessionDetailView]:
    """按标题关键词搜索会话。"""
    details = _session_manager().search_sessions(keyword)
    return [_session_detail_to_view(d) for d in details]


def get_memory_session_detail(session_id: str) -> SessionDetailView | None:
    """获取单个会话详情。"""
    try:
        d = _session_manager().get_session_detail(session_id)
        return _session_detail_to_view(d)
    except Exception:
        return None


def get_memory_context_info(session_id: str) -> ContextInfoView | None:
    """获取会话的上下文状态快照。"""
    try:
        info = _session_manager().get_session_context_info(session_id)
        return _context_info_to_view(info)
    except Exception:
        return None


def rename_memory_session(session_id: str, title: str) -> None:
    """重命名会话。"""
    _session_manager().rename_session(session_id, title)


def delete_memory_session(session_id: str) -> None:
    """删除会话。"""
    _session_manager().delete_session(session_id)


def reset_memory_session(session_id: str) -> None:
    """重置会话上下文。"""
    _session_manager().reset_session(session_id)


def _session_detail_to_view(d: SessionDetail) -> SessionDetailView:
    return SessionDetailView(
        session_id=d.session_id,
        title=d.title or "无标题",
        created_at=d.created_at.strftime("%Y-%m-%d %H:%M"),
        updated_at=d.updated_at.strftime("%Y-%m-%d %H:%M"),
        message_count=d.message_count,
        has_summary=d.has_summary,
        model_name=d.model_name or "",
        last_prompt_tokens=d.last_prompt_tokens,
    )


def _context_info_to_view(info: ContextInfo) -> ContextInfoView:
    return ContextInfoView(
        model_name=info.model_name or "",
        context_window=info.context_window,
        context_tokens=info.context_tokens,
        threshold_tokens=info.threshold_tokens,
        usage_percent=info.usage_percent,
        total_messages=info.total_messages,
        recent_messages=info.recent_messages,
        has_summary=info.has_summary,
        summary_length=info.summary_length,
    )


# ── MCP 服务 ──────────────────────────────────────────


@dataclass(frozen=True)
class MCPStatusView:
    """MCP 状态视图模型。"""
    client_enabled: bool
    server_enabled: bool
    client_initialized: bool
    server_host: str
    server_port: int
    server_transport: str
    tool_count: int


@dataclass(frozen=True)
class MCPToolView:
    """MCP 工具视图模型。"""
    name: str
    description: str


def get_mcp_status() -> MCPStatusView:
    """获取 MCP 状态快照。"""
    tools = mcp_client_manager.tools
    return MCPStatusView(
        client_enabled=mcp_settings.mcp_enabled,
        server_enabled=mcp_settings.mcp_server_enabled,
        client_initialized=mcp_client_manager.is_initialized,
        server_host=mcp_settings.mcp_server_host,
        server_port=mcp_settings.mcp_server_port,
        server_transport=mcp_settings.mcp_server_transport,
        tool_count=len(tools),
    )


def get_mcp_server_configs() -> dict:
    """获取已配置的 MCP 服务器列表。"""
    return mcp_settings.get_server_configs()


def list_mcp_tools() -> list[MCPToolView]:
    """列出 MCP 客户端已加载的工具。"""
    return [
        MCPToolView(name=t.name, description=t.description or "")
        for t in mcp_client_manager.tools
    ]


def initialize_mcp_client() -> int:
    """初始化 MCP 客户端并加载工具。"""
    return mcp_client_manager.run_sync(mcp_client_manager.initialize())


def shutdown_mcp_client() -> None:
    """关闭 MCP 客户端。"""
    mcp_client_manager.run_sync(mcp_client_manager.shutdown())


# ── Skills 服务 ───────────────────────────────────────


@dataclass(frozen=True)
class SkillView:
    """技能视图模型。"""
    name: str
    trigger: str
    description: str
    enabled: bool
    priority: int
    model: str
    tools: tuple[str, ...]
    args_template: str
    system_prompt: str
    skill_dir: str


def list_all_skills() -> list[SkillView]:
    """列出所有已注册技能。"""
    return [_skill_config_to_view(s) for s in skill_registry.get_all()]


def get_skill_detail(name: str) -> SkillView | None:
    """获取单个技能详情。"""
    try:
        return _skill_config_to_view(skill_registry.get(name))
    except KeyError:
        return None


def scan_skills_action() -> int:
    """扫描技能目录发现新技能。"""
    skills_dir = Path(__file__).parent.parent / "skills" / "skills"
    return skill_registry.scan(skills_dir, incremental=True)


def toggle_skill_action(name: str) -> bool:
    """切换技能启用/禁用状态，返回新状态。"""
    skill = skill_registry.get(name)
    skill.enabled = not skill.enabled
    return skill.enabled


def _skill_config_to_view(s: SkillConfig) -> SkillView:
    return SkillView(
        name=s.name,
        trigger=s.trigger,
        description=s.description,
        enabled=s.enabled,
        priority=s.priority,
        model=s.model or "",
        tools=tuple(s.tools),
        args_template=s.args_template or "",
        system_prompt=s.system_prompt,
        skill_dir=str(s.skill_dir) if s.skill_dir else "",
    )
