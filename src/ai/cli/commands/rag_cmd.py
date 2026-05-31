"""RAG 知识库管理子命令 — list / search / index / delete / clear / stats / sessions。"""

import typer
from pathlib import Path

rag_app = typer.Typer(help="RAG 知识库管理")


def _get_rag_service():
    """延迟获取 RAG 服务。"""
    from src.ai.core.container import container

    return container.rag_container.rag_service()


@rag_app.command("list")
def list_documents(
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
) -> None:
    """列出已索引文档。"""
    svc = _get_rag_service()
    docs = svc.list_documents(session_id=session)

    if not docs:
        typer.echo("  暂无已索引文档")
        return

    typer.echo(f"\n  共 {len(docs)} 个文档:\n")
    for doc in docs:
        title = doc.title or doc.source_path
        typer.echo(f"  {title}")
        typer.echo(f"    路径: {doc.source_path}")
        typer.echo(f"    分块: {doc.chunk_count}  类型: {doc.mime_type}")
    typer.echo()


@rag_app.command("search")
def search_documents(
    query: str = typer.Argument(..., help="搜索查询"),
    limit: int = typer.Option(5, "--limit", "-n", help="返回条数"),
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
) -> None:
    """向量相似度搜索。"""
    svc = _get_rag_service()
    results = svc.search(query, session_id=session, top_k=limit)

    if not results:
        typer.echo(f'  未找到与 "{query}" 相关的内容')
        return

    typer.echo(f'\n  搜索 "{query}" 结果:\n')
    for i, r in enumerate(results, 1):
        title = r.title or r.source_path
        typer.echo(f"  {i}. [{title}] (相关度: {r.score:.2f})")
        preview = r.content[:120].replace("\n", " ")
        typer.echo(f"    {preview}...")
    typer.echo()


@rag_app.command("index")
def index_path(
    path: str = typer.Argument(..., help="文件或目录路径"),
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
    reindex: bool = typer.Option(False, "--reindex", "-r", help="重新索引"),
) -> None:
    """索引文件或目录。"""
    svc = _get_rag_service()
    target = Path(path)

    if target.is_dir():
        docs = svc.index_directory(target, session_id=session, reindex=reindex)
        if not docs:
            typer.echo("  目录中无可索引文件")
            return
        typer.echo(f"  [OK] 已索引 {len(docs)} 个文件:")
        for doc in docs:
            typer.echo(f"    {doc.source_path} ({doc.chunk_count} 分块)")
    elif target.is_file():
        doc = svc.index_file(target, session_id=session, reindex=reindex)
        typer.echo(f"  [OK] 已索引: {doc.source_path} ({doc.chunk_count} 分块)")
    else:
        typer.echo(f"  [X] 路径不存在: {path}", err=True)
        raise typer.Exit(1)


@rag_app.command("delete")
def delete_document(
    path: str = typer.Argument(..., help="文件路径"),
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="跳过确认"),
) -> None:
    """删除指定文档。"""
    svc = _get_rag_service()

    if not force:
        confirm = typer.confirm(f'确认删除文档 "{path}" 的索引?')
        if not confirm:
            typer.echo("  已取消")
            return

    success = svc.delete_file(path, session_id=session)
    if success:
        typer.echo(f"  [OK] 已删除文档索引: {path}")
    else:
        typer.echo(f"  [X] 未找到文档: {path}", err=True)


@rag_app.command("clear")
def clear_knowledge_base(
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="跳过确认"),
) -> None:
    """清空知识库。"""
    svc = _get_rag_service()

    if not force:
        scope = f"会话 {session}" if session else "全局"
        confirm = typer.confirm(f"确认清空{scope}知识库?")
        if not confirm:
            typer.echo("  已取消")
            return

    count = svc.delete_all(session_id=session)
    typer.echo(f"  [OK] 已清空知识库，删除 {count} 个分块")


@rag_app.command("stats")
def knowledge_base_stats(
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
) -> None:
    """显示知识库统计信息。"""
    svc = _get_rag_service()
    stats = svc.get_stats(session_id=session)
    typer.echo("\n  知识库统计:")
    for key, value in stats.items():
        typer.echo(f"    {key}: {value}")
    typer.echo()


@rag_app.command("sessions")
def list_sessions() -> None:
    """列出所有会话级知识库。"""
    svc = _get_rag_service()
    sessions = svc.list_sessions()

    if not sessions:
        typer.echo("  暂无会话级知识库")
        return

    typer.echo(f"\n  共 {len(sessions)} 个会话级知识库:\n")
    for sid in sessions:
        typer.echo(f"  {sid}")
    typer.echo()
