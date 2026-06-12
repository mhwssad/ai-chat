"""超时 ToolNode — 替代 LangGraph 预置 ToolNode，支持工具级超时和依赖分组并行。"""

from __future__ import annotations

import asyncio
from src.ai.config.logging_setup import get_logger
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import ToolNode

from src.ai.exception.tool_exception import ToolConfirmationRequiredError, ToolNotFoundError
from src.ai.core.tools.recovery import RecoveryManager, RecoveryStrategy

logger = get_logger(__name__)


def analyze_tool_dependencies(
    tool_calls: list[dict[str, Any]],
) -> list[list[int]]:
    """分析工具调用间的数据依赖，返回分组索引列表。

    同一组内的工具调用互相独立，可并行执行。
    组间存在依赖，需串行执行。

    依赖判断逻辑：
    - 如果工具 B 的参数值中包含工具 A 的 tool_call_id，则 B 依赖 A
    - 如果工具 B 的参数引用了占位符模式 `$tool_A.field`，则 B 依赖 A

    Args:
        tool_calls: AIMessage.tool_calls 列表。

    Returns:
        分组索引列表，每组是一个 index 列表。如 [[0, 2], [1]] 表示
        第 0、2 个调用并行，完成后执行第 1 个。
    """
    if not tool_calls:
        return []

    n = len(tool_calls)
    if n <= 1:
        return [list(range(n))]

    # 构建 ID → index 映射
    id_to_idx: dict[str, int] = {}
    for i, tc in enumerate(tool_calls):
        tc_id = tc.get("id", "")
        if tc_id:
            id_to_idx[tc_id] = i

    # 构建依赖图：dependency[i] = set of indices that i depends on
    dependency: list[set[int]] = [set() for _ in range(n)]

    for i, tc in enumerate(tool_calls):
        args_str = str(tc.get("args", {}))
        # 检查参数中是否引用了其他工具的 ID
        for tc_id, j in id_to_idx.items():
            if i != j and tc_id in args_str:
                dependency[i].add(j)
        # 检查占位符引用模式 $tool_name.field
        for j, other_tc in enumerate(tool_calls):
            if i != j:
                other_name = other_tc.get("name", "")
                if other_name and f"${other_name}." in args_str:
                    dependency[i].add(j)

    # 拓扑排序生成分组
    groups: list[list[int]] = []
    assigned: set[int] = set()

    while len(assigned) < n:
        # 找出当前所有依赖已满足的节点（未分配且依赖已全部分配）
        ready = [
            i
            for i in range(n)
            if i not in assigned and dependency[i].issubset(assigned)
        ]
        if not ready:
            # 存在循环依赖，将剩余节点全部放入一组
            ready = [i for i in range(n) if i not in assigned]
        groups.append(ready)
        assigned.update(ready)

    return groups


