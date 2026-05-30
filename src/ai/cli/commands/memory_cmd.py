"""记忆管理子命令 — list / search / delete / rebuild。"""

import typer

memory_app = typer.Typer(help="记忆管理")


def _get_memory_service():
    """延迟获取记忆服务。"""
    from src.ai.core.container import container

    return container.memory_container.memory_service()


@memory_app.command("list")
def list_memories(
    memory_type: str = typer.Option(
        None, "--type", "-t", help="按类型筛选（user/feedback/project/reference）"
    ),
) -> None:
    """列出所有记忆条目。"""
    svc = _get_memory_service()

    mt = memory_type if memory_type else None
    entries = svc.list_entries(memory_type=mt)

    if not entries:
        typer.echo("  暂无记忆条目")
        return

    typer.echo(f"\n  共 {len(entries)} 条记忆:\n")
    for entry in entries:
        name = entry.name
        mt = entry.memory_type
        desc = entry.description[:60] if entry.description else ""
        typer.echo(f"  [{mt}] {name}")
        if desc:
            typer.echo(f"    {desc}")
    typer.echo()


@memory_app.command("search")
def search_memories(
    query: str = typer.Argument(..., help="搜索关键词"),
    limit: int = typer.Option(5, "--limit", "-n", help="返回条数"),
) -> None:
    """搜索记忆。"""
    svc = _get_memory_service()
    results = svc.search(query, limit=limit)

    if not results:
        typer.echo(f"  未找到与「{query}」相关的记忆")
        return

    typer.echo(f"\n  搜索「{query}」结果:\n")
    for r in results:
        typer.echo(
            f"  [{r.entry.memory_type}] {r.entry.name} (相关度: {r.score:.2f}, 匹配: {r.match_type})"
        )
        if r.entry.description:
            typer.echo(f"    {r.entry.description[:60]}")
    typer.echo()


@memory_app.command("delete")
def delete_memory(
    name: str = typer.Argument(..., help="记忆名称"),
    force: bool = typer.Option(False, "--force", "-f", help="跳过确认"),
) -> None:
    """删除指定记忆条目。"""
    svc = _get_memory_service()

    entry = svc.get(name)
    if entry is None:
        typer.echo(f"  ✗ 记忆不存在: {name}", err=True)
        return

    if not force:
        confirm = typer.confirm(f"确认删除记忆「{name}」?")
        if not confirm:
            typer.echo("  已取消")
            return

    success = svc.delete(name)
    if success:
        typer.echo(f"  ✓ 已删除记忆: {name}")
    else:
        typer.echo(f"  ✗ 删除失败: {name}", err=True)


@memory_app.command("rebuild")
def rebuild_index() -> None:
    """重建记忆索引（MEMORY.md）。"""
    svc = _get_memory_service()
    svc.rebuild_index()
    typer.echo("  ✓ 记忆索引已重建")


@memory_app.command("stats")
def memory_stats() -> None:
    """显示记忆统计信息。"""
    svc = _get_memory_service()
    stats = svc.get_stats()
    typer.echo("\n  记忆统计:")
    for key, value in stats.items():
        typer.echo(f"    {key}: {value}")
    typer.echo()
