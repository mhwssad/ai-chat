"""定时任务管理子命令 — list / pause / resume / delete / logs / stats。"""

import typer

scheduler_app = typer.Typer(help="定时任务管理")


def _get_scheduler_service():
    """延迟获取调度服务。"""
    from src.ai.core.container import container

    return container.scheduler_container.scheduler_service()


@scheduler_app.command("list")
def list_tasks(
    status: str = typer.Option(
        None,
        "--status",
        "-s",
        help="按状态筛选（active/paused/completed/failed/disabled）",
    ),
    limit: int = typer.Option(50, "--limit", "-n", help="返回条数"),
) -> None:
    """列出定时任务。"""
    svc = _get_scheduler_service()

    from src.ai.core.scheduler.types import TaskStatus

    task_status = TaskStatus(status) if status else None
    tasks = svc.list_tasks(status=task_status, limit=limit)

    if not tasks:
        typer.echo("  暂无定时任务")
        return

    typer.echo(f"\n  共 {len(tasks)} 个任务:\n")
    for task in tasks:
        status_icon = {
            "active": "*",
            "paused": "[H]",
            "completed": "[OK]",
            "failed": "[X]",
            "disabled": "o",
        }.get(task.status.value, "?")
        typer.echo(
            f"  {status_icon} {task.name:<24s} [{task.status.value}]"
            f"  类型: {task.task_type.value}  总执行: {task.total_runs}"
        )
        if task.description:
            typer.echo(f"    {task.description[:60]}")
    typer.echo()


@scheduler_app.command("pause")
def pause_task(
    task_id: str = typer.Argument(..., help="任务 ID"),
) -> None:
    """暂停任务。"""
    svc = _get_scheduler_service()
    result = svc.pause_task(task_id)
    if result:
        typer.echo(f"  [OK] 已暂停任务: {result.name}")
    else:
        typer.echo("  [X] 操作失败（任务不存在或状态不允许）", err=True)


@scheduler_app.command("resume")
def resume_task(
    task_id: str = typer.Argument(..., help="任务 ID"),
) -> None:
    """恢复任务。"""
    svc = _get_scheduler_service()
    result = svc.resume_task(task_id)
    if result:
        typer.echo(f"  [OK] 已恢复任务: {result.name}")
    else:
        typer.echo("  [X] 操作失败（任务不存在或状态不允许）", err=True)


@scheduler_app.command("delete")
def delete_task(
    task_id: str = typer.Argument(..., help="任务 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="跳过确认"),
) -> None:
    """删除任务。"""
    svc = _get_scheduler_service()

    task = svc.get_task(task_id)
    if task is None:
        typer.echo(f"  [X] 任务不存在: {task_id}", err=True)
        return

    if not force:
        confirm = typer.confirm(f'确认删除任务 "{task.name}"?')
        if not confirm:
            typer.echo("  已取消")
            return

    success = svc.delete_task(task_id)
    if success:
        typer.echo(f"  [OK] 已删除任务: {task.name}")
    else:
        typer.echo("  [X] 删除失败", err=True)


@scheduler_app.command("logs")
def task_logs(
    task_id: str = typer.Argument(..., help="任务 ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="返回条数"),
) -> None:
    """查看任务执行日志。"""
    svc = _get_scheduler_service()
    logs = svc.get_task_logs(task_id, limit=limit)

    if not logs:
        typer.echo(f"  暂无执行日志: {task_id}")
        return

    typer.echo(f"\n  任务 {task_id} 最近 {len(logs)} 条日志:\n")
    for log in logs:
        status = log.get("status", "?")
        started = log.get("started_at", "?")
        duration = log.get("duration_ms")
        duration_str = f"{duration:.0f}ms" if duration else "-"
        summary = log.get("result_summary", "")
        error = log.get("error_message", "")

        status_icon = (
            "[OK]" if status == "success" else "[X]" if status == "failed" else "*"
        )
        typer.echo(f"  {status_icon} [{status}] {started} ({duration_str})")
        if summary:
            typer.echo(f"    {str(summary)[:80]}")
        if error:
            typer.echo(f"    错误: {str(error)[:80]}")
    typer.echo()


@scheduler_app.command("stats")
def scheduler_stats() -> None:
    """显示调度器统计信息。"""
    svc = _get_scheduler_service()
    stats = svc.get_stats()

    typer.echo("\n  调度器统计:")
    typer.echo(f"    运行中: {'是' if svc.is_running else '否'}")
    for key, value in stats.items():
        typer.echo(f"    {key}: {value}")
    typer.echo()
