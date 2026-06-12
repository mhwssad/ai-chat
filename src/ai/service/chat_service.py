"""统一对话服务 — 流式/非流式对话编排，含工具调用循环和记忆提取。
还包含 Agent 模式的规划阶段：分析需求 → 生成计划 → 自动执行。

合并自：
- cli/chat_executor.py — 工具调用循环、记忆提取
- api/services/chat_service.py — 流式支持、多模态消息转换

共享服务层，CLI 和 API 统一使用。
"""

from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from src.ai.config.logging_setup import get_logger
from src.ai.core.context.types import ContextBuildRequest
from src.ai.service.types import ChatOptions, ChatResult

logger = get_logger(__name__)

# 工具结果最大字符数
_TOOL_RESULT_MAX_LEN = 2000


def _extract_tool_calls_from_chunks(
    full_content: str,
    pending_tc: dict[int, dict[str, str]],
) -> list[dict[str, Any]]:
    """回退：从未流式化的 pending_tc 中提取完整 tool_calls。

    部分 LLM 提供商的流式响应中 tool_call_chunks 为空，
    但最终 chunk 的 additional_kwargs.tool_calls 包含完整信息。
    此函数尝试从 pending_tc 中从未使用的条目提取工具调用。

    Args:
        full_content: 累积的文本内容。
        pending_tc: tool_call_chunks 的待处理字典。

    Returns:
        工具调用列表。
    """
    tool_calls: list[dict[str, Any]] = []
    for tc_data in pending_tc.values():
        if tc_data.get("name"):  # 从 pending 中获取（可能不完整）
            name = tc_data["name"]
            args_str = tc_data.get("args", "{}")
            try:
                parsed_args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                parsed_args = {"raw": args_str} if args_str else {}
            tool_calls.append({
                "name": name,
                "args": parsed_args,
                "id": tc_data.get("id", ""),
            })
    return tool_calls


class CircuitBreakerOpenError(RuntimeError):
    """熔断器打开时抛出的异常，用于区分断路器拒绝和真实 LLM 故障。"""
    pass


