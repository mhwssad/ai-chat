"""系统面板 — 运行状态、配置摘要和系统动作。"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab, TabLayoutSpec, TabSummary
from src.ai.cli.utils.theme import Icons


class SystemTab(BaseTab):
    """系统面板。"""

    name = "系统"
    hotkey = "0"
    layout = TabLayoutSpec(mode="system")

    def __init__(self, *, thread_pool: Any, system_service: Any) -> None:
        super().__init__(thread_pool)
        self._system_service = system_service
        self._cache_ttl = 5.0
        self._runtime_status: dict[str, Any] = {}
        self._config_summary: dict[str, Any] = {}
        self._generated_key: str = ""

    def register_commands(self, router: Any, tab_index: int) -> None:
        router.register(tab_index, "g", self._generate_key)
        router.register(tab_index, "r", self._refresh_now)

    def _load_data(self) -> None:
        self._runtime_status = self._system_service.get_runtime_status()
        self._config_summary = self._system_service.get_config_summary()

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._ensure_cache()
        text = Text()
        text.append("运行状态\n", style="subtitle")
        text.append(Icons.LINE * max(1, width - 4) + "\n", style="muted")

        if not self._runtime_status:
            text.append("  暂无系统状态\n", style="muted")
        else:
            model_status = str(self._runtime_status.get("model_status", "unknown"))
            scheduler_status = str(self._runtime_status.get("scheduler_status", "unknown"))
            memory_status = str(self._runtime_status.get("memory_status", "unknown"))
            tool_status = str(self._runtime_status.get("tool_status", "unknown"))
            thread_pool_status = str(
                self._runtime_status.get("thread_pool_status", "unknown")
            )
            text.append(
                f"  模型: {self._runtime_status.get('model_key', '未配置')}\n",
                style="value",
            )
            text.append(
                f"  模型状态: {_status_label(model_status)}\n",
                style=_status_style(model_status),
            )
            text.append(
                f"  后端: {self._runtime_status.get('model_backend', '')}\n",
                style="value",
            )
            text.append(
                f"  调度器: {_status_label(scheduler_status)}\n",
                style=_status_style(scheduler_status),
            )
            text.append(
                f"  记忆: {_status_label(memory_status)} / {self._runtime_status.get('memory_count', 0)} 条\n",
                style=_status_style(memory_status),
            )
            text.append(
                f"  工具: {_status_label(tool_status)} / {self._runtime_status.get('enabled_tool_count', 0)} 启用 / {self._runtime_status.get('tool_count', 0)} 总数\n",
                style=_status_style(tool_status),
            )
            text.append(
                f"  线程池: {_status_label(thread_pool_status)}\n",
                style=_status_style(thread_pool_status),
            )

            text.append("\n服务状态\n", style="subtitle")
            for name, status in [
                ("model", model_status),
                ("scheduler", scheduler_status),
                ("memory", memory_status),
                ("tools", tool_status),
                ("thread_pool", thread_pool_status),
            ]:
                text.append(f"  {name}: ", style="muted")
                text.append(f"{_status_label(status)}\n", style=_status_style(status))

            text.append(
                f"\n  记忆条数: {self._runtime_status.get('memory_count', 0)}\n",
                style="value",
            )
            text.append(
                f"  工具数量: {self._runtime_status.get('tool_count', 0)}\n",
                style="value",
            )

        if self._generated_key:
            text.append("\n最近生成的密钥\n", style="subtitle")
            text.append(f"  {self._generated_key}\n", style="highlight")

        return Panel(
            text,
            title=f"[title]{Icons.TAB_SYSTEM} 系统[/]",
            border_style="border",
        )

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        self._ensure_cache()
        text = Text()
        text.append("配置摘要\n\n", style="subtitle")
        if not self._config_summary:
            text.append("  暂无配置摘要\n", style="muted")
        else:
            for key, value in self._config_summary.items():
                text.append(f"  {key}: ", style="muted")
                text.append(f"{value}\n", style="value")
        return Panel(text, title="[title]系统配置[/]", border_style="border")

    def handle_input(self, key: str) -> bool:
        if key == "g":
            self._generate_key()
            return True
        if key == "r":
            self._refresh_now()
            return True
        return False

    def get_footer_commands(self) -> list[tuple[str, str]]:
        return [("g", "生成密钥"), ("r", "刷新")]

    def get_tab_header_lines(self) -> list[str]:
        model = self._runtime_status.get("model_key", "未配置") if self._runtime_status else "未配置"
        return [f"模型: {model}", "模式: 系统状态"]

    def get_summary(self) -> TabSummary:
        model = self._runtime_status.get("model_key", "未配置") if self._runtime_status else "未配置"
        scheduler = (
            "运行中"
            if self._runtime_status.get("scheduler_running")
            else self._runtime_status.get("scheduler_status", "已停止")
        )
        return TabSummary(
            title=self.name,
            mode=self.layout.mode,
            status=f"模型: {model}",
            metrics=(
                ("调度器", str(scheduler)),
                ("线程池", str(self._runtime_status.get("thread_pool_status", "-"))),
                ("工具", str(self._runtime_status.get("tool_count", 0))),
            ),
        )

    def _generate_key(self) -> None:
        self._generated_key = self._system_service.generate_encryption_key()
        self._set_status("[success][OK] 已生成新的 ENCRYPTION_KEY[/]")

    def _refresh_now(self) -> None:
        self._invalidate_cache()
        self._set_status("[info]系统状态已刷新[/]")


def _status_label(status: str) -> str:
    """转换服务状态为 TUI 展示文本。"""
    labels = {
        "available": "正常",
        "configured": "已配置",
        "not_configured": "未配置",
        "disabled": "已禁用",
        "stopped": "已停止",
        "not_started": "未启动",
        "error": "失败",
    }
    return labels.get(status, status)


def _status_style(status: str) -> str:
    """转换服务状态为 Rich 样式。"""
    if status in {"available", "configured"}:
        return "active"
    if status in {"not_configured", "disabled", "stopped", "not_started"}:
        return "warning"
    if status == "error":
        return "error"
    return "muted"