class TimeoutToolNode(ToolNode):
    """带超时和依赖分组的 ToolNode。

    继承 LangGraph ToolNode，在每个工具调用上包装 asyncio.wait_for()。
    支持依赖分析：无依赖的工具并行执行，有依赖的串行执行。

    Args:
        tools: 工具列表。
        default_timeout: 默认超时秒数（默认 120）。
        handle_tool_errors: 是否捕获工具异常（默认 True）。
        parallel_enabled: 是否启用依赖感知的分组并行（默认 True）。
        **kwargs: 传递给 ToolNode 的其他参数。
    """

    def __init__(
        self,
        tools: list,
        *,
        default_timeout: float = 120.0,
        handle_tool_errors: bool = True,
        tool_manager: Any | None = None,
        parallel_enabled: bool = True,
        recovery_manager: RecoveryManager | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(tools, handle_tool_errors=handle_tool_errors, **kwargs)
        self._default_timeout = default_timeout
        self._tool_manager = tool_manager
        self._parallel_enabled = parallel_enabled
        self._recovery_manager = recovery_manager

    async def _arun_one(  # type: ignore[override]
        self,
        call: dict[str, Any],
        input_type: str,
        config: Any,
    ) -> ToolMessage:
        """执行单个工具调用，带超时包装。

        Args:
            call: 工具调用信息（name, args, id）。
            input_type: 输入类型。
            config: LangChain 配置。

        Returns:
            工具执行结果消息。
        """
        name = call.get("name", "")
        call_id = call.get("id", "")
        arguments = call.get("args", {}) or {}

        try:
            if self._tool_manager is not None:
                result = await self._tool_manager.execute(
                    name,
                    arguments,
                    config=config,
                    timeout=self._default_timeout,
                )
                content = result if isinstance(result, str) else str(result)
                return ToolMessage(content=content, tool_call_id=call_id, name=name)

            return await asyncio.wait_for(
                super()._arun_one(call, input_type, config),  # type: ignore[arg-type]
                timeout=self._default_timeout,
            )  # type: ignore[return-value]
        except TimeoutError:
            logger.warning("工具 %s 执行超时 (%.1fs)", name, self._default_timeout)
            return ToolMessage(
                content=f"Error: 工具 {name} 执行超时 ({self._default_timeout}s)",
                tool_call_id=call_id,
                name=name,
            )
        except ToolConfirmationRequiredError as exc:
            logger.info("工具 %s 等待用户确认", name)
            return ToolMessage(
                content=f"ConfirmationRequired: {exc}",
                tool_call_id=call_id,
                name=name,
            )
        except Exception as e:
            # 其他异常由父类 handle_tool_errors 处理
            if not self.handle_tool_errors:  # type: ignore[attr-defined]
                raise

            # 尝试错误恢复
            if self._recovery_manager is not None:
                recovery_result = await self._try_recover(
                    name, arguments, e, call_id
                )
                if recovery_result is not None:
                    return recovery_result

            logger.error("工具 %s 执行异常: %s", name, str(e), exc_info=True)
            return ToolMessage(
                content=f"Error: {e}",
                tool_call_id=call_id,
                name=name,
            )

    async def ainvoke(
        self,
        input: dict[str, Any] | Any,
        config: Any = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """异步执行所有工具调用，支持依赖感知的分组并行。

        当 parallel_enabled=True 时，使用依赖分析器将工具调用分组：
        - 同一组内无依赖 → 并行执行
        - 组间有依赖 → 串行执行

        当 parallel_enabled=False 或仅一个调用时，行为与原版一致。

        Args:
            input: 输入状态（包含 messages）。
            config: LangChain 配置。
            **kwargs: 其他参数。

        Returns:
            包含 ToolMessage 列表的状态更新。
        """
        # 提取工具调用
        message = input.get("messages", [])[-1] if isinstance(input, dict) else input
        if not isinstance(message, AIMessage) or not message.tool_calls:
            return {"messages": []}

        input_type = "list" if isinstance(input, list) else "dict"
        tool_calls = message.tool_calls

        # 单个调用或禁用并行 → 直接并行（实际只有一个）
        if not self._parallel_enabled or len(tool_calls) <= 1:
            return await self._execute_group(tool_calls, input_type, config)

        # 依赖分析 → 分组
        groups = analyze_tool_dependencies(tool_calls)
        if len(groups) <= 1:
            # 无依赖或全部可并行
            return await self._execute_group(tool_calls, input_type, config)

        logger.debug(
            "工具依赖分组: %d 个调用分为 %d 组: %s",
            len(tool_calls),
            len(groups),
            groups,
        )

        # 按组串行执行，组内并行
        all_messages: list[ToolMessage] = []
        approval_pending = False

        for group in groups:
            group_calls = [tool_calls[i] for i in group]
            result = await self._execute_group(group_calls, input_type, config)
            all_messages.extend(result.get("messages", []))
            if result.get("user_approval_pending"):
                approval_pending = True

        return {
            "messages": all_messages,
            "user_approval_pending": approval_pending,
        }

    async def _try_recover(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        error: Exception,
        call_id: str,
    ) -> ToolMessage | None:
        """尝试错误恢复（RETRY / FALLBACK）。

        仅处理可在工具节点内透明恢复的策略（RETRY、FALLBACK）。
        REPLAN 和 ASK_USER 策略返回 None，让调用方按原逻辑处理。

        Args:
            tool_name: 失败的工具名称。
            arguments: 原始调用参数。
            error: 原始异常。
            call_id: 工具调用 ID。

        Returns:
            恢复成功返回 ToolMessage，无法恢复返回 None。
        """
        if self._recovery_manager is None:
            return None

        attempt = 0
        strategy = self._recovery_manager.decide_strategy(tool_name, error, attempt)

        # 仅 RETRY 和 FALLBACK 在此处理
        if strategy not in (RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK):
            return None

        execute_tool = self._make_execute_fn()
        result = await self._recovery_manager.execute_recovery(
            tool_name=tool_name,
            arguments=arguments,
            error=error,
            attempt=attempt,
            execute_fn=execute_tool,
        )

        action = result.get("action", "")
        if action in ("retry", "fallback") and "result" in result:
            content = result["result"]
            if not isinstance(content, str):
                content = str(content)
            logger.info(
                "工具 %s 恢复成功: action=%s", tool_name, action
            )
            return ToolMessage(
                content=content,
                tool_call_id=call_id,
                name=result.get("fallback_tool", tool_name),
            )

        return None

    def _make_execute_fn(self) -> Any:
        """创建供 RecoveryManager 使用的工具执行函数。"""

        async def execute_fn(name: str, args: dict[str, Any]) -> str:
            if self._tool_manager is not None:
                result = await self._tool_manager.execute(name, args)
                return result if isinstance(result, str) else str(result)
            # 回退：直接查找注册表中的工具并调用
            tool_by_name = self.tools_by_name  # type: ignore[attr-defined]
            tool = tool_by_name.get(name)
            if tool is None:
                raise ToolNotFoundError("备选工具不存在", context={"tool": name})
            result = await tool.ainvoke(args)
            return result if isinstance(result, str) else str(result)

        return execute_fn

    async def _execute_group(
        self,
        tool_calls: list[dict[str, Any]],
        input_type: str,
        config: Any,
    ) -> dict[str, Any]:
        """并行执行一组工具调用。

        Args:
            tool_calls: 本组的工具调用列表。
            input_type: 输入类型。
            config: LangChain 配置。

        Returns:
            包含 ToolMessage 列表的状态更新。
        """
        tasks = [
            self._arun_one(call, input_type, config)  # type: ignore[arg-type]
            for call in tool_calls
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        messages: list[ToolMessage] = []
        user_approval_pending = False
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                call = tool_calls[i]
                logger.error(
                    "工具 %s gather 异常: %s", call.get("name", ""), str(result)
                )
                messages.append(
                    ToolMessage(
                        content=f"Error: {result}",
                        tool_call_id=call.get("id", ""),
                        name=call.get("name", ""),
                    )
                )
            else:
                if isinstance(result.content, str) and result.content.startswith(
                    "ConfirmationRequired:"
                ):
                    user_approval_pending = True
                messages.append(result)  # type: ignore[arg-type]

        return {
            "messages": messages,
            "user_approval_pending": user_approval_pending,
        }