class _LLMCircuitBreaker:
    """LLM 调用熔断器 — 防止级联故障。

    状态机：CLOSED → OPEN → HALF_OPEN → CLOSED/OPEN

    当连续失败超过阈值时打开电路，拒绝后续调用。
    经过恢复超时后进入半开状态，允许一次探测调用。
    探测成功则关闭电路，失败则重新打开。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 10.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failure_count = 0
        self._opened_at: float | None = None
        self._state = "closed"

    @property
    def is_open(self) -> bool:
        """电路是否打开（拒绝调用）。"""
        import time as _time
        if self._state == "closed":
            return False
        if self._state == "open":
            elapsed = _time.monotonic() - (self._opened_at or 0)
            if elapsed >= self._recovery_timeout:
                self._state = "half_open"
                logger.info("熔断器进入半开状态，允许探测调用")
                return False
            return True
        return False

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def state(self) -> str:
        return self._state

    def record_success(self) -> None:
        """记录成功调用。"""
        self._failure_count = 0
        if self._state == "half_open":
            self._state = "closed"
            self._opened_at = None
            logger.info("熔断器恢复关闭")

    def record_failure(self) -> None:
        """记录失败调用。"""
        self._failure_count += 1
        if self._state == "half_open" or (
            self._state == "closed" and self._failure_count >= self._failure_threshold
        ):
            self._state = "open"
            self._opened_at = __import__("time").monotonic()
            logger.warning(
                "熔断器打开 (failures=%d, threshold=%d, recovery=%.0fs)",
                self._failure_count,
                self._failure_threshold,
                self._recovery_timeout,
            )

    def reset(self) -> None:
        """手动重置断路器。"""
        self._failure_count = 0
        self._state = "closed"
        self._opened_at = None
        logger.info("熔断器已手动重置")


class ChatService:
    """统一对话服务。

    职责：
    1. 构建上下文（委托 ContextService）
    2. 调用 LLM + 工具调用循环
    3. 流式/非流式双模式
    4. 保存对话历史
    5. 可选记忆提取
    """

    def __init__(
        self,
        *,
        model_service: Any,
        context_service: Any,
        tool_manager: Any,
        memory_service: Any,
        chat_history_manager: Any,
        chat_llm: Any,
        thread_pool: Any,
    ) -> None:
        self._model_service = model_service
        self._context_service = context_service
        self._tool_manager = tool_manager
        self._memory_service = memory_service
        self._history_manager = chat_history_manager
        self._chat_llm = chat_llm
        self._thread_pool = thread_pool
        self._llm_breaker = _LLMCircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30.0,
        )

    # ── 非流式入口 ────────────────────────────────────────────

    async def chat(
        self,
        user_input: str,
        session_id: str,
        *,
        options: ChatOptions | None = None,
    ) -> ChatResult:
        """非流式对话（含完整工具循环）。

        流程:
        1. 拦截斜杠命令（如 /code-review）
        2. 构建 ContextBuildRequest
        3. context_service.abuild() 构建上下文
        4. 绑定工具 -> LLM ainvoke
        5. 工具调用循环 (max_rounds)
        6. 保存历史
        7. 可选记忆提取

        Args:
            user_input: 用户输入文本。
            session_id: 会话 ID。
            options: 对话选项，None 使用默认值。

        Returns:
            ChatResult 包含 content, tool_calls, iterations 等。
        """
        # 未指定或占位值时生成新会话 ID
        if not session_id or session_id == "default":
            session_id = str(uuid.uuid4())

        opts = options or ChatOptions(session_id=session_id)
        if opts.session_id is None or opts.session_id == "default":
            opts.session_id = session_id

        # 斜杠命令拦截
        skill_body = self._resolve_slash_command(user_input)

        try:
            # 1. 构建上下文
            request = ContextBuildRequest(
                messages=[HumanMessage(content=user_input)],
                session_id=session_id,
                enable_memory=opts.enable_memory,
                enable_tools=opts.enable_tools,
                enable_rag=opts.enable_rag,
                enable_agent=opts.enable_agent,
                custom_system_prompt=skill_body,
            )
            context_result = await self._context_service.abuild(request)

            # 2. 获取 LLM（支持按请求参数覆盖）
            llm = self._get_llm(opts)

            # 3. 绑定工具
            tools = self._get_available_tools(opts.tools)
            llm_with_tools = llm.bind_tools(tools) if tools else llm

            # 4. 工具调用循环
            messages = list(context_result.messages)
            response, new_messages, iterations = await self._execute_tool_loop(
                llm_with_tools, messages, opts.max_rounds
            )

            # 5. 保存历史
            await self._save_history(session_id, user_input, response, new_messages)

            # 6. 可选记忆提取
            if opts.extract_memory:
                await self._extract_memory(session_id, user_input, response)

            content = (
                response.content if isinstance(response, AIMessage) else str(response)
            )
            return ChatResult(
                content=content or "",
                session_id=session_id,
                tool_calls=self._extract_tool_calls(response),
                iterations=iterations,
                context_sources=_context_sources_to_dict(context_result.source_summary),
            )

        except Exception as e:
            logger.error("对话执行异常: %s", e, exc_info=True)
            return ChatResult(
                content="",
                session_id=session_id,
                error=str(e),
            )

    # ── 流式入口 ──────────────────────────────────────────────

    async def chat_stream(
        self,
        user_input: str,
        session_id: str,
        *,
        options: ChatOptions | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """流式对话（SSE 事件流）。

        Yields:
            SSE 事件字典 {"event": str, "data": dict}。
            事件类型: token, tool_call, tool_result, done, error。
        """
        # 未指定或占位值时生成新会话 ID
        if not session_id or session_id == "default":
            session_id = str(uuid.uuid4())

        opts = options or ChatOptions(session_id=session_id, streaming=True)
        if opts.session_id is None or opts.session_id == "default":
            opts.session_id = session_id

        # 斜杠命令拦截
        skill_body = self._resolve_slash_command(user_input)

        try:
            # 构建上下文
            ctx_request = ContextBuildRequest(
                messages=[HumanMessage(content=user_input)],
                session_id=session_id,
                enable_memory=opts.enable_memory,
                enable_tools=opts.enable_tools,
                enable_rag=opts.enable_rag,
                enable_agent=opts.enable_agent,
                custom_system_prompt=skill_body,
            )
            context_result = await self._context_service.abuild(ctx_request)

            # 产出 session 事件
            yield {
                "event": "session",
                "data": {"type": "session", "session_id": session_id},
            }

            # 获取可用工具列表
            tools = self._get_available_tools(opts.tools)
            logger.info(
                "可用工具: %d 个 (enable_tools=%s)",
                len(tools), opts.enable_tools,
            )
            messages = list(context_result.messages)

            # ── Agent 模式：规划阶段 ──
            plan_steps: list[dict[str, str]] = []
            recovery_manager = None
            if opts.enable_agent and tools:
                # 构建恢复管理器
                recovery_manager = self._build_recovery_manager(tools)

                # 插入 Agent 系统提示
                tools_info = [
                    {"name": t.name, "description": getattr(t, "description", "") or ""}
                    for t in tools
                ]
                agent_prompt = self._get_agent_system_prompt(tools_info)
                messages.append(SystemMessage(content=agent_prompt))

                # 流式产出规划事件，同时捕获计划（含重试）
                async for plan_event in self._agent_planning_with_retry(
                    user_input, messages, opts
                ):
                    yield plan_event
                    if plan_event.get("event") == "plan_complete":
                        plan_steps = plan_event.get("data", {}).get("plan", [])
                        plan_error = plan_event.get("data", {}).get("error")
                        if plan_error:
                            logger.warning("规划阶段出错: %s", plan_error)

                # 将计划作为上下文追加到消息
                if plan_steps:
                    plan_text = "\n".join(
                        f"{s['step']}. **{s['title']}**：{s['description']}"
                        for s in plan_steps
                    )
                    messages.append(
                        HumanMessage(content=f"已制定以下执行计划：\n{plan_text}\n\n请按计划逐步执行，完成后汇报结果。")
                    )

            # 获取流式 LLM
            self._check_llm_breaker()
            llm = self._get_llm(opts, streaming=True)

            # 绑定工具（仅在 enable_tools 为 True 时）
            llm_with_tools = (
                llm.bind_tools(tools, tool_choice="auto")
                if (tools and opts.enable_tools)
                else llm
            )
            logger.info(
                "工具绑定完成: 总计 %d 个工具 bind_tools=%s enable_tools=%s",
                len(tools), tools and opts.enable_tools, opts.enable_tools,
            )

            # 流式调用 LLM — 逐 token 产出 SSE 事件
            full_content = ""
            tool_calls_raw: list[dict[str, Any]] = []
            pending_tc: dict[int, dict[str, Any]] = {}

            try:
                async for chunk in llm_with_tools.astream(messages):
                    # 产出 token 事件
                    if hasattr(chunk, "content") and chunk.content:
                        token = str(chunk.content)
                        if token:
                            full_content += token
                            yield {"event": "token", "data": {"type": "token", "content": token}}
                    # 收集 tool_call_chunks
                    if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                        for tc_chunk in chunk.tool_call_chunks:
                            idx = getattr(tc_chunk, "index", 0)
                            if idx not in pending_tc:
                                pending_tc[idx] = {"name": "", "args": "", "id": ""}
                            tc = pending_tc[idx]
                            if getattr(tc_chunk, "name", None):
                                tc["name"] = tc_chunk.name
                            if getattr(tc_chunk, "id", None):
                                tc["id"] = tc_chunk.id
                            if getattr(tc_chunk, "args", None):
                                tc["args"] += tc_chunk.args
                                yield {
                                    "event": "tool_call",
                                    "data": {
                                        "type": "tool_call",
                                        "name": tc["name"] or tc_chunk.name or "",
                                        "args_preview": tc_chunk.args[:200],
                                    },
                                }
                # LLM 调用成功，记录
                self._llm_breaker.record_success()
            except CircuitBreakerOpenError:
                raise
            except Exception as e:
                self._llm_breaker.record_failure()
                raise

            # 解析 tool_calls（来自流式 chunks）
            for tc_data in pending_tc.values():
                if tc_data["name"]:
                    try:
                        parsed_args = json.loads(tc_data["args"]) if tc_data["args"] else {}
                    except json.JSONDecodeError:
                        parsed_args = {"raw": tc_data["args"]}
                    tool_calls_raw.append({
                        "name": tc_data["name"],
                        "args": parsed_args,
                        "id": tc_data["id"],
                    })

            # 回退：部分 LLM 提供商不流式传输 tool_call_chunks，
            # 而是将完整 tool_calls 放在最后一个 chunk 的 additional_kwargs 中
            if not tool_calls_raw:
                tool_calls_raw = _extract_tool_calls_from_chunks(
                    full_content, pending_tc
                )

            logger.info(
                "LLM 首轮响应: content_len=%d tool_calls=%d pending_tc=%d",
                len(full_content), len(tool_calls_raw), len(pending_tc),
            )

            # 工具调用循环（流式模式下仍需执行）
            iterations = 0
            new_messages: list[AIMessage | ToolMessage] = []
            all_tool_calls: list[dict[str, Any]] = list(tool_calls_raw)

            current_response = AIMessage(content=full_content, tool_calls=tool_calls_raw)
            # 工具重试计数（按 tool_call_id 跟踪）
            tool_attempts: dict[str, int] = {}
            while tool_calls_raw and iterations < opts.max_rounds:
                iterations += 1
                messages.append(current_response)
                new_messages.append(current_response)

                for tc in tool_calls_raw:
                    tool_name = tc["name"]
                    tool_args = tc["args"]
                    tool_id = tc["id"]

                    # 工具调用进度日志
                    import time as _time
                    _t0 = _time.monotonic()
                    logger.info(
                        "开始执行工具: %s args=%s",
                        tool_name,
                        str(tool_args)[:200],
                    )

                    # MCP 工具使用较短超时（30s），其他工具使用默认（120s）
                    _tool_timeout = 30.0 if tool_name.startswith("mcp__") or tool_name.startswith("context7_") else None

                    # 带恢复的工具执行
                    attempt_key = f"{tool_id}/{tool_name}"
                    current_attempt = tool_attempts.get(attempt_key, 0)
                    exec_result = await self._execute_tool_with_recovery(
                        tool_name,
                        tool_args,
                        tool_id,
                        timeout=_tool_timeout,
                        recovery_manager=recovery_manager,
                        attempt=current_attempt,
                    )

                    result_str = exec_result["result"]
                    recovery_info = exec_result.get("recovery")
                    if recovery_info:
                        tool_attempts[attempt_key] = recovery_info.get("attempt", current_attempt + 1)
                        yield {
                            "event": "recovery_action",
                            "data": {
                                "type": "recovery_action",
                                "tool_name": tool_name,
                                "action": recovery_info.get("action", "unknown"),
                                "attempt": recovery_info.get("attempt", 1),
                                "fallback_tool": recovery_info.get("fallback_tool"),
                                "error": recovery_info.get("error"),
                            },
                        }

                    _elapsed = _time.monotonic() - _t0
                    logger.info(
                        "工具执行完成: %s 耗时 %.1fs, 结果长度 %d",
                        tool_name, _elapsed, len(result_str),
                    )

                    yield {
                        "event": "tool_result",
                        "data": {
                            "type": "tool_result",
                            "name": tool_name,
                            "id": tool_id,
                            "result": result_str[:500],
                        },
                    }

                    tool_msg = ToolMessage(content=result_str, tool_call_id=tool_id)
                    messages.append(tool_msg)
                    new_messages.append(tool_msg)

                # 流式获取下一轮 — 逐 token 产出
                self._check_llm_breaker()
                next_content = ""
                tool_calls_raw = []
                pending_tc_next: dict[int, dict[str, Any]] = {}

                try:
                    async for chunk in llm_with_tools.astream(messages):
                        if hasattr(chunk, "content") and chunk.content:
                            token = str(chunk.content)
                            if token:
                                next_content += token
                                yield {"event": "token", "data": {"type": "token", "content": token}}
                        if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                            for tc_chunk in chunk.tool_call_chunks:
                                idx = getattr(tc_chunk, "index", 0)
                                if idx not in pending_tc_next:
                                    pending_tc_next[idx] = {"name": "", "args": "", "id": ""}
                                tc = pending_tc_next[idx]
                                if getattr(tc_chunk, "name", None):
                                    tc["name"] = tc_chunk.name
                                if getattr(tc_chunk, "id", None):
                                    tc["id"] = tc_chunk.id
                                if getattr(tc_chunk, "args", None):
                                    tc["args"] += tc_chunk.args
                                    yield {
                                        "event": "tool_call",
                                        "data": {
                                            "type": "tool_call",
                                            "name": tc["name"] or tc_chunk.name or "",
                                            "args_preview": tc_chunk.args[:200],
                                        },
                                    }
                    self._llm_breaker.record_success()
                except CircuitBreakerOpenError:
                    raise
                except Exception as e:
                    self._llm_breaker.record_failure()
                    raise

                for tc_data in pending_tc_next.values():
                    if tc_data["name"]:
                        try:
                            parsed_args = json.loads(tc_data["args"]) if tc_data["args"] else {}
                        except json.JSONDecodeError:
                            parsed_args = {"raw": tc_data["args"]}
                        tool_calls_raw.append({
                            "name": tc_data["name"],
                            "args": parsed_args,
                            "id": tc_data["id"],
                        })

                # 回退：部分提供商不流式传输 tool_call_chunks
                if not tool_calls_raw:
                    tool_calls_raw = _extract_tool_calls_from_chunks(
                        next_content, pending_tc_next
                    )

                all_tool_calls.extend(tool_calls_raw)
                current_response = AIMessage(
                    content=next_content, tool_calls=tool_calls_raw
                )
                logger.info(
                    "工具循环第 %d 轮: next_content_len=%d new_tool_calls=%d total_tool_calls=%d",
                    iterations, len(next_content), len(tool_calls_raw), len(all_tool_calls),
                )

            # 保存历史
            final_content = (
                current_response.content
                if isinstance(current_response, AIMessage)
                else str(current_response)
            )

            # 若 LLM 未生成文本回复但执行了工具，生成工具执行摘要
            if not final_content and all_tool_calls:
                tool_names = list({tc["name"] for tc in all_tool_calls})
                final_content = (
                    f"已执行工具: {', '.join(tool_names)}\n"
                    f"共调用 {len(all_tool_calls)} 次，循环 {iterations} 轮。\n"
                    f"请求已完成，但 AI 未生成文本回复。"
                )
                logger.warning(
                    "工具执行完成但无文本回复: tools=%s iterations=%d",
                    tool_names, iterations,
                )
            await self._save_history(
                session_id, user_input, current_response, new_messages
            )

            # 可选记忆提取
            if opts.extract_memory:
                await self._extract_memory(session_id, user_input, current_response)

            # 完成事件
            yield {
                "event": "done",
                "data": {
                    "type": "done",
                    "content": final_content or "",
                    "session_id": session_id,
                    "tool_calls": all_tool_calls,
                    "iterations": iterations,
                    "plan": plan_steps,
                    "context_sources": _context_sources_to_dict(
                        context_result.source_summary
                    ),
                },
            }

        except CircuitBreakerOpenError:
            # 熔断器拒绝，不记录为失败（不是真实 LLM 故障）
            raise
        except Exception as e:
            self._llm_breaker.record_failure()
            logger.error("流式对话异常: %s", e, exc_info=True)
            yield {
                "event": "error",
                "data": {"error": str(e)},
            }

    # ── API 兼容入口 ──────────────────────────────────────────

    async def chat_with_messages(
        self,
        messages: list[dict[str, Any]],
        session_id: str | None = None,
        *,
        options: ChatOptions | None = None,
    ) -> ChatResult:
        """API 兼容入口 — 接收原始消息列表。

        从消息列表中提取最后一条用户消息，委托给 chat()。
        ContextService 通过 session_id 管理完整历史。

        Args:
            messages: 原始消息列表（dict 格式）。
            session_id: 会话 ID。
            options: 对话选项。

        Returns:
            ChatResult。
        """
        sid = session_id or str(uuid.uuid4())
        opts = options or ChatOptions(session_id=sid)

        # 提取最后一条用户消息
        user_input = ""
        for msg in reversed(messages):
            role = msg.get("role", "user")
            if role == "user":
                user_input = self._extract_text(msg.get("content", ""))
                break

        if not user_input:
            return ChatResult(
                content="",
                session_id=sid,
                error="没有找到用户消息",
            )

        return await self.chat(user_input, sid, options=opts)

    # ── 内部方法 ──────────────────────────────────────────────

    def _get_llm(self, options: ChatOptions, *, streaming: bool = False) -> Any:
        """获取 LLM 实例。

        如果 options 指定了 temperature 或 max_tokens，则按请求参数创建。
        否则使用容器预构建的 chat_llm。
        """
        if options.temperature is not None or options.max_tokens is not None:
            return self._model_service.get_chat_llm(
                temperature=options.temperature,
                max_tokens=options.max_tokens,
                streaming=streaming,
            )
        if streaming:
            return self._model_service.get_chat_llm(streaming=True)
        return self._chat_llm

    def _get_available_tools(self, tool_names: list[str] | None = None) -> list[Any]:
        """获取可用工具。

        Args:
            tool_names: 工具名称白名单，None 表示全部启用的工具。

        Returns:
            工具列表。
        """
        tools = self._tool_manager.list_tools(enabled_only=True)
        if tool_names is None:
            return tools
        return [t for t in tools if t.name in tool_names]

    async def _execute_tool_loop(
        self,
        llm_with_tools: Any,
        messages: list[Any],
        max_rounds: int,
    ) -> tuple[AIMessage, list[AIMessage | ToolMessage], int]:
        """执行工具调用循环。

        Args:
            llm_with_tools: 绑定了工具的 LLM 实例。
            messages: 消息列表（会被就地修改）。
            max_rounds: 最大循环轮数。

        Returns:
            (最终响应, 新消息列表, 循环轮数)
        """
        response: AIMessage = await llm_with_tools.ainvoke(messages)
        new_messages: list[AIMessage | ToolMessage] = []
        round_count = 0

        while response.tool_calls and round_count < max_rounds:
            round_count += 1
            messages.append(response)
            new_messages.append(response)

            for tc in response.tool_calls:
                result_str = await self._execute_single_tool(
                    tc["name"], tc["args"], tc["id"]
                )
                tool_msg = ToolMessage(content=result_str, tool_call_id=tc["id"])
                messages.append(tool_msg)
                new_messages.append(tool_msg)

            response = await llm_with_tools.ainvoke(messages)

        return response, new_messages, round_count

    async def _execute_single_tool(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_id: str,
        timeout: float | None = None,
    ) -> str:
        """执行单个工具调用并格式化结果。

        Args:
            tool_name: 工具名称。
            tool_args: 工具参数。
            tool_id: 工具调用 ID。
            timeout: 超时秒数，None 使用默认值。

        Returns:
            格式化的结果字符串（已截断）。
        """
        try:
            tool_result = await self._tool_manager.execute(
                tool_name, tool_args, timeout=timeout
            )
            result_str = (
                tool_result
                if isinstance(tool_result, str)
                else json.dumps(tool_result, ensure_ascii=False, default=str)
            )
            if len(result_str) > _TOOL_RESULT_MAX_LEN:
                result_str = result_str[:_TOOL_RESULT_MAX_LEN] + "\n...(已截断)"
            return result_str
        except Exception as e:
            return f"工具执行失败: {e}"

    async def _stream_llm(
        self,
        llm: Any,
        messages: list[Any],
    ) -> tuple[str, list[dict[str, Any]]]:
        """流式调用 LLM，收集完整内容和工具调用。

        Args:
            llm: LLM 实例。
            messages: 消息列表。

        Returns:
            (完整内容, 工具调用列表)
        """
        full_content = ""
        tool_calls: list[dict[str, Any]] = []

        async for chunk in llm.astream(messages):
            if isinstance(chunk, AIMessage):
                if chunk.content:
                    full_content += str(chunk.content)
                if chunk.tool_calls:
                    tool_calls.extend(chunk.tool_calls)

        return full_content, tool_calls

    async def _save_history(
        self,
        session_id: str,
        user_input: str,
        response: AIMessage,
        new_messages: list[AIMessage | ToolMessage],
    ) -> None:
        """保存对话历史。

        Args:
            session_id: 会话 ID。
            user_input: 用户输入。
            response: 最终 AI 响应。
            new_messages: 工具循环中产生的新消息。
        """
        try:
            self._history_manager.add_message(
                session_id, HumanMessage(content=user_input)
            )
            for msg in new_messages:
                self._history_manager.add_message(session_id, msg)
            self._history_manager.add_message(session_id, response)
        except Exception:
            logger.debug("保存对话历史失败", exc_info=True)

    async def _extract_memory(
        self,
        session_id: str,
        user_input: str,
        response: AIMessage,
    ) -> None:
        """可选：从对话中提取记忆。

        Args:
            session_id: 会话 ID。
            user_input: 用户输入。
            response: AI 响应。
        """
        try:
            content = (
                response.content if isinstance(response, AIMessage) else str(response)
            )
            candidates = await self._memory_service.aextract_from_conversation(
                user_input, content
            )
            if candidates:
                await self._thread_pool.run_io(
                    self._memory_service.save_extracted,
                    candidates,
                    session_id=session_id,
                )
        except Exception:
            pass

    # ── Agent 模式 ──────────────────────────────────────────────

    @staticmethod
    def _resolve_slash_command(user_input: str) -> str | None:
        """拦截斜杠命令，若匹配到技能则返回 SKILL.md 正文内容。

        例如用户输入 "/code-review" → 读取 skills/code-review/SKILL.md 的 body。

        Args:
            user_input: 用户输入文本。

        Returns:
            SKILL.md 的正文内容（不含 frontmatter），或 None（非斜杠命令/未匹配）。
        """
        if not user_input.startswith("/"):
            return None

        try:
            from src.ai.core.container import container
            from src.ai.core.skills.loader import split_frontmatter

            skill_svc = container.skill_container.skill_service()
            skill_index = skill_svc.match_slash_command(user_input)
            if skill_index is None:
                logger.debug("未匹配斜杠命令: %s", user_input)
                return None

            text = skill_index.source_path.read_text(encoding="utf-8")
            _meta, body = split_frontmatter(text)
            if not body:
                logger.warning("技能文件 body 为空: %s", skill_index.source_path)
                return None

            logger.info(
                "斜杠命令已匹配: %s → %s (body 长度=%d)",
                user_input, skill_index.name, len(body),
            )
            return f"## 技能: {skill_index.name}\n\n{body}"

        except Exception as e:
            logger.warning("斜杠命令解析失败: %s", e)
            return None

    @staticmethod
    def _get_agent_system_prompt(tools_info: list[dict[str, str]]) -> str:
        """返回 Agent 模式的系统提示，含可用工具清单。"""
        tool_descriptions = "\n".join(
            f"- **{t['name']}**: {t['description']}"
            for t in tools_info
        )
        return (
            "你是一个自主智能 Agent，负责分析用户需求并自动完成任务。\n\n"
            "## 工作流程\n"
            "1. **分析需求**：理解用户想要什么\n"
            "2. **制定计划**：列出需要执行的步骤和需要的工具\n"
            "3. **逐步执行**：按计划调用工具，观察结果，调整策略\n"
            "4. **总结汇报**：完成后向用户汇报执行结果\n\n"
            "## 可用工具\n"
            f"{tool_descriptions}\n\n"
            "## 规则\n"
            "- 先用 `todo_write` 记录任务清单，完成一项标记一项\n"
            "- 使用工具前先思考：这个工具是否必要？参数是否正确？\n"
            "- 工具返回结果后分析是否达到预期，未达到则调整方案\n"
            "- 执行完成后向用户清晰汇报结果"
        )

    @staticmethod
    async def _retry_with_backoff(
        fn: Any,
        *args: Any,
        max_retries: int = 3,
        base_delay: float = 1.0,
        retryable_errors: tuple = (),
        **kwargs: Any,
    ) -> Any:
        """通用异步重试助手 — 指数退避重试。

        Args:
            fn: 异步可调用对象。
            max_retries: 最大重试次数。
            base_delay: 基础延迟（秒），实际延迟 = base * 2^attempt。
            retryable_errors: 可重试的异常类型元组，空表示全部重试。
            *args, **kwargs: 传递给 fn 的参数。

        Returns:
            fn 的返回值。

        Raises:
            最后一次失败的异常（如果全部重试失败）。
        """
        import asyncio

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "重试 (%d/%d): 延迟 %.1fs 后重试",
                    attempt, max_retries, delay,
                )
                await asyncio.sleep(delay)
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if retryable_errors and not isinstance(e, retryable_errors):
                    raise
                if attempt >= max_retries:
                    logger.error("重试耗尽 (%d 次): %s", max_retries, e)
                    raise
                logger.debug("第 %d 次尝试失败: %s", attempt + 1, e)
        raise last_error  # type: ignore[misc]

    async def _agent_planning_with_retry(
        self,
        user_input: str,
        context_messages: list[BaseMessage],
        opts: ChatOptions,
        *,
        max_retries: int = 2,
        base_delay: float = 1.0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Agent 规划阶段（含重试）。

        先尝试标准规划，如果解析结果为空计划，则用更详细的提示词重试。
        最多重试 max_retries 次，使用指数退避。

        Yields:
            thinking / plan_complete SSE 事件字典。
        """
        import asyncio

        all_thinking_content = ""
        all_plan_steps: list[dict[str, str]] = []

        for attempt in range(max_retries + 1):
            if attempt > 0:
                # 重试前通知用户
                delay = base_delay * (2 ** (attempt - 1))
                yield {
                    "event": "thinking",
                    "data": {
                        "type": "thinking",
                        "content": f"\n\n⚠️ 规划不完整，正在重新分析 (第 {attempt} 次重试)...\n",
                    },
                }
                await asyncio.sleep(delay)

            # 构建规划提示（第二次及以后使用更详细的提示）
            if attempt == 0:
                plan_prompt = (
                    "请分析以下用户需求，制定执行计划。\n\n"
                    "## 用户需求\n"
                    f"{user_input}\n\n"
                    "## 要求\n"
                    "先分析需求，然后列出具体的执行步骤。格式如下：\n\n"
                    "### 分析\n"
                    "（简要分析需求要点）\n\n"
                    "### 执行计划\n"
                    "1. **步骤名**：具体操作描述，使用的工具\n"
                    "2. **步骤名**：具体操作描述，使用的工具\n"
                    "...\n\n"
                    "### 预期结果\n"
                    "（最终产出什么）\n\n"
                    "现在开始分析。"
                )
            else:
                plan_prompt = (
                    "上次规划结果不完整，请重新分析并制定更详细的执行计划。\n\n"
                    "## 用户需求\n"
                    f"{user_input}\n\n"
                    "## 重要提示\n"
                    "- 务必使用数字编号（1. 2. 3.）列出每个步骤\n"
                    "- 每个步骤必须包含：**步骤名**、具体操作描述、使用的工具\n"
                    "- 步骤要具体、可执行，不能过于笼统\n\n"
                    "格式：\n"
                    "### 分析\n"
                    "（分析需求）\n\n"
                    "### 执行计划\n"
                    "1. **步骤名**：具体操作描述，使用的工具\n"
                    "2. **步骤名**：具体操作描述，使用的工具\n\n"
                    "### 预期结果\n"
                    "（预期产出）\n\n"
                    "请重新开始分析。"
                )

            thinking_content = ""
            planning_messages: list[BaseMessage] = list(context_messages)
            planning_messages.append(HumanMessage(content=plan_prompt))

            llm = self._get_llm(opts, streaming=True)

            if attempt == 0:
                yield {
                    "event": "thinking",
                    "data": {"type": "thinking", "content": "🔍 **分析需求中...**\n\n"},
                }

            try:
                async for chunk in llm.astream(planning_messages):
                    if hasattr(chunk, "content") and chunk.content:
                        token = str(chunk.content)
                        thinking_content += token
                        yield {
                            "event": "thinking",
                            "data": {"type": "thinking", "content": token},
                        }
            except Exception as e:
                logger.warning("规划 LLM 调用失败 (attempt %d): %s", attempt + 1, e)
                if attempt >= max_retries:
                    yield {
                        "event": "plan_complete",
                        "data": {
                            "type": "plan_complete",
                            "plan": [],
                            "thinking_content": all_thinking_content,
                            "error": f"规划阶段失败: {e}",
                        },
                    }
                    return
                continue

            # 解析计划
            plan_steps = self._translate_plan(thinking_content)
            all_thinking_content += thinking_content

            if plan_steps:
                all_plan_steps = plan_steps
                yield {
                    "event": "thinking",
                    "data": {
                        "type": "thinking",
                        "content": "\n\n---\n",
                        "plan_parsed": plan_steps,
                    },
                }
                yield {
                    "event": "plan_complete",
                    "data": {
                        "type": "plan_complete",
                        "plan": plan_steps,
                        "thinking_content": all_thinking_content,
                        "retry_count": attempt,
                    },
                }
                return
            else:
                logger.warning(
                    "规划解析为空 (attempt %d), thinking_content 长度=%d",
                    attempt + 1, len(thinking_content),
                )

        # 所有重试后仍无计划
        yield {
            "event": "plan_complete",
            "data": {
                "type": "plan_complete",
                "plan": all_plan_steps,
                "thinking_content": all_thinking_content,
                "error": "无法从规划中解析出有效步骤，将直接尝试执行。",
                "retry_count": max_retries,
            },
        }

    async def _execute_tool_with_recovery(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        tool_id: str,
        timeout: float | None = None,
        *,
        recovery_manager: Any | None = None,
        attempt: int = 0,
    ) -> dict[str, Any]:
        """执行单个工具（含恢复逻辑）。

        当 recovery_manager 不为 None 时，执行失败后尝试恢复策略：
        RETRY → FALLBACK → REPLAN/ASK_USER。

        Args:
            tool_name: 工具名称。
            tool_args: 工具参数。
            tool_id: 工具调用 ID。
            timeout: 超时秒数。
            recovery_manager: RecoveryManager 实例。
            attempt: 当前尝试次数。

        Returns:
            {"result": str, "recovery": dict|None} — 含结果和恢复信息。
        """
        from src.ai.core.tools.recovery import RecoveryStrategy

        try:
            result_str = await self._execute_single_tool(
                tool_name, tool_args, tool_id, timeout=timeout
            )
            # 检测结果是否为错误
            if result_str.startswith("工具执行失败:"):
                raise RuntimeError(result_str)
            return {"result": result_str, "recovery": None}

        except Exception as e:
            if recovery_manager is None:
                return {"result": f"工具执行失败: {e}", "recovery": None}

            logger.warning(
                "工具 %s 执行失败 (attempt %d): %s", tool_name, attempt, e
            )

            # 执行恢复
            recovery_result = await recovery_manager.execute_recovery(
                tool_name=tool_name,
                arguments=tool_args,
                error=e,
                attempt=attempt,
                execute_fn=lambda name, args: self._execute_single_tool(
                    name, args, tool_id, timeout=timeout
                ),
            )

            # 根据恢复结果返回
            action = recovery_result.get("action", "replan")
            if action in ("retry", "fallback"):
                result = recovery_result.get("result", str(recovery_result))
                return {
                    "result": result if isinstance(result, str) else str(result),
                    "recovery": {
                        "action": action,
                        "attempt": attempt + 1,
                        "fallback_tool": recovery_result.get("fallback_tool"),
                    },
                }
            elif action == "retry_failed":
                # 重试也失败了，反馈给 LLM
                return {
                    "result": f"工具 {tool_name} 重试失败: {e}",
                    "recovery": {
                        "action": "replan",
                        "attempt": attempt + 1,
                        "error": str(e),
                    },
                }
            elif action == "fallback_failed":
                return {
                    "result": f"工具 {tool_name} 及备选工具均失败: {e}",
                    "recovery": {
                        "action": "replan",
                        "attempt": attempt + 1,
                        "error": str(e),
                    },
                }
            elif action == "ask_user":
                return {
                    "result": recovery_result.get("message", f"工具 {tool_name} 执行失败: {e}"),
                    "recovery": {
                        "action": "ask_user",
                        "attempt": attempt + 1,
                    },
                }
            else:
                # replan 或其他
                return {
                    "result": recovery_result.get("message", f"工具 {tool_name} 执行失败: {e}"),
                    "recovery": {
                        "action": "replan",
                        "attempt": attempt + 1,
                        "error": str(e),
                    },
                }

    def _build_recovery_manager(self, tools: list[Any]) -> Any | None:
        """构建恢复管理器，配置工具回退映射。

        Returns:
            RecoveryManager 实例，如果无可配置项则返回 None。
        """
        from src.ai.core.tools.recovery import RecoveryConfig, RecoveryManager

        tool_names = {getattr(t, "name", "") for t in tools}

        # 构建回退映射：常用工具配置备选
        fallback_map: dict[str, str] = {}
        fallback_pairs = [
            ("file_read", "file_json_read"),
            ("glob_files", "grep"),
            ("web_fetch", "web_search"),
        ]
        for primary, fallback in fallback_pairs:
            if primary in tool_names and fallback in tool_names:
                fallback_map[primary] = fallback

        if not fallback_map:
            # 无可用回退映射，仍可进行 RETRY/REPLAN
            pass

        config = RecoveryConfig(
            max_retries=2,
            retry_delay_base=1.0,
            fallback_map=fallback_map,
        )
        return RecoveryManager(config=config)

    def _check_llm_breaker(self) -> None:
        """检查 LLM 熔断器状态，若电路打开则抛出 CircuitBreakerOpenError。"""
        if self._llm_breaker.is_open:
            raise CircuitBreakerOpenError(
                f"LLM 服务熔断中 (失败 {self._llm_breaker.failure_count} 次)，"
                f"请稍后重试。"
            )

    @staticmethod
    def _translate_plan(content: str) -> list[dict[str, str]]:
        """从思考内容中提取结构化计划步骤。

        尝试解析 Markdown 中的编号列表，每个步骤格式为：
        `N. **标题**：描述`

        Returns:
            步骤列表 [{"step": "1", "title": "标题", "description": "描述"}, ...]
        """
        import re

        steps: list[dict[str, str]] = []
        # 匹配 "1. **标题**：描述" 或 "1. 描述" 格式
        pattern = r"(\d+)[\.\)]\s*(?:\*\*(.+?)\*\*[:：]\s*)?(.+)"
        for match in re.finditer(pattern, content, re.MULTILINE):
            num = match.group(1)
            title = match.group(2) or ""
            desc = match.group(3).strip()
            steps.append({
                "step": num,
                "title": title,
                "description": desc,
            })
        return steps

    # ── 消息格式转换（API 兼容） ─────────────────────────────

    @staticmethod
    def convert_messages(messages: list[dict[str, Any]]) -> list[Any]:
        """转换消息格式为 LangChain 消息。

        支持多模态内容（文本 + 图像）。

        Args:
            messages: 原始消息列表。

        Returns:
            LangChain 消息列表。
        """
        lc_messages: list[Any] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(
                    SystemMessage(content=ChatService._extract_text(content))
                )
            elif role == "assistant":
                lc_messages.append(
                    AIMessage(content=ChatService._extract_text(content))
                )
            else:
                lc_messages.append(
                    HumanMessage(content=ChatService._convert_content(content))
                )
        return lc_messages

    @staticmethod
    def _extract_text(content: Any) -> str:
        """从内容中提取纯文本。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif hasattr(block, "type") and block.type == "text":
                    texts.append(block.text or "")
            return "\n".join(texts)
        return str(content)

    @staticmethod
    def _convert_content(content: Any) -> Any:
        """转换内容为 LangChain 格式（支持多模态）。"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            lc_content: list[dict[str, Any]] = []
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type", "text")
                    if block_type == "text":
                        lc_content.append(
                            {"type": "text", "text": block.get("text", "")}
                        )
                    elif block_type == "image_url":
                        lc_content.append(
                            {
                                "type": "image_url",
                                "image_url": block.get("image_url", {}),
                            }
                        )
                elif hasattr(block, "type"):
                    if block.type == "text":
                        lc_content.append({"type": "text", "text": block.text or ""})
                    elif block.type == "image_url":
                        lc_content.append(
                            {
                                "type": "image_url",
                                "image_url": block.image_url or {},
                            }
                        )
            return lc_content
        return str(content)


def _context_sources_to_dict(sources: list[Any]) -> list[dict[str, Any]]:
    """转换上下文来源摘要为 API/TUI 可序列化结构。"""
    return [
        {
            "source": item.source,
            "item_count": item.item_count,
            "token_count": item.token_count,
            "truncated": item.truncated,
            "cacheable": item.cacheable,
            "summary": item.summary,
        }
        for item in sources
    ]
