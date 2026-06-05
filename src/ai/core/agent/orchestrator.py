"""Agent 编排器 — 基于 LangGraph StateGraph 的 ReAct 循环。

职责：
1. 构建上下文（ContextService）
2. LLM 推理（ModelService）
3. 工具执行（TimeoutToolNode，并行 + 超时）
4. 状态管理（LangGraph GraphState）
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from src.ai.core.agent.state import GraphState
from src.ai.core.agent.types import AgentResult, AgentStatus, AgentTraceStep, ToolCall
from src.ai.core.context.types import ContextBuildRequest
from src.ai.core.tools.timeout_node import TimeoutToolNode
from src.ai.utils.redaction import redact_for_audit

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

    from src.ai.core.context.service import ContextService
    from src.ai.core.models.service import ModelService
    from src.ai.core.tools.manager import ToolManager
    from src.ai.core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Agent 编排器。

    基于 LangGraph StateGraph 实现 ReAct（Reasoning + Acting）循环：
    1. 推理：LLM 分析当前状态并决定下一步行动
    2. 行动：ToolNode 并行执行工具调用
    3. 观察：工具结果自动追加到消息状态
    4. 重复直到任务完成或达到最大迭代次数

    Args:
        model_service: 模型服务。
        tool_manager: 工具管理器。
        context_service: 上下文服务。
        tool_registry: 工具注册表（用于获取 BaseTool 给 ToolNode）。
    """

    def __init__(
        self,
        *,
        model_service: ModelService,
        tool_manager: ToolManager,
        context_service: ContextService,
        tool_registry: ToolRegistry,
        checkpointer: Any = None,
    ) -> None:
        self._model = model_service
        self._tools = tool_manager
        self._context = context_service
        self._registry = tool_registry
        self._checkpointer = checkpointer
        self._current_task: asyncio.Task | None = None

    async def run(
        self,
        *,
        session_id: str,
        user_message: str,
        system_prompt: str | None = None,
        max_iterations: int = 10,
        tools: list[str] | None = None,
        agent_timeout: float = 300,
    ) -> AgentResult:
        """执行 Agent 循环。

        Args:
            session_id: 会话 ID。
            user_message: 用户消息。
            system_prompt: 系统提示（可选，覆盖默认）。
            max_iterations: 最大迭代次数。
            tools: 可用工具名称列表（None 表示全部）。
            agent_timeout: Agent 整体超时秒数（默认 300）。

        Returns:
            Agent 执行结果。
        """
        # 添加用户消息到策略历史
        await self._context.strategy.aadd_message(
            session_id, HumanMessage(content=user_message)
        )

        # 获取 BaseTool 列表
        available_tools = self._get_base_tools(tools)

        logger.info(
            "Agent 开始执行: session=%s, max_iterations=%d, tools=%d, timeout=%.0fs",
            session_id,
            max_iterations,
            len(available_tools),
            agent_timeout,
        )

        # 构建并编译图
        graph = self._build_graph(available_tools)
        compile_kwargs: dict[str, Any] = {}
        if self._checkpointer is not None:
            compile_kwargs["checkpointer"] = self._checkpointer
        compiled = graph.compile(**compile_kwargs)

        # 初始状态
        initial_state: dict[str, Any] = {
            "messages": [],
            "iteration": 0,
            "max_iterations": max_iterations,
            "total_tokens": 0,
            "session_id": session_id,
            "is_plan_mode": False,
            "plan": None,
            "error": None,
            "checkpoint_id": None,
            "interrupted_at": None,
            "user_approval_pending": False,
            "context_sources": [],
        }

        # 构造 RunnableConfig（含 thread_id 用于 checkpoint）
        config: dict[str, Any] | None = None
        if self._checkpointer is not None:
            config = {"configurable": {"thread_id": session_id}}

        start_time = time.perf_counter()

        try:
            # 创建任务并保存引用（支持 cancel）
            self._current_task = asyncio.current_task()
            final_state = await asyncio.wait_for(
                compiled.ainvoke(initial_state, config=config),  # type: ignore[arg-type]
                timeout=agent_timeout,
            )
        except TimeoutError:
            logger.warning(
                "Agent 整体超时: session=%s, timeout=%.0fs",
                session_id,
                agent_timeout,
            )
            return AgentResult(
                status=AgentStatus.TIMEOUT,
                content=f"Agent 执行超时 ({agent_timeout}s)",
                tool_calls=[],
                iterations=0,
                total_tokens=0,
                trace=[
                    AgentTraceStep(
                        index=1,
                        step_type="timeout",
                        title="Agent 超时",
                        summary=f"整体执行超过 {agent_timeout}s",
                        status="timeout",
                    )
                ],
            )
        except asyncio.CancelledError:
            logger.info("Agent 被取消: session=%s", session_id)
            return AgentResult(
                status=AgentStatus.CANCELLED,
                content="Agent 执行被取消",
                tool_calls=[],
                iterations=0,
                total_tokens=0,
                trace=[
                    AgentTraceStep(
                        index=1,
                        step_type="cancelled",
                        title="Agent 已取消",
                        summary="用户取消了当前执行",
                        status="cancelled",
                    )
                ],
            )
        except Exception as e:
            logger.error(
                "Agent 图执行异常: session=%s, error=%s",
                session_id,
                str(e),
                exc_info=True,
            )
            return AgentResult(
                status=AgentStatus.FAILED,
                content=f"执行异常: {e}",
                tool_calls=[],
                iterations=0,
                total_tokens=0,
                trace=[
                    AgentTraceStep(
                        index=1,
                        step_type="error",
                        title="Agent 异常",
                        summary=redact_for_audit(str(e), max_length=500),
                        status="failed",
                        error=type(e).__name__,
                    )
                ],
            )
        finally:
            self._current_task = None

        duration = int((time.perf_counter() - start_time) * 1000)
        logger.info("Agent 执行完成: session=%s, duration=%dms", session_id, duration)

        # 从最终状态构建结果
        return self._build_result(final_state)  # type: ignore[arg-type]

    def cancel(self) -> bool:
        """取消当前正在执行的 Agent 任务。

        Returns:
            True 表示成功取消，False 表示没有正在执行的任务。
        """
        if self._current_task is not None and not self._current_task.done():
            self._current_task.cancel()
            logger.info("Agent 任务取消请求已发送")
            return True
        return False

    def set_confirm_handler(self, handler: Any | None) -> None:
        """设置工具权限确认回调。"""
        self._tools.set_confirm_handler(handler)

    async def resume(
        self,
        *,
        session_id: str,
        user_message: str,
        max_iterations: int = 10,
        tools: list[str] | None = None,
        agent_timeout: float = 300,
    ) -> AgentResult:
        """从 checkpoint 恢复 Agent 执行。

        Args:
            session_id: 会话 ID（用于定位 checkpoint）。
            user_message: 新的用户消息。
            max_iterations: 最大迭代次数。
            tools: 可用工具名称列表。
            agent_timeout: Agent 整体超时秒数。

        Returns:
            Agent 执行结果。

        Raises:
            RuntimeError: 无 checkpointer 或 checkpoint 不存在时。
        """
        if self._checkpointer is None:
            raise RuntimeError("Agent 未配置 checkpointer，无法恢复执行")

        # 检查 checkpoint 是否存在
        config = {"configurable": {"thread_id": session_id}}
        checkpoint = await self._checkpointer.aget(config)
        if checkpoint is None:
            raise RuntimeError(f"未找到 session {session_id} 的 checkpoint")

        # 添加用户消息到策略历史
        await self._context.strategy.aadd_message(
            session_id, HumanMessage(content=user_message)
        )

        available_tools = self._get_base_tools(tools)

        logger.info(
            "Agent 从 checkpoint 恢复: session=%s, checkpoint_id=%s",
            session_id,
            checkpoint.id,
        )

        # 构建并编译图
        graph = self._build_graph(available_tools)
        compile_kwargs: dict[str, Any] = {}
        compile_kwargs["checkpointer"] = self._checkpointer
        compiled = graph.compile(**compile_kwargs)

        start_time = time.perf_counter()

        try:
            self._current_task = asyncio.current_task()
            final_state = await asyncio.wait_for(
                compiled.ainvoke(None, config=config),  # type: ignore[call-overload]
                timeout=agent_timeout,
            )
        except TimeoutError:
            return AgentResult(
                status=AgentStatus.TIMEOUT,
                content=f"Agent 恢复执行超时 ({agent_timeout}s)",
                tool_calls=[],
                iterations=0,
                total_tokens=0,
                trace=[
                    AgentTraceStep(
                        index=1,
                        step_type="timeout",
                        title="Agent 恢复超时",
                        summary=f"恢复执行超过 {agent_timeout}s",
                        status="timeout",
                    )
                ],
            )
        except asyncio.CancelledError:
            return AgentResult(
                status=AgentStatus.CANCELLED,
                content="Agent 恢复执行被取消",
                tool_calls=[],
                iterations=0,
                total_tokens=0,
                trace=[
                    AgentTraceStep(
                        index=1,
                        step_type="cancelled",
                        title="Agent 恢复已取消",
                        summary="用户取消了恢复执行",
                        status="cancelled",
                    )
                ],
            )
        except Exception as e:
            logger.error(
                "Agent 恢复执行异常: session=%s, error=%s",
                session_id,
                str(e),
                exc_info=True,
            )
            return AgentResult(
                status=AgentStatus.FAILED,
                content=f"恢复执行异常: {e}",
                tool_calls=[],
                iterations=0,
                total_tokens=0,
                trace=[
                    AgentTraceStep(
                        index=1,
                        step_type="error",
                        title="Agent 恢复异常",
                        summary=redact_for_audit(str(e), max_length=500),
                        status="failed",
                        error=type(e).__name__,
                    )
                ],
            )
        finally:
            self._current_task = None

        duration = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "Agent 恢复执行完成: session=%s, duration=%dms", session_id, duration
        )

        return self._build_result(final_state)  # type: ignore[arg-type]

    def _build_graph(self, tools: list[BaseTool]) -> StateGraph:
        """构建 LangGraph 状态图。

        图结构：
        START → context_builder → llm_call ──[有工具调用]──→ tools → plan_mode_check ──[继续]──→ llm_call
                                       │                                                  │
                                       └──[无工具调用]──→ END              ──[退出/错误]──→ END

        Args:
            tools: 可用的 BaseTool 列表。

        Returns:
            编译前的 StateGraph。
        """
        # 创建 TimeoutToolNode（带超时的工具执行节点）
        tool_node = TimeoutToolNode(
            tools,
            handle_tool_errors=True,
            tool_manager=self._tools,
        )

        # 创建绑定工具的 LLM
        llm = self._model.get_chat_llm(streaming=False)
        if tools:
            llm = llm.bind_tools(tools)  # type: ignore[assignment]

        # 创建图
        graph = StateGraph(GraphState)

        # 注册节点
        graph.add_node("context_builder", self._create_context_builder_node())
        graph.add_node("llm_call", self._llm_call_node(llm))
        graph.add_node("tools", tool_node)
        graph.add_node("plan_mode_check", self._plan_mode_check_node)

        # 注册边
        graph.add_edge(START, "context_builder")
        graph.add_edge("context_builder", "llm_call")
        graph.add_conditional_edges(
            "llm_call",
            self._should_continue,
            {"tools": "tools", "end": END},
        )
        graph.add_edge("tools", "plan_mode_check")
        graph.add_conditional_edges(
            "plan_mode_check",
            self._after_plan_check,
            {"llm_call": "llm_call", "end": END},
        )

        return graph

    # ── 节点函数 ──────────────────────────────────────────────

    def _create_context_builder_node(self):
        """创建上下文构建节点（闭包捕获 self）。"""

        async def node(state: GraphState) -> dict[str, Any]:
            session_id = state["session_id"]
            request = ContextBuildRequest(
                session_id=session_id,
                messages=[],
            )
            result = await self._context.abuild(request)
            return {
                "messages": result.messages,
                "context_sources": [
                    {
                        "source": item.source,
                        "item_count": item.item_count,
                        "token_count": item.token_count,
                        "truncated": item.truncated,
                        "cacheable": item.cacheable,
                        "summary": item.summary,
                    }
                    for item in result.source_summary
                ],
            }

        return node

    def _llm_call_node(self, llm: Any):
        """创建 LLM 调用节点（闭包捕获 llm）。"""

        async def node(state: GraphState) -> dict[str, Any]:
            messages = state["messages"]
            session_id = state["session_id"]
            iteration = state["iteration"] + 1

            logger.debug(
                "LLM 推理: session=%s, iteration=%d",
                session_id,
                iteration,
            )

            # 单次 LLM 调用独立超时（60s），避免消耗整个 agent_timeout 预算
            try:
                async with asyncio.timeout(60):
                    response = await llm.ainvoke(messages)
            except TimeoutError:
                logger.warning(
                    "LLM 调用超时: session=%s, iteration=%d",
                    session_id,
                    iteration,
                )
                return {
                    "messages": [AIMessage(content="LLM 调用超时，请重试。")],
                    "iteration": iteration,
                    "error": "LLM 调用超时 (60s)",
                }

            if not isinstance(response, AIMessage):
                response = AIMessage(content=str(response))

            # 提取 token 使用量
            usage = getattr(response, "usage_metadata", None) or {}
            input_tokens = usage.get("input_tokens", 0) or 0
            output_tokens = usage.get("output_tokens", 0) or 0

            return {
                "messages": [response],
                "iteration": iteration,
                "total_tokens": state["total_tokens"] + input_tokens + output_tokens,
            }

        return node

    @staticmethod
    async def _plan_mode_check_node(state: GraphState) -> dict[str, Any]:
        """检测 exit_plan_mode 工具调用。"""
        messages = state["messages"]
        ai_message = _find_last_ai_message(messages)

        if ai_message is None:
            return {}

        # 检查是否有 exit_plan_mode 调用
        for tc in ai_message.tool_calls or []:
            if tc.get("name") == "exit_plan_mode":
                plan = tc.get("args", {}).get("plan", "")
                logger.info(
                    "Agent 检测到 exit_plan_mode: plan_length=%d",
                    len(plan),
                )
                return {"is_plan_mode": True, "plan": plan}

        return {}

    # ── 路由函数 ──────────────────────────────────────────────

    @staticmethod
    def _should_continue(state: GraphState) -> str:
        """判断是否继续执行工具。"""
        messages = state["messages"]
        ai_message = _find_last_ai_message(messages)

        if ai_message is None:
            return "end"

        # AIMessage 有 tool_calls → 执行工具
        if ai_message.tool_calls:
            return "tools"

        return "end"

    @staticmethod
    def _after_plan_check(state: GraphState) -> str:
        """工具执行后判断是否继续循环。"""
        # 计划模式 → 结束
        if state.get("is_plan_mode"):
            return "end"

        # 等待用户确认 → 结束，交给调用层展示等待状态
        if state.get("user_approval_pending"):
            return "end"

        # 达到最大迭代次数 → 结束
        if state["iteration"] >= state["max_iterations"]:
            logger.warning(
                "Agent 达到最大迭代次数: session=%s, iterations=%d",
                state["session_id"],
                state["iteration"],
            )
            return "end"

        # 错误 → 结束
        if state.get("error"):
            return "end"

        return "llm_call"

    # ── 辅助方法 ──────────────────────────────────────────────

    def _get_base_tools(self, tool_names: list[str] | None = None) -> list[BaseTool]:
        """获取 BaseTool 列表。

        Args:
            tool_names: 工具名称列表，None 表示全部。

        Returns:
            BaseTool 列表。
        """
        all_tools = self._registry.list(enabled_only=True)

        if tool_names is None:
            return all_tools

        name_set = set(tool_names)
        return [t for t in all_tools if t.name in name_set]

    @staticmethod
    def _build_result(state: GraphState) -> AgentResult:
        """从最终图状态构建 AgentResult。"""
        messages = state["messages"]
        tool_calls = _rebuild_tool_calls(messages)

        # 提取最终响应内容
        content = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                content = msg.content or ""  # type: ignore[assignment]
                break

        # 确定状态
        if state.get("error"):
            status = AgentStatus.FAILED
            content = content or f"执行异常: {state['error']}"
        elif state.get("user_approval_pending"):
            status = AgentStatus.WAITING_CONFIRMATION
            content = content or "等待用户确认"
        elif state.get("is_plan_mode"):
            status = AgentStatus.PLAN_MODE
            content = content or "等待计划审批"
        elif state["iteration"] >= state["max_iterations"]:
            status = AgentStatus.MAX_ITERATIONS
            content = content or "达到最大迭代次数，任务未完成。"
        else:
            status = AgentStatus.SUCCESS

        return AgentResult(
            status=status,
            content=content,
            tool_calls=tool_calls,
            iterations=state["iteration"],
            total_tokens=state.get("total_tokens", 0),
            plan=state.get("plan"),
            trace=_build_trace(messages),
            context_sources=state.get("context_sources", []),
        )


