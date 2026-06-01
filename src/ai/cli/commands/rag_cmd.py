"""RAG 知识库管理子命令 — list / search / index / delete / clear / stats / sessions / update / hybrid-search / context / chunks / batch-delete / delete-session / global-stats。"""

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


@rag_app.command("update")
def update_text(
    source_path: str = typer.Argument(..., help="原索引的 source_path"),
    text: str = typer.Argument(..., help="新的文本内容"),
    title: str = typer.Option(None, "--title", "-t", help="文档标题"),
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
) -> None:
    """更新已索引的文本内容。"""
    svc = _get_rag_service()
    doc = svc.update_text(
        text, source_path=source_path, title=title, session_id=session
    )
    typer.echo(f"  [OK] 已更新: {doc.source_path} ({doc.chunk_count} 分块)")


@rag_app.command("hybrid-search")
def hybrid_search(
    query: str = typer.Argument(..., help="搜索查询"),
    limit: int = typer.Option(5, "--limit", "-n", help="返回条数"),
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
) -> None:
    """混合搜索（向量 + BM25）。"""
    svc = _get_rag_service()
    results = svc.hybrid_search(query, session_id=session, top_k=limit)

    if not results:
        typer.echo(f'  未找到与 "{query}" 相关的内容')
        return

    typer.echo(f'\n  混合搜索 "{query}" 结果:\n')
    for i, r in enumerate(results, 1):
        title = r.title or r.source_path
        typer.echo(f"  {i}. [{title}] (相关度: {r.score:.4f})")
        preview = r.content[:120].replace("\n", " ")
        typer.echo(f"    {preview}...")
    typer.echo()


@rag_app.command("context")
def build_context(
    query: str = typer.Argument(..., help="搜索查询"),
    limit: int = typer.Option(5, "--limit", "-n", help="返回条数"),
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
) -> None:
    """构建 RAG 上下文文本。"""
    svc = _get_rag_service()
    context = svc.build_context(query, session_id=session, top_k=limit)

    if not context:
        typer.echo(f'  未找到与 "{query}" 相关的内容')
        return

    typer.echo("\n  RAG 上下文:\n")
    typer.echo(context)
    typer.echo()


@rag_app.command("chunks")
def view_chunks(
    path: str = typer.Argument(..., help="文档 source_path"),
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
) -> None:
    """查看文档的所有 chunks 详情。"""
    svc = _get_rag_service()
    chunks = svc.get_document_chunks(path, session_id=session)

    if not chunks:
        typer.echo(f"  [X] 未找到文档: {path}", err=True)
        return

    typer.echo(f"\n  文档 {path} 共 {len(chunks)} 个分块:\n")
    for c in chunks:
        preview = c["content"][:80].replace("\n", " ")
        typer.echo(f"  [{c['chunk_index']}] {c['id']}")
        typer.echo(f"      {preview}...")
    typer.echo()


@rag_app.command("batch-delete")
def batch_delete(
    paths: list[str] = typer.Argument(..., help="文件路径列表"),
    session: str = typer.Option(None, "--session", "-s", help="会话 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="跳过确认"),
) -> None:
    """批量删除多个文档。"""
    svc = _get_rag_service()

    if not force:
        confirm = typer.confirm(f"确认删除 {len(paths)} 个文档的索引?")
        if not confirm:
            typer.echo("  已取消")
            return

    results = svc.delete_documents_batch(paths, session_id=session)
    success = sum(1 for v in results.values() if v)
    fail = sum(1 for v in results.values() if not v)
    typer.echo(f"  [OK] 批量删除完成: 成功 {success}, 失败 {fail}")
    for path, ok in results.items():
        status = "OK" if ok else "FAIL"
        typer.echo(f"    [{status}] {path}")


@rag_app.command("delete-session")
def delete_session(
    session_id: str = typer.Argument(..., help="会话 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="跳过确认"),
) -> None:
    """删除会话及其知识库。"""
    svc = _get_rag_service()

    if not force:
        confirm = typer.confirm(f'确认删除会话 "{session_id}" 及其知识库?')
        if not confirm:
            typer.echo("  已取消")
            return

    success = svc.delete_session(session_id)
    if success:
        typer.echo(f"  [OK] 已删除会话: {session_id}")
    else:
        typer.echo(f"  [X] 会话不存在或删除失败: {session_id}", err=True)


@rag_app.command("global-stats")
def global_stats() -> None:
    """显示全局统计信息（跨所有会话）。"""
    svc = _get_rag_service()
    stats = svc.get_all_stats()

    typer.echo("\n  RAG 全局统计:")
    typer.echo(f"    默认知识库分块数: {stats['default_chunks']}")
    typer.echo(f"    总会话数: {stats['total_sessions']}")
    typer.echo(f"    总分块数: {stats['total_chunks']}")

    if stats["sessions"]:
        typer.echo("\n  会话详情:")
        for s in stats["sessions"]:
            typer.echo(
                f"    {s['session_id']}: "
                f"{s['document_count']} 文档, {s['total_chunks']} 分块"
            )
    typer.echo()
