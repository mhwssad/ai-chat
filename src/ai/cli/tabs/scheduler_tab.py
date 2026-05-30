"""定时任务面板 — 任务列表、状态切换、日志查看。"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab
from src.ai.cli.utils.theme import Icons
from src.ai.cli.utils.formatting import (
    truncate,
    format_timestamp,
    format_status,
    format_duration,
)


class SchedulerTab(BaseTab):
    """定时任务面板。

    展示任务列表，支持暂停/恢复/删除操作和日志查看。
    """

    name = "任务"
    hotkey = "4"

    def __init__(self) -> None:
        super().__init__()
        self._tasks: list[dict[str, object]] = []
        self._show_logs: bool = False
        self._selected_log_task: str | None = None

    def _load_tasks(self) -> None:
        """加载任务列表。"""
        try:
            from src.ai.core.container import container

            svc = container.scheduler_container.scheduler_service()
            tasks = svc.list_tasks(limit=100)
            self._tasks = []
            for task in tasks:
                self._tasks.append(
                    {
                        "id": task.id,
                        "name": task.name,
                        "description": task.description or "",
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
        except Exception:
            self._tasks = []

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._load_tasks()
        self._clamp_selection(len(self._tasks))

        text = Text()

        # 调度器状态
        try:
            from src.ai.core.container import container

            svc = container.scheduler_container.scheduler_service()
            running = svc.is_running
            status_icon = Icons.RUNNING if running else Icons.INACTIVE
            text.append(
                f"调度器: {status_icon} {'运行中' if running else '已停止'}\n",
                style="active" if running else "inactive",
            )
        except Exception:
            text.append("调度器: 未知\n", style="muted")

        text.append(Icons.LINE * (width - 4) + "\n", style="muted")

        if self._show_logs and self._selected_log_task:
            # 日志视图
            self._render_logs(text, width, height)
        else:
            # 任务列表
            text.append(f"任务列表 ({len(self._tasks)} 个)\n", style="subtitle")
            text.append(
                "  状态  名称                    类型        执行次数\n", style="muted"
            )
            text.append("  " + Icons.LINE * (width - 6) + "\n", style="muted")

            if not self._tasks:
                text.append("  暂无定时任务\n", style="muted")
            else:
                for i, task in enumerate(self._tasks):
                    prefix = Icons.POINTER if i == self._selected_index else " "
                    status = str(task["status"])
                    status_display = format_status(status)
                    name = truncate(str(task["name"]), max_len=22)
                    task_type = str(task["task_type"])
                    total = task["total_runs"]
                    success = task["success_runs"]
                    failed = task["failed_runs"]

                    line_style = "selected" if i == self._selected_index else ""
                    text.append(f" {prefix} ", style=line_style)
                    text.append(f"{status_display} ")
                    text.append(f"{name:<24s}", style=line_style)
                    text.append(f" {task_type:<12s}", style="muted")
                    text.append(f" {total}次 (✓{success} ✗{failed})\n", style="muted")

            # 操作提示
            text.append("\n", style="")
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            text.append(
                "  ↑↓ 浏览 │ P 暂停/恢复 │ D 删除 │ L 查看日志 │ S 调度器开关\n",
                style="muted",
            )

        return Panel(
            text,
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
                    duration_str = format_duration(duration / 1000) if duration else "-"
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
        except Exception:
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

        if key == "up":
            self._move_selection(-1, len(self._tasks))
            return True
        elif key == "down":
            self._move_selection(1, len(self._tasks))
            return True
        elif key == "p":
            self._toggle_pause()
            return True
        elif key == "d":
            self._delete_selected()
            return True
        elif key == "l":
            self._show_selected_logs()
            return True
        elif key == "s":
            self._toggle_scheduler()
            return True
        return False

    def _toggle_pause(self) -> None:
        """暂停/恢复选中的任务。"""
        if not self._tasks or self._selected_index >= len(self._tasks):
            return

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
        except Exception:
            pass

    def _delete_selected(self) -> None:
        """删除选中的任务。"""
        if not self._tasks or self._selected_index >= len(self._tasks):
            return

        task = self._tasks[self._selected_index]
        try:
            from src.ai.core.container import container

            svc = container.scheduler_container.scheduler_service()
            svc.delete_task(str(task["id"]))
            self._selected_index = max(0, self._selected_index - 1)
        except Exception:
            pass

    def _show_selected_logs(self) -> None:
        """显示选中任务的日志。"""
        if not self._tasks or self._selected_index >= len(self._tasks):
            return

        task = self._tasks[self._selected_index]
        self._selected_log_task = str(task["id"])
        self._show_logs = True

    def _toggle_scheduler(self) -> None:
        """切换调度器运行状态。"""
        try:
            import asyncio

            from src.ai.core.container import container

            svc = container.scheduler_container.scheduler_service()

            async def _toggle():
                if svc.is_running:
                    await svc.stop()
                else:
                    await svc.start()

            asyncio.run(_toggle())
        except Exception:
            pass

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
                f"  上次: {format_timestamp(task['last_run_at'])}\n", style="value"
            )
            text.append(
                f"  下次: {format_timestamp(task['next_run_at'])}\n", style="value"
            )
            text.append(
                f"  创建: {format_timestamp(task['created_at'])}\n", style="muted"
            )

        return Panel(text, title="[title]任务详情[/]", border_style="border")
