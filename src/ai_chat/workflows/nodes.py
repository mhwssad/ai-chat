"""节点执行器工厂 — 按节点类型创建 StateGraph 节点函数。"""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.messages import AIMessage

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.workflows.models import NodeConfig, WorkflowConfig
from src.ai_chat.workflows.state import WorkflowState, extract_last_human_message

logger = get_logger(__name__)

# 节点构建函数签名：(NodeConfig, WorkflowConfig) -> (WorkflowState) -> dict
NodeBuilder = Callable[[NodeConfig, WorkflowConfig], Callable[[WorkflowState], dict]]


def _build_chain_node(node: NodeConfig, wf_config: WorkflowConfig) -> Callable:
    """构建 chain 类型节点 — 引用持久化链执行。"""
    ref = node.ref

    def execute(state: WorkflowState) -> dict:
        from src.ai_chat.chains import chain_manager

        chain = chain_manager.instantiate(ref)
        input_text = extract_last_human_message(state["messages"])
        result = chain.invoke(input_text)
        return {
            "messages": [AIMessage(content=result)],
            "outputs": {**state.get("outputs", {}), node.name: result},
        }

    return execute


def _build_llm_node(node: NodeConfig, wf_config: WorkflowConfig) -> Callable:
    """构建 llm 类型节点 — 原始 LLM 调用。"""
    prompt_key = node.prompt_key
    prompt_context = dict(node.prompt_context)
    model_name = node.model_name or wf_config.default_model

    def execute(state: WorkflowState) -> dict:
        from src.ai_chat.llm import llm_factory
        from src.ai_chat.prompts import render_messages

        question = extract_last_human_message(state["messages"])
        context = {**prompt_context, "question": question}
        if state.get("context"):
            context["context"] = state["context"]

        messages = render_messages(prompt_key, **context) if prompt_key else state["messages"]
        model = model_name or ""
        llm = llm_factory.get_chat_provider(model).get_client(model)
        result = llm.invoke(messages)
        content = result.content if isinstance(result.content, str) else str(result.content)
        return {
            "messages": [AIMessage(content=content)],
            "outputs": {**state.get("outputs", {}), node.name: content},
        }

    return execute


def _build_agent_node(node: NodeConfig, wf_config: WorkflowConfig) -> Callable:
    """构建 agent 类型节点 — 引用已注册 Agent 执行。"""
    ref = node.ref
    model_name = node.model_name or wf_config.default_model

    def execute(state: WorkflowState) -> dict:
        from src.ai_chat.graphs import agent_factory

        agent = agent_factory.create(ref, model_name=model_name)
        message = extract_last_human_message(state["messages"])
        result = agent.invoke(message)
        return {
            "messages": [AIMessage(content=result)],
            "outputs": {**state.get("outputs", {}), node.name: result},
        }

    return execute


def _build_classifier_node(node: NodeConfig, wf_config: WorkflowConfig) -> Callable:
    """构建 classifier 类型节点 — LLM 分类，输出路由键到 state["intent"]。"""
    prompt_key = node.prompt_key
    prompt_context = dict(node.prompt_context)
    allowed = list(node.allowed_intents)
    model_name = node.model_name or wf_config.default_model

    def execute(state: WorkflowState) -> dict:
        from src.ai_chat.llm import llm_factory
        from src.ai_chat.prompts import render_messages

        question = extract_last_human_message(state["messages"])
        context = {**prompt_context, "question": question}

        if prompt_key:
            messages = render_messages(prompt_key, **context)
        else:
            from langchain_core.messages import HumanMessage, SystemMessage
            allowed_str = ", ".join(allowed) if allowed else "chat, rag"
            system = f"你是一个意图分类器。根据用户输入，只返回以下类别之一: {allowed_str}。只返回类别名称，不要其他内容。"
            messages = [SystemMessage(content=system), HumanMessage(content=question)]

        model = model_name or ""
        llm = llm_factory.get_chat_provider(model).get_client(model)
        result = llm.invoke(messages)
        intent = result.content.strip().lower() if isinstance(result.content, str) else ""

        if allowed and intent not in allowed:
            intent = allowed[0]

        logger.debug("分类器 '%s' 输出: '%s'", node.name, intent)
        return {
            "intent": intent,
            "outputs": {**state.get("outputs", {}), node.name: intent},
        }

    return execute


def _build_passthrough_node(node: NodeConfig, wf_config: WorkflowConfig) -> Callable:
    """构建 input/output 虚拟节点 — 透传。"""

    def execute(state: WorkflowState) -> dict:
        return {}

    return execute


class NodeExecutorFactory:
    """节点执行器工厂 — 按节点类型注册和创建节点函数。"""

    def __init__(self) -> None:
        self._registry: dict[str, NodeBuilder] = {}
        self.register("chain", _build_chain_node)
        self.register("llm", _build_llm_node)
        self.register("agent", _build_agent_node)
        self.register("classifier", _build_classifier_node)
        self.register("input", _build_passthrough_node)
        self.register("output", _build_passthrough_node)

    def register(self, node_type: str, builder: NodeBuilder) -> None:
        """注册节点类型构建函数。"""
        self._registry[node_type] = builder

    def build(self, node: NodeConfig, wf_config: WorkflowConfig) -> Callable:
        """构建节点执行函数。"""
        builder = self._registry.get(node.type)
        if builder is None:
            raise ValueError(f"未知节点类型: '{node.type}'，可用: {list(self._registry)}")
        return builder(node, wf_config)

    def list_types(self) -> list[str]:
        """返回所有已注册的节点类型。"""
        return list(self._registry.keys())