# ── 模块级辅助函数 ──────────────────────────────────────────


def _find_last_ai_message(messages: list[BaseMessage]) -> AIMessage | None:
    """查找最后一条 AIMessage。"""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return msg
    return None


def _rebuild_tool_calls(messages: list[BaseMessage]) -> list[ToolCall]:
    """从消息历史重建 ToolCall 记录。

    匹配 AIMessage.tool_calls 与对应的 ToolMessage，
    构建完整的工具调用记录列表。

    Args:
        messages: 消息列表。

    Returns:
        ToolCall 列表。
    """
    # 构建 tool_call_id → ToolMessage 映射
    tool_results: dict[str, ToolMessage] = {}
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.tool_call_id:
            tool_results[msg.tool_call_id] = msg

    # 遍历 AIMessage 提取工具调用
    result: list[ToolCall] = []
    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        for tc in msg.tool_calls or []:
            tc_id = tc.get("id", str(uuid.uuid4()))
            tool_msg = tool_results.get(tc_id)  # type: ignore[arg-type]

            error: str | None = None
            result_content: str | None = None
            if tool_msg:
                content = tool_msg.content or ""
                # ToolNode 将错误格式化为 "Error: ..." 开头
                if content.startswith("Error:"):  # type: ignore[union-attr]
                    error = content  # type: ignore[assignment]
                else:
                    result_content = content  # type: ignore[assignment]

            result.append(
                ToolCall(
                    id=tc_id,  # type: ignore[arg-type]
                    name=tc.get("name", ""),
                    arguments=tc.get("args", {}),
                    result=result_content,
                    error=error,
                )
            )

    return result


