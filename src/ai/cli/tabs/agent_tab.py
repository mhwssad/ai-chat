"""Agent 面板 — 任务执行与结果查看。"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.sessions import SessionManager
from src.ai.cli.tabs import BaseTab, TabLayoutSpec, TabSummary
from src.ai.cli.utils.formatting import truncate, wrap_text
from src.ai.cli.utils.theme import Icons
from src.ai.core.agent.types import AgentResult

logger = logging.getLogger(__name__)


class AgentTab(BaseTab):
    """Agent 执行面板。"""

    name = "Agent"
    hotkey = "2"
    layout = TabLayoutSpec(
        mode="execution",
        prefer_detail=True,
        main_ratio=5,
        detail_ratio=3,
        min_main_width=72,
        min_detail_width=36,
    )

    def __init__(
        self,
        *,
        thread_pool: Any,
        agent_orchestrator: Any,
        session_mgr: SessionManager,
    ) -> None:
        super().__init__(thread_pool)
        self._agent = agent_orchestrator
        self._session_mgr = session_mgr
        self._current_task_text: str = ""
        self._max_iterations: int = 10
        self._running: bool = False
        self._result: AgentResult | None = None
        self._last_error: str = ""

    def register_commands(self, router: Any, tab_index: int) -> None:
        router.register(tab_index, "r", self._request_run)
        router.register(tab_index, "x", self._cancel_run)
        router.register(tab_index, "m", self._request_max_iterations)

    def _load_data(self) -> None:
        return None

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        text = Text()
        active = self._session_mgr.active_session
        text.append("任务执行\n", style="subtitle")
        text.append(Icons.LINE * max(1, width - 4) + "\n", style="muted")
        text.append(
            f"  会话: {active.name if active else '未选择'}\n",
            style="value" if active else "warning",
        )
        text.append(f"  最大迭代: {self._max_iterations}\n", style="value")
        status = "运行中" if self._running else "空闲"
        text.append(
            f"  状态: {status}\n",
            style="warning" if self._running else "muted",
        )
        text.append("\n当前任务\n", style="subtitle")
        text.append(
            f"  {self._current_task_text or '按 R 输入任务并开始执行'}\n",
            style="value" if self._current_task_text else "muted",
        )

        if self._last_error:
            text.append("\n最近错误\n", style="subtitle")
            for line in wrap_text(self._last_error, max(16, width - 6))[:6]:
                text.append(f"  {line}\n", style="error")

        if self._result is not None:
            text.append("\n执行结果\n", style="subtitle")
            text.append(f"  状态: {self._result.status.value}\n", style="value")
            text.append(f"  迭代: {self._result.iterations}\n", style="value")
            text.append(f"  工具调用: {len(self._result.tool_calls)}\n", style="value")
            text.append("\n结果内容\n", style="subtitle")
            for line in wrap_text(self._result.content or "", max(20, width - 6))[:12]:
                text.append(f"  {line}\n", style="value")

        return Panel(
            text,
            title=f"[title]{Icons.TAB_AGENT} Agent[/]",
            border_style="border",
        )

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        text = Text()
        text.append("执行详情\n\n", style="subtitle")
        if self._result is None:
            text.append("  暂无执行结果\n", style="muted")
        else:
            if self._result.plan:
                text.append("  计划模式输出:\n", style="subtitle")
                for line in wrap_text(self._result.plan, max(16, width - 6))[:10]:
                    text.append(f"  {line}\n", style="value")
                text.append("\n", style="")

            text.append("  上下文来源\n", style="subtitle")
            if not self._result.context_sources:
                text.append("  暂无来源摘要\n", style="muted")
            else:
                for item in self._result.context_sources[:8]:
                    source = item.get("source", "-")
                    count = item.get("item_count", 0)
                    tokens = item.get("token_count", 0)
                    truncated = " / 已裁剪" if item.get("truncated") else ""
                    text.append(
                        f"  {source}: {count} 项 / {tokens} tokens{truncated}\n",
                        style="value",
                    )
                    summary = item.get("summary") or ""
                    if summary:
                        text.append(
                            f"    {truncate(summary, max_len=max(16, width - 8))}\n",
                            style="muted",
                        )
                text.append("\n", style="")

            text.append("  执行轨迹\n", style="subtitle")
            if not self._result.trace:
                text.append("  暂无轨迹\n", style="muted")
            else:
                for step in self._result.trace[:12]:
                    marker = "[X]" if step.status in {"failed", "timeout"} else "[OK]"
                    text.append(
                        f"  {marker} {step.index}. {step.title}\n",
                        style="error" if step.error else "value",
                    )
                    for line in wrap_text(step.summary, max(16, width - 8))[:2]:
                        text.append(f"    {line}\n", style="muted")
                    if step.error:
                        text.append(
                            f"    {truncate(step.error, max_len=max(16, width - 12))}\n",
                            style="error",
                        )
                text.append("\n", style="")

            text.append("  工具调用\n", style="subtitle")
            if not self._result.tool_calls:
                text.append("  无工具调用\n", style="muted")
            else:
                for tc in self._result.tool_calls[:12]:
                    marker = "[X]" if tc.error else "[OK]"
                    text.append(
                        f"  {marker} {truncate(tc.name, max_len=max(10, width - 10))}\n",
                        style="error" if tc.error else "value",
                    )
                    if tc.error:
                        text.append(
                            f"    {truncate(tc.error, max_len=max(16, width - 12))}\n",
                            style="error",
                        )
                    elif tc.result:
                        text.append(
                            f"    {truncate(tc.result, max_len=max(16, width - 12))}\n",
                            style="muted",
                        )
        return Panel(text, title="[title]Agent 详情[/]", border_style="border")

    def handle_input(self, key: str) -> bool:
        if key == "r":
            self._request_run()
            return True
        if key == "x":
            return self._cancel_run()
        if key == "m":
            self._request_max_iterations()
            return True
        return False

    def get_footer_commands(self) -> list[tuple[str, str]]:
        return [("r", "运行"), ("x", "取消"), ("m", "迭代")]

    def get_tab_header_lines(self) -> list[str]:
        status = "运行中" if self._running else "空闲"
        return [f"状态: {status}", f"迭代上限: {self._max_iterations}"]

    def get_summary(self) -> TabSummary:
        status = "运行中" if self._running else "空闲"
        metrics = [("迭代上限", str(self._max_iterations))]
        if self._result is not None:
            metrics.extend(
                [
                    ("结果", self._result.status.value),
                    ("工具调用", str(len(self._result.tool_calls))),
                    ("上下文来源", str(len(self._result.context_sources))),
                ]
            )
        return TabSummary(
            title=self.name,
            mode=self.layout.mode,
            status=f"状态: {status}",
            metrics=tuple(metrics),
        )

    def _request_run(self) -> None:
        if self._running:
            self._set_status("[warning]Agent 正在运行[/]")
            return
        if self._session_mgr.active_session is None:
            self._set_status("[warning]请先选择会话[/]")
            return
        self._request_input("Agent 任务: ", self._start_run)

    def _request_max_iterations(self) -> None:
        self._request_input("最大迭代次数: ", self._set_max_iterations)

    def _set_max_iterations(self, value: str) -> None:
        try:
            parsed = int(value)
            if parsed <= 0:
                raise ValueError
        except ValueError:
            self._set_status("[error][X] 请输入有效的正整数[/]")
            return
        self._max_iterations = parsed
        self._set_status(f"[info]最大迭代次数已设置为 {parsed}[/]")

    def _start_run(self, task_text: str) -> None:
        task_text = task_text.strip()
        if not task_text:
            self._set_status("[warning]任务内容不能为空[/]")
            return
        active = self._session_mgr.active_session
        if active is None:
            self._set_status("[warning]请先选择会话[/]")
            return

        self._current_task_text = task_text
        self._running = True
        self._last_error = ""
        self._result = None
        self._set_status("[info]Agent 已开始执行[/]")

        def _run() -> None:
            try:
                result = asyncio.run(self._run_agent(active.session_id, task_text))
                self._result = result
                if result.status.value == "waiting_confirmation":
                    self._set_status("[warning]Agent 等待工具确认[/]")
                else:
                    self._set_status(
                        f"[success][OK] Agent 执行完成: {result.status.value}[/]"
                    )
            except Exception as exc:
                logger.exception("Agent 执行失败")
                self._last_error = str(exc)
                self._set_status(f"[error][X] Agent 执行失败: {exc}[/]")
            finally:
                self._running = False
                self._agent.set_confirm_handler(None)

        self._thread_pool.run_bg(_run)

    async def _run_agent(self, session_id: str, task_text: str) -> AgentResult:
        """运行 Agent，并为工具权限设置 TUI 确认回调。"""

        async def _confirm(tool_name: str, arguments: dict[str, Any]) -> bool:
            loop = asyncio.get_running_loop()
            future: asyncio.Future[bool] = loop.create_future()

            def _complete(confirmed: bool) -> None:
                def _set_result() -> None:
                    if not future.done():
                        future.set_result(confirmed)

                loop.call_soon_threadsafe(_set_result)

            self._request_confirm_decision(
                f"工具 {tool_name} 需要确认执行，是否允许？",
                _complete,
            )
            self._set_status(f"[warning]等待确认工具: {tool_name}[/]")
            return await future

        self._agent.set_confirm_handler(_confirm)
        return await self._agent.run(
            session_id=session_id,
            user_message=task_text,
            max_iterations=self._max_iterations,
        )

    def _cancel_run(self) -> bool:
        if not self._running:
            self._set_status("[warning]当前没有运行中的 Agent[/]")
            return False
        if self._agent.cancel():
            self._set_status("[info]已发送 Agent 取消请求[/]")
            return True
        self._set_status("[warning]Agent 取消失败[/]")
        return False
