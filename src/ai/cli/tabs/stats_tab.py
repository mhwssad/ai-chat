"""系统统计面板 — 模型调用、工具使用、Token 消耗等统计信息。"""

import logging

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab
from src.ai.cli.utils.theme import Icons
from src.ai.cli.utils.rich_components import create_styled_table

logger = logging.getLogger(__name__)

# 子视图标识
_VIEW_OVERVIEW = 0
_VIEW_MODELS = 1
_VIEW_TOOLS = 2

_VIEW_NAMES = ["概览", "模型详情", "工具统计"]


class StatsTab(BaseTab):
    """系统统计面板。

    展示模型调用统计、工具使用统计、Token 消耗和费用信息。
    """

    name = "统计"
    hotkey = "5"

    def __init__(self) -> None:
        super().__init__()
        self._cache_ttl = 10.0
        self._current_view: int = _VIEW_OVERVIEW

        # 统计数据
        self._model_stats: dict[str, object] = {}
        self._model_breakdown: list[dict[str, object]] = []
        self._tool_stats: list[dict[str, object]] = []
        self._memory_stats: dict[str, object] = {}

    def _load_data(self) -> None:
        """加载统计数据。"""
        try:
            from src.ai.core.container import container
            from src.ai.storage.runtime_repository import (
                ModelCallRepository,
                ToolCallRepository,
            )

            # 模型调用聚合统计
            with container.storage_container.session_factory() as session:
                model_repo = ModelCallRepository(session)
                self._model_stats = model_repo.get_aggregated_stats()
                self._model_breakdown = model_repo.get_stats_by_model()

                # 工具调用统计（手动聚合）
                tool_repo = ToolCallRepository(session)
                tool_calls = tool_repo.list(limit=1000)
                self._tool_stats = self._aggregate_tool_stats(tool_calls)

            # 记忆统计
            try:
                memory_svc = container.memory_container.memory_service()
                self._memory_stats = memory_svc.get_stats()
            except Exception:
                self._memory_stats = {}

        except Exception as e:
            logger.debug("加载统计数据失败: %s", e)
            self._model_stats = {}
            self._model_breakdown = []
            self._tool_stats = []
            self._memory_stats = {}

    def _aggregate_tool_stats(self, tool_calls: list) -> list[dict[str, object]]:
        """手动聚合工具调用统计。"""
        stats: dict[str, dict[str, object]] = {}
        for call in tool_calls:
            name = call.tool_name
            if name not in stats:
                stats[name] = {
                    "tool_name": name,
                    "calls": 0,
                    "success": 0,
                    "errors": 0,
                    "total_duration_ms": 0,
                }
            entry = stats[name]
            entry["calls"] = int(entry["calls"]) + 1  # type: ignore[operator]
            if call.status == "success":
                entry["success"] = int(entry["success"]) + 1  # type: ignore[operator]
            else:
                entry["errors"] = int(entry["errors"]) + 1  # type: ignore[operator]
            if call.duration_ms:
                entry["total_duration_ms"] = (
                    int(entry["total_duration_ms"]) + call.duration_ms
                )  # type: ignore[operator]

        # 按调用次数排序
        return sorted(stats.values(), key=lambda x: int(x["calls"]), reverse=True)

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._ensure_cache()

        text = Text()

        # 子视图切换提示
        text.append(" 视图: ", style="muted")
        for i, name in enumerate(_VIEW_NAMES):
            if i == self._current_view:
                text.append(f"[{i + 1}] {name} ", style="active")
            else:
                text.append(f"[{i + 1}] {name} ", style="muted")
        text.append("\n")
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")

        if self._current_view == _VIEW_OVERVIEW:
            self._render_overview(text, width, height)
        elif self._current_view == _VIEW_MODELS:
            self._render_model_details(text, width, height)
        elif self._current_view == _VIEW_TOOLS:
            self._render_tool_stats(text, width, height)

        return Panel(
            text,
            title=f"[title]{Icons.TAB_STATS} 统计[/]",
            border_style="border",
        )

    def _render_overview(self, text: Text, width: int, height: int) -> None:
        """渲染概览视图：指标卡片 + 模型分布表。"""
        stats = self._model_stats
        if not stats:
            text.append("\n  暂无统计数据\n", style="muted")
            text.append("  发送消息后自动生成统计\n", style="muted")
            return

        # 指标卡片
        text.append("\n")
        cards = [
            ("总调用", str(stats.get("total_calls", 0)), "info"),
            ("成功", str(stats.get("success_calls", 0)), "active"),
            ("失败", str(stats.get("error_calls", 0)), "error"),
            ("错误率", f"{stats.get('error_rate', 0):.1%}", "warning"),
        ]
        for label, value, style in cards:
            text.append(f" {label}: ", style="muted")
            text.append(f"{value}  ", style=style)

        text.append("\n\n")
        text.append(" Token 统计\n", style="subtitle")
        total_tokens = int(stats.get("total_tokens", 0))
        input_tokens = int(stats.get("total_input_tokens", 0))
        output_tokens = int(stats.get("total_output_tokens", 0))
        text.append(f"  总计: {self._format_number(total_tokens)}", style="value")
        text.append(f"  输入: {self._format_number(input_tokens)}", style="info")
        text.append(f"  输出: {self._format_number(output_tokens)}", style="active")
        text.append("\n")

        text.append("\n 费用与耗时\n", style="subtitle")
        total_cost = float(stats.get("total_cost", 0))
        avg_duration = stats.get("avg_duration_ms")
        text.append(f"  总费用: {total_cost:.4f}", style="value")
        if avg_duration:
            text.append(f"  平均耗时: {avg_duration:.0f}ms", style="value")
        text.append("\n")

        # 记忆统计
        if self._memory_stats:
            text.append("\n 记忆统计\n", style="subtitle")
            text.append(
                f"  总条目: {self._memory_stats.get('total', 0)}\n", style="value"
            )

        # 模型分布表
        if self._model_breakdown:
            text.append("\n")
            table = create_styled_table(
                "模型调用分布",
                [
                    ("模型", "bold", 20),
                    ("调用次数", "right", 10),
                    ("总 Token", "right", 12),
                    ("费用", "right", 10),
                ],
            )
            for item in self._model_breakdown[:10]:
                table.add_row(
                    str(item["model"]),
                    str(item["calls"]),
                    self._format_number(int(item["total_tokens"])),
                    f"{float(item['total_cost']):.4f}",
                )
            # 用 console.print 渲染 table 到 text 不方便，改用文本方式
            # 直接用 Text 渲染表格内容
            text.append(" 模型调用分布\n", style="subtitle")
            text.append(
                "  模型                  调用      Token     费用\n", style="muted"
            )
            text.append("  " + Icons.LINE * (width - 6) + "\n", style="muted")
            for item in self._model_breakdown[:10]:
                model = str(item["model"])
                if len(model) > 22:
                    model = model[:19] + "..."
                calls = str(item["calls"])
                tokens = self._format_number(int(item["total_tokens"]))
                cost = f"{float(item['total_cost']):.4f}"
                text.append(f"  {model:<24s}", style="value")
                text.append(f"{calls:>6s}", style="info")
                text.append(f"{tokens:>10s}", style="value")
                text.append(f"{cost:>10s}\n", style="muted")

    def _render_model_details(self, text: Text, width: int, height: int) -> None:
        """渲染模型详情视图。"""
        if not self._model_breakdown:
            text.append("\n  暂无模型调用记录\n", style="muted")
            return

        text.append("\n 模型详情\n\n", style="subtitle")
        for item in self._model_breakdown:
            model = str(item["model"])
            calls = int(item["calls"])
            tokens = int(item["total_tokens"])
            cost = float(item["total_cost"])

            text.append(f"  {model}\n", style="active")
            text.append(f"    调用: {calls}", style="value")
            text.append(f"  Token: {self._format_number(tokens)}", style="value")
            text.append(f"  费用: {cost:.4f}\n", style="muted")

    def _render_tool_stats(self, text: Text, width: int, height: int) -> None:
        """渲染工具统计视图。"""
        if not self._tool_stats:
            text.append("\n  暂无工具调用记录\n", style="muted")
            return

        text.append("\n 工具调用统计\n", style="subtitle")
        text.append(
            "  工具名称              调用    成功    失败    平均耗时\n", style="muted"
        )
        text.append("  " + Icons.LINE * (width - 6) + "\n", style="muted")

        for item in self._tool_stats[:20]:
            name = str(item["tool_name"])
            if len(name) > 20:
                name = name[:17] + "..."
            calls = int(item["calls"])
            success = int(item["success"])
            errors = int(item["errors"])
            total_dur = int(item["total_duration_ms"])
            avg_dur = f"{total_dur // calls}ms" if calls > 0 else "-"

            text.append(f"  {name:<22s}", style="value")
            text.append(f"{calls:>5d}", style="info")
            text.append(f"{success:>7d}", style="active")
            text.append(f"{errors:>7d}", style="error" if errors > 0 else "muted")
            text.append(f"  {avg_dur:>8s}\n", style="muted")

    def handle_input(self, key: str) -> bool:
        if key == "1":
            self._current_view = _VIEW_OVERVIEW
            return True
        elif key == "2":
            self._current_view = _VIEW_MODELS
            return True
        elif key == "3":
            self._current_view = _VIEW_TOOLS
            return True
        return False

    def get_footer_commands(self) -> list[tuple[str, str]]:
        """返回 Stats Tab 底部命令列表。"""
        return [("1", "概览"), ("2", "模型"), ("3", "工具")]

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        text = Text()
        stats = self._model_stats

        if not stats:
            text.append("  暂无统计数据", style="muted")
            return Panel(text, title="[title]统计详情[/]", border_style="border")

        text.append("详细统计\n\n", style="subtitle")

        # 成功率
        total = int(stats.get("total_calls", 0))
        success = int(stats.get("success_calls", 0))
        errors = int(stats.get("error_calls", 0))
        error_rate = float(stats.get("error_rate", 0))

        text.append("  调用统计\n", style="subtitle")
        text.append(f"  总调用: {total}\n", style="value")
        text.append(f"  成功: {success}\n", style="active")
        text.append(f"  失败: {errors}\n", style="error")
        text.append(f"  成功率: {(1 - error_rate):.1%}\n", style="value")

        # Token 详情
        text.append("\n  Token 详情\n", style="subtitle")
        text.append(
            f"  输入: {self._format_number(int(stats.get('total_input_tokens', 0)))}\n",
            style="info",
        )
        text.append(
            f"  输出: {self._format_number(int(stats.get('total_output_tokens', 0)))}\n",
            style="active",
        )
        text.append(
            f"  总计: {self._format_number(int(stats.get('total_tokens', 0)))}\n",
            style="value",
        )

        # 费用
        text.append("\n  费用\n", style="subtitle")
        total_cost = float(stats.get("total_cost", 0))
        text.append(f"  总费用: {total_cost:.6f}\n", style="value")
        if total > 0:
            text.append(f"  平均: {total_cost / total:.6f}/次\n", style="muted")

        # 耗时
        avg_dur = stats.get("avg_duration_ms")
        if avg_dur:
            text.append("\n  耗时\n", style="subtitle")
            text.append(f"  平均: {avg_dur:.0f}ms\n", style="value")

        return Panel(text, title="[title]统计详情[/]", border_style="border")

    @staticmethod
    def _format_number(n: int) -> str:
        """大数字格式化（1234 → 1.2K）。"""
        if n < 1000:
            return str(n)
        if n < 1_000_000:
            return f"{n / 1000:.1f}K"
        if n < 1_000_000_000:
            return f"{n / 1_000_000:.1f}M"
        return f"{n / 1_000_000_000:.1f}B"