def _build_trace(messages: list[BaseMessage]) -> list[AgentTraceStep]:
    """从消息历史构建可展示的 Agent 执行轨迹。"""
    steps: list[AgentTraceStep] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            steps.append(
                AgentTraceStep(
                    index=len(steps) + 1,
                    step_type="user",
                    title="用户输入",
                    summary=_content_summary(msg.content),
                )
            )
            continue

        if isinstance(msg, AIMessage):
            tool_calls = msg.tool_calls or []
            title = "模型决策" if tool_calls else "模型回复"
            summary = _content_summary(msg.content)
            if tool_calls:
                names = ", ".join(str(tc.get("name", "")) for tc in tool_calls)
                summary = f"请求工具: {names}" if names else "请求工具执行"
            steps.append(
                AgentTraceStep(
                    index=len(steps) + 1,
                    step_type="llm",
                    title=title,
                    summary=summary,
                )
            )
            continue

        if isinstance(msg, ToolMessage):
            content = _content_summary(msg.content)
            is_error = content.startswith("Error:")
            steps.append(
                AgentTraceStep(
                    index=len(steps) + 1,
                    step_type="tool",
                    title=f"工具结果 {msg.name or msg.tool_call_id or ''}".strip(),
                    summary=content,
                    status="failed" if is_error else "success",
                    error=content if is_error else None,
                )
            )

    return steps


def _content_summary(value: Any) -> str:
    """生成 Agent 轨迹内容摘要。"""
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = str(value)
    return redact_for_audit(text, max_length=500)
