"""对话管理子命令 — list / create / delete / history。"""

import typer

chat_app = typer.Typer(help="对话管理")


def _get_history_manager():
    """延迟获取历史管理器。"""
    from src.ai.core.container import container

    return container.context_container.chat_history_manager()


@chat_app.command("list")
def list_sessions() -> None:
    """列出对话会话。"""
    # 使用 SessionManager 发现已有会话
    from src.ai.cli.sessions import SessionManager

    history_mgr = _get_history_manager()
    mgr = SessionManager(history_mgr)
    mgr.discover_existing_sessions()

    sessions = mgr.list_sessions()
    if not sessions:
        typer.echo("  暂无对话会话")
        return

    typer.echo(f"\n  共 {len(sessions)} 个会话:\n")
    for s in sessions:
        active = "●" if s.is_active else "○"
        typer.echo(f"  {active} {s.session_id:<24s} 消息: {s.message_count}")
    typer.echo()


@chat_app.command("create")
def create_session(
    session_id: str = typer.Argument(..., help="会话 ID"),
    name: str = typer.Option(None, "--name", help="显示名称"),
) -> None:
    """创建新会话。"""
    from src.ai.cli.sessions import SessionManager

    history_mgr = _get_history_manager()
    mgr = SessionManager(history_mgr)

    try:
        info = mgr.create_session(session_id=session_id, name=name)
        typer.echo(f"  ✓ 已创建会话: {info.session_id}")
    except ValueError as e:
        typer.echo(f"  ✗ {e}", err=True)


@chat_app.command("delete")
def delete_session(
    session_id: str = typer.Argument(..., help="会话 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="跳过确认"),
) -> None:
    """删除会话及其历史。"""
    from src.ai.cli.sessions import SessionManager

    history_mgr = _get_history_manager()
    mgr = SessionManager(history_mgr)

    # 先尝试发现已有会话
    mgr.discover_existing_sessions()

    if mgr.get_session(session_id) is None:
        typer.echo(f"  ✗ 会话不存在: {session_id}", err=True)
        return

    if not force:
        confirm = typer.confirm(f"确认删除会话「{session_id}」及其历史?")
        if not confirm:
            typer.echo("  已取消")
            return

    try:
        mgr.delete_session(session_id)
        typer.echo(f"  ✓ 已删除会话: {session_id}")
    except ValueError as e:
        typer.echo(f"  ✗ {e}", err=True)


@chat_app.command("history")
def session_history(
    session_id: str = typer.Argument(..., help="会话 ID"),
    limit: int = typer.Option(20, "--limit", "-n", help="显示条数"),
) -> None:
    """查看会话消息历史。"""
    history_mgr = _get_history_manager()

    try:
        messages = history_mgr.get_messages(session_id)
    except Exception:
        typer.echo(f"  ✗ 会话不存在或读取失败: {session_id}", err=True)
        return

    if not messages:
        typer.echo(f"  会话 {session_id} 暂无消息")
        return

    # 显示最近 N 条
    recent = messages[-limit:]
    typer.echo(f"\n  会话 {session_id} 最近 {len(recent)} 条消息:\n")
    for msg in recent:
        role = msg.type
        content = str(msg.content)[:100]
        if role == "human":
            typer.echo(f"  你: {content}")
        elif role == "ai":
            typer.echo(f"  助手: {content}")
        elif role == "tool":
            typer.echo(f"  [工具结果] {content}")
        else:
            typer.echo(f"  [{role}] {content}")
    typer.echo()
