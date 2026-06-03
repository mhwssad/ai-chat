"""定时任务面板 — 任务列表、状态切换、日志查看。"""

import logging

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.console import Group

from src.ai.cli.tabs import BaseTab
from src.ai.cli.utils.theme import Icons
from src.ai.cli.utils.formatting import (
    truncate,
    format_timestamp,
    format_status,
    format_duration,
)
from src.ai.cli.utils.rich_components import create_styled_table

logger = logging.getLogger(__name__)


class SchedulerTab(BaseTab):
    """定时任务面板。

    展示任务列表，支持暂停/恢复/删除操作和日志查看。
    """

    name = "任务"
    hotkey = "4"

    def __init__(self) -> None:
        super().__init__()
        self._cache_ttl = 3.0
        self._tasks: list[dict[str, object]] = []
        self._show_logs: bool = False
        self._selected_log_task: str | None = None

    def _load_data(self) -> None:
        """加载任务列表。"""
        try:
            from src.ai.core.container import container

            svc = container.scheduler_container.scheduler_service()
            tasks = svc.list_tasks(limit=100)
            self._tasks = []
            query = self._search_query.lower()
            for task in tasks:
                name = task.name
                desc = task.description or ""
                # 搜索过滤：按名称或描述匹配
                if query and query not in name.lower() and query not in desc.lower():
                    continue
                self._tasks.append(
                    {
                        "id": task.id,
                        "name": name,
                        "description": desc,
                        "status": task.status.value,
                        "task_type": task.task_type.value,
                        "cron_expr": task.cron_expr or "",
                        "interval_seconds": task.interval_seconds,
                        "one_shot": task.one_shot,
                        "enabled": task.enabled,
                        "total_runs": task.total_runs,
                        "success_runs": task.success_runs,
                        "failed_runs": task.failed_runs,
                        "last_run_at": task.last_run_at,
                        "next_run_at": task.next_run_at,
                        "created_at": task.created_at,
                    }
                )
        except Exception as e:
            logger.debug("加载任务列表失败: %s", e)
            self._tasks = []

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._ensure_cache()
        self._clamp_selection(len(self._tasks))

        # 调度器状态行
        status_text = Text()
        try:
            from src.ai.core.container import container

            svc = container.scheduler_container.scheduler_service()
            running = svc.is_running
            status_icon = Icons.RUNNING if running else Icons.INACTIVE
            status_text.append(
                f"调度器: {status_icon} {'运行中' if running else '已停止'}\n",
                style="active" if running else "inactive",
            )
        except Exception:
            status_text.append("调度器: 未知\n", style="muted")

        if self._show_logs and self._selected_log_task:
            # 日志视图保持 Text.append
            text = Text()
            text.append_text(status_text)
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            self._render_logs(text, width, height)
            return Panel(
                text,
                title=f"[title]{Icons.TAB_SCHEDULER} 定时任务[/]",
                border_style="border",
            )

        # 任务列表使用 Rich Table
        if self._search_query:
            title_info = f'搜索 "{self._search_query}" ({len(self._tasks)} 个)'
        else:
            title_info = f"任务列表 ({len(self._tasks)} 个)"

        if not self._tasks:
            text = Text()
            text.append_text(status_text)
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            text.append(f"\n  {title_info}\n", style="subtitle")
            text.append("  暂无定时任务\n", style="muted")
            text.append("\n")
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            text.append(
                "  UP/DN 浏览 | P 暂停/恢复 | D 删除 | L 查看日志 | S 调度器开关\n",
                style="muted",
            )
            return Panel(
                text,
                title=f"[title]{Icons.TAB_SCHEDULER} 定时任务[/]",
                border_style="border",
            )

        table = create_styled_table(
            title_info,
            [
                ("", "", 2),  # 指针
                ("状态", "center", 8),
                ("名称", "bold", 20),
                ("类型", "muted", 10),
                ("执行统计", "", 18),
                ("上次执行", "muted", 14),
            ],
        )

        # 滚动支持
        visible_count = max(1, height - 10)
        scroll = self._get_scroll_offset(visible_count, len(self._tasks))

        for i in range(scroll, min(scroll + visible_count, len(self._tasks))):
            task = self._tasks[i]
            pointer = Icons.POINTER if i == self._selected_index else " "
            status = str(task["status"])
            name = truncate(str(task["name"]), max_len=22)
            task_type = str(task["task_type"])
            total = task["total_runs"]
            success = task["success_runs"]
            failed = task["failed_runs"]
            last_run = format_timestamp(task["last_run_at"])  # type: ignore[arg-type]

            stats_text = f"{total}次 [OK]{success} [X]{failed}"

            row_style = "reverse" if i == self._selected_index else ""
            table.add_row(
                Text(pointer, style="bold green" if i == self._selected_index else ""),
                Text(format_status(status)),
                Text(name, style=row_style),
                Text(task_type),
                Text.from_markup(stats_text),
                Text(last_run),
                style=row_style,
            )

        # 底部操作提示
        text = Text()
        text.append_text(status_text)
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")

        return Panel(
            Group(text, table),
            title=f"[title]{Icons.TAB_SCHEDULER} 定时任务[/]",
            border_style="border",
        )

    def _render_logs(self, text: Text, width: int, height: int) -> None:
        """渲染日志视图。"""
        text.append(f"任务日志: {self._selected_log_task}\n", style="subtitle")
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")

        try:
            from src.ai.core.container import container

            svc = container.scheduler_container.scheduler_service()
            logs = svc.get_task_logs(str(self._selected_log_task), limit=20)

            if not logs:
                text.append("  暂无执行日志\n", style="muted")
            else:
                for log in logs:
                    status = log.get("status", "?")
                    started = log.get("started_at", "?")
                    duration = log.get("duration_ms")
                    duration_str = (
                        format_duration(duration / 1000)
                        if duration is not None
                        else "-"
                    )
                    summary = log.get("result_summary", "")
                    error = log.get("error_message", "")

                    status_display = format_status(status)
                    text.append(f"  {status_display} ", style="")
                    text.append(f"{started}", style="muted")
                    text.append(f" ({duration_str})\n", style="muted")

                    if summary:
                        text.append(
                            f"    {truncate(str(summary), width - 10)}\n", style="value"
                        )
                    if error:
                        text.append(
                            f"    错误: {truncate(str(error), width - 14)}\n",
                            style="error",
                        )
        except Exception as e:
            logger.debug("加载日志失败: %s", e)
            text.append("  无法加载日志\n", style="error")

        text.append("\n", style="")
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")
        text.append("  Esc 返回任务列表\n", style="muted")

    def handle_input(self, key: str) -> bool:
        if self._show_logs:
            if key == "escape":
                self._show_logs = False
                self._selected_log_task = None
                return True
            return False

        if key == "escape":
            if self.is_searching:
                self.clear_search()
                return True

        if key == "up":
            self._move_selection(-1, len(self._tasks))
            return True
        elif key == "down":
            self._move_selection(1, len(self._tasks))
            return True
        elif key == "p":
            return self._toggle_pause()
        elif key == "d":
            return self._delete_selected()
        elif key == "l":
            self._show_selected_logs()
            return True
        elif key == "s":
            return self._toggle_scheduler()
        return False

    def _toggle_pause(self) -> bool:
        """暂停/恢复选中的任务。"""
        if not self._tasks or self._selected_index >= len(self._tasks):
            return False

        task = self._tasks[self._selected_index]
        task_id = str(task["id"])
        status = str(task["status"])

        try:
            from src.ai.core.container import container

            svc = container.scheduler_container.scheduler_service()
            if status == "active":
                svc.pause_task(task_id)
            elif status == "paused":
                svc.resume_task(task_id)
            self._invalidate_cache()
            return True
        except Exception as e:
            logger.debug("暂停/恢复任务失败: %s", e)
            return False

    def _delete_selected(self) -> bool:
        """删除选中的任务。"""
        if not self._tasks or self._selected_index >= len(self._tasks):
            return False

        task = self._tasks[self._selected_index]
        try:
            from src.ai.core.container import container

            svc = container.scheduler_container.scheduler_service()
            svc.delete_task(str(task["id"]))
            self._selected_index = max(0, self._selected_index - 1)
            self._invalidate_cache()
            return True
        except Exception as e:
            logger.debug("删除任务失败: %s", e)
            return False

    def _show_selected_logs(self) -> None:
        """显示选中任务的日志。"""
        if not self._tasks or self._selected_index >= len(self._tasks):
            return

        task = self._tasks[self._selected_index]
        self._selected_log_task = str(task["id"])
        self._show_logs = True

    def _toggle_scheduler(self) -> bool:
        """切换调度器运行状态（后台线程执行）。"""
        try:
            from src.ai.core.container import container

            svc = container.scheduler_container.scheduler_service()
            running = svc.is_running

            import threading

            def _run() -> None:
                try:
                    import asyncio

                    if running:
                        asyncio.run(svc.stop())
                    else:
                        asyncio.run(svc.start())
                except Exception as e:
                    logger.debug("切换调度器状态失败: %s", e)
                finally:
                    self._invalidate_cache()

            threading.Thread(target=_run, daemon=True).start()
            return True
        except Exception as e:
            logger.debug("切换调度器状态失败: %s", e)
            return False

    def get_footer_commands(self) -> list[tuple[str, str]]:
        """返回 Scheduler Tab 底部命令列表。"""
        return [("p", "暂停/恢复"), ("d", "删除"), ("l", "日志"), ("s", "调度器")]

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        text = Text()

        if not self._tasks or self._selected_index >= len(self._tasks):
            text.append("  选择一个任务查看详情", style="muted")
        else:
            task = self._tasks[self._selected_index]
            text.append("任务详情\n\n", style="subtitle")
            text.append(f"  ID: {task['id']}\n", style="value")
            text.append(f"  名称: {task['name']}\n", style="value")
            text.append(f"  描述: {task['description']}\n", style="value")
            text.append(f"  状态: {format_status(str(task['status']))}\n", style="")
            text.append(f"  类型: {task['task_type']}\n", style="value")
            text.append(f"  启用: {'是' if task['enabled'] else '否'}\n", style="value")

            # 调度信息
            text.append("\n调度信息\n", style="subtitle")
            if task["cron_expr"]:
                text.append(f"  Cron: {task['cron_expr']}\n", style="value")
            if task["interval_seconds"]:
                text.append(f"  间隔: {task['interval_seconds']}秒\n", style="value")
            if task["one_shot"]:
                text.append("  一次性: 是\n", style="value")

            # 执行统计
            text.append("\n执行统计\n", style="subtitle")
            text.append(f"  总执行: {task['total_runs']}\n", style="value")
            text.append(f"  成功: {task['success_runs']}\n", style="active")
            text.append(f"  失败: {task['failed_runs']}\n", style="error")
            text.append(
                f"  上次: {format_timestamp(task['last_run_at'])}\n",  # type: ignore[arg-type]
                style="value",
            )
            text.append(
                f"  下次: {format_timestamp(task['next_run_at'])}\n",  # type: ignore[arg-type]
                style="value",
            )
            text.append(
                f"  创建: {format_timestamp(task['created_at'])}\n",  # type: ignore[arg-type]
                style="muted",
            )

        return Panel(text, title="[title]任务详情[/]", border_style="border")
