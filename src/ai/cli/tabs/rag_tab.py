"""RAG 面板 — 知识库索引、检索和统计。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.sessions import SessionManager
from src.ai.cli.tabs import BaseTab, TabLayoutSpec, TabSummary
from src.ai.cli.utils.formatting import truncate, wrap_text
from src.ai.cli.utils.rich_components import create_styled_table
from src.ai.cli.utils.theme import Icons


class RagTab(BaseTab):
    """RAG 知识库面板。"""

    name = "RAG"
    hotkey = "6"
    layout = TabLayoutSpec(mode="resource")

    def __init__(
        self,
        *,
        thread_pool: Any,
        rag_service: Any,
        session_mgr: SessionManager,
    ) -> None:
        super().__init__(thread_pool)
        self._rag_service = rag_service
        self._session_mgr = session_mgr
        self._cache_ttl = 4.0
        self._view: str = "documents"
        self._use_session_scope: bool = True
        self._documents: list[Any] = []
        self._search_results: list[Any] = []
        self._sessions: list[str] = []
        self._stats: dict[str, Any] = {}
        self._global_stats: dict[str, Any] = {}
        self._context_preview: str = ""

    def register_commands(self, router: Any, tab_index: int) -> None:
        router.register(tab_index, "o", self._toggle_scope)
        router.register(tab_index, "i", lambda: self._request_input("索引路径: ", self._index_path))
        router.register(tab_index, "s", lambda: self._request_input("搜索关键词: ", self._search))
        router.register(tab_index, "h", lambda: self._request_input("混合搜索: ", self._hybrid_search))
        router.register(tab_index, "b", lambda: self._request_input("构建上下文: ", self._build_context))
        router.register(tab_index, "v", self._cycle_view)
        router.register(tab_index, "d", self._request_delete_selected)
        router.register(tab_index, "c", self._request_clear_scope)
        router.register(tab_index, "x", self._request_delete_session_scope)

    def _load_data(self) -> None:
        session_id = self._session_id if self._use_session_scope else None
        self._documents = self._rag_service.list_documents(session_id=session_id)
        self._stats = self._rag_service.get_stats(session_id=session_id)
        self._sessions = self._rag_service.list_sessions()
        self._global_stats = self._rag_service.get_all_stats()

    @property
    def _session_id(self) -> str | None:
        active = self._session_mgr.active_session
        return active.session_id if active else None

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._ensure_cache()
        if self._view == "documents":
            return self._render_documents(width, height)
        if self._view == "search":
            return self._render_search(width, height)
        if self._view == "sessions":
            return self._render_sessions(width, height)
        if self._view == "stats":
            return self._render_stats(width, height)
        return self._render_context(width)

    def _render_documents(self, width: int, height: int) -> Panel:
        title = f"文档列表 ({len(self._documents)} 个)"
        if not self._documents:
            text = Text()
            text.append(f"{title}\n", style="subtitle")
            text.append("  暂无已索引文档\n", style="muted")
            return Panel(text, title=f"[title]{Icons.TAB_RAG} RAG[/]", border_style="border")

        table = create_styled_table(
            title,
            [
                ("", "", 2),
                ("标题", "bold", 20),
                ("范围", "muted", 8),
                ("状态", "muted", 10),
                ("分块", "right", 8),
                ("类型", "muted", 10),
            ],
        )
        self._clamp_selection(len(self._documents))
        visible = max(1, height - 10)
        scroll = self._get_scroll_offset(visible, len(self._documents))
        for i in range(scroll, min(scroll + visible, len(self._documents))):
            doc = self._documents[i]
            pointer = Icons.POINTER if i == self._selected_index else " "
            title_text = truncate(doc.title or doc.source_path, max_len=20)
            scope = truncate(getattr(doc, "scope", "") or "-", max_len=8)
            status = truncate(getattr(doc, "status", "") or "-", max_len=10)
            mime = truncate(doc.mime_type or "-", max_len=10)
            row_style = "reverse" if i == self._selected_index else ""
            table.add_row(
                Text(pointer, style="bold green" if i == self._selected_index else ""),
                Text(title_text, style=row_style),
                Text(scope),
                Text(status),
                Text(str(doc.chunk_count)),
                Text(mime),
                style=row_style,
            )
        return Panel(table, title=f"[title]{Icons.TAB_RAG} RAG[/]", border_style="border")

    def _render_search(self, width: int, height: int) -> Panel:
        title = f"检索结果 ({len(self._search_results)} 条)"
        text = Text()
        text.append(f"{title}\n", style="subtitle")
        text.append(Icons.LINE * max(1, width - 4) + "\n", style="muted")
        if not self._search_results:
            text.append("  暂无检索结果\n", style="muted")
        else:
            self._clamp_selection(len(self._search_results))
            visible = max(1, height - 8)
            scroll = self._get_scroll_offset(visible, len(self._search_results))
            for i in range(scroll, min(scroll + visible, len(self._search_results))):
                row = self._search_results[i]
                prefix = Icons.POINTER if i == self._selected_index else " "
                score = getattr(row, "score", 0.0)
                text.append(f" {prefix} {truncate(row.title or row.source_path, max_len=max(20, width - 18))}\n", style="selected" if i == self._selected_index else "value")
                text.append(f"    相关度: {score:.4f}\n", style="muted")
                text.append(f"    {truncate(row.content.replace(chr(10), ' '), max_len=max(20, width - 8))}\n", style="muted")
        return Panel(text, title=f"[title]{Icons.TAB_RAG} RAG[/]", border_style="border")

    def _render_sessions(self, width: int, height: int) -> Panel:
        text = Text()
        text.append("会话级知识库\n", style="subtitle")
        text.append(Icons.LINE * max(1, width - 4) + "\n", style="muted")
        if not self._sessions:
            text.append("  暂无会话级知识库\n", style="muted")
        else:
            for sid in self._sessions[: max(1, height - 4)]:
                text.append(f"  {sid}\n", style="value")
        return Panel(text, title=f"[title]{Icons.TAB_RAG} RAG[/]", border_style="border")

    def _render_stats(self, width: int, height: int) -> Panel:
        text = Text()
        text.append("知识库统计\n", style="subtitle")
        text.append(Icons.LINE * max(1, width - 4) + "\n", style="muted")
        for key, value in self._stats.items():
            text.append(f"  {key}: {value}\n", style="value")
        text.append("\n全局统计\n", style="subtitle")
        for key in ("default_chunks", "total_sessions", "total_chunks"):
            if key in self._global_stats:
                text.append(f"  {key}: {self._global_stats[key]}\n", style="value")
        return Panel(text, title=f"[title]{Icons.TAB_RAG} RAG[/]", border_style="border")

    def _render_context(self, width: int) -> Panel:
        text = Text()
        text.append("上下文预览\n", style="subtitle")
        text.append(Icons.LINE * max(1, width - 4) + "\n", style="muted")
        if self._context_preview:
            for line in wrap_text(self._context_preview, max(20, width - 6))[:20]:
                text.append(f"  {line}\n", style="value")
        else:
            text.append("  暂无上下文预览\n", style="muted")
        return Panel(text, title=f"[title]{Icons.TAB_RAG} RAG[/]", border_style="border")

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        text = Text()
        text.append("详情\n\n", style="subtitle")
        if self._view == "documents" and self._documents:
            doc = self._documents[min(self._selected_index, len(self._documents) - 1)]
            text.append(f"  路径: {doc.source_path}\n", style="value")
            text.append(f"  标题: {doc.title or '-'}\n", style="value")
            text.append(f"  范围: {getattr(doc, 'scope', '-') or '-'}\n", style="value")
            text.append(f"  状态: {getattr(doc, 'status', '-') or '-'}\n", style="value")
            text.append(
                f"  集合: {getattr(doc, 'collection_name', '-') or '-'}\n",
                style="value",
            )
            text.append(f"  分块: {doc.chunk_count}\n", style="value")
            content_hash = getattr(doc, "content_hash", None)
            if content_hash:
                text.append(f"  哈希: {truncate(content_hash, 16)}\n", style="muted")
            chunks = self._rag_service.get_document_chunks(
                doc.source_path,
                session_id=self._session_id if self._use_session_scope else None,
            )
            text.append("\n  Chunks:\n", style="subtitle")
            for chunk in chunks[:8]:
                preview = truncate(
                    str(chunk["content"]).replace("\n", " "),
                    max_len=max(16, width - 8),
                )
                text.append(f"  [{chunk['chunk_index']}] {preview}\n", style="muted")
        elif self._view == "search" and self._search_results:
            row = self._search_results[min(self._selected_index, len(self._search_results) - 1)]
            text.append(f"  标题: {row.title or row.source_path}\n", style="value")
            text.append(f"  路径: {row.source_path}\n", style="value")
            text.append(f"  分块: {row.chunk_index}\n", style="value")
            text.append(f"  相关度: {row.score:.4f}\n", style="value")
            text.append("\n  内容:\n", style="subtitle")
            for line in wrap_text(row.content, max(18, width - 6))[:18]:
                text.append(f"  {line}\n", style="value")
        else:
            text.append("  选择项目查看详情\n", style="muted")
        return Panel(text, title="[title]RAG 详情[/]", border_style="border")

    def handle_input(self, key: str) -> bool:
        count = len(self._documents) if self._view == "documents" else len(self._search_results)
        if key == "up":
            self._move_selection(-1, count)
            return True
        if key == "down":
            self._move_selection(1, count)
            return True
        if key == "o":
            return self._toggle_scope()
        if key == "v":
            return self._cycle_view()
        if key == "d":
            self._request_delete_selected()
            return True
        if key == "c":
            self._request_clear_scope()
            return True
        if key == "x":
            self._request_delete_session_scope()
            return True
        return False

    def get_footer_commands(self) -> list[tuple[str, str]]:
        return [
            ("o", "切换范围"),
            ("i", "索引"),
            ("s", "搜索"),
            ("h", "混合搜"),
            ("b", "上下文"),
            ("v", "视图"),
            ("d", "删除"),
            ("c", "清空"),
        ]

    def get_tab_header_lines(self) -> list[str]:
        scope = self._session_id if self._use_session_scope and self._session_id else "全局"
        return [f"范围: {scope}", f"视图: {self._view}"]

    def get_summary(self) -> TabSummary:
        scope = self._session_id if self._use_session_scope and self._session_id else "全局"
        return TabSummary(
            title=self.name,
            mode=self.layout.mode,
            status=f"范围: {scope}",
            metrics=(
                ("视图", self._view),
                ("文档", str(len(self._documents))),
                ("会话库", str(len(self._sessions))),
            ),
        )

    def _toggle_scope(self) -> bool:
        self._use_session_scope = not self._use_session_scope
        self._invalidate_cache()
        scope = self._session_id if self._use_session_scope and self._session_id else "全局"
        self._set_status(f"[info]RAG 范围已切换: {scope}[/]")
        return True

    def _cycle_view(self) -> bool:
        views = ["documents", "search", "stats", "sessions", "context"]
        idx = views.index(self._view)
        self._view = views[(idx + 1) % len(views)]
        self._set_status(f"[info]RAG 视图: {self._view}[/]")
        return True

    def _index_path(self, value: str) -> None:
        path = Path(value.strip())
        if not path.exists():
            self._set_status(f"[error][X] 路径不存在: {value}[/]")
            return
        session_id = self._session_id if self._use_session_scope else None
        if path.is_dir():
            docs = self._rag_service.index_directory(path, session_id=session_id)
            self._set_status(f"[success][OK] 已索引目录，共 {len(docs)} 个文件[/]")
        else:
            doc = self._rag_service.index_file(path, session_id=session_id)
            self._set_status(f"[success][OK] 已索引: {doc.source_path}[/]")
        self._invalidate_cache()

    def _search(self, query: str) -> None:
        session_id = self._session_id if self._use_session_scope else None
        self._search_results = self._rag_service.search(query, session_id=session_id)
        self._view = "search"
        self._selected_index = 0
        self._set_status(f"[info]RAG 搜索完成: {query}[/]")

    def _hybrid_search(self, query: str) -> None:
        session_id = self._session_id if self._use_session_scope else None
        self._search_results = self._rag_service.hybrid_search(query, session_id=session_id)
        self._view = "search"
        self._selected_index = 0
        self._set_status(f"[info]RAG 混合搜索完成: {query}[/]")

    def _build_context(self, query: str) -> None:
        session_id = self._session_id if self._use_session_scope else None
        self._context_preview = self._rag_service.build_context(query, session_id=session_id)
        self._view = "context"
        self._set_status(f"[info]RAG 上下文已构建: {query}[/]")

    def _request_delete_selected(self) -> None:
        source_path = self._selected_source_path()
        if not source_path:
            self._set_status("[warning]当前没有可删除的文档[/]")
            return
        self._request_confirm(
            f'确认删除文档 "{truncate(source_path, 32)}"？',
            lambda: self._delete_source(source_path),
        )

    def _selected_source_path(self) -> str | None:
        if self._view == "documents" and self._documents:
            return self._documents[min(self._selected_index, len(self._documents) - 1)].source_path
        if self._view == "search" and self._search_results:
            return self._search_results[min(self._selected_index, len(self._search_results) - 1)].source_path
        return None

    def _delete_source(self, source_path: str) -> None:
        session_id = self._session_id if self._use_session_scope else None
        if self._rag_service.delete_file(source_path, session_id=session_id):
            self._invalidate_cache()
            self._set_status("[success][OK] RAG 文档已删除[/]")
        else:
            self._set_status("[error][X] 未找到待删除文档[/]")

    def _request_clear_scope(self) -> None:
        scope = self._session_id if self._use_session_scope and self._session_id else "全局"
        self._request_confirm(
            f"确认清空 {scope} 知识库？",
            self._clear_scope,
        )

    def _clear_scope(self) -> None:
        session_id = self._session_id if self._use_session_scope else None
        count = self._rag_service.delete_all(session_id=session_id)
        self._invalidate_cache()
        self._set_status(f"[success][OK] 已清空知识库，删除 {count} 个分块[/]")

    def _request_delete_session_scope(self) -> None:
        if not self._session_id:
            self._set_status("[warning]当前没有会话级知识库[/]")
            return
        self._request_confirm(
            f'确认删除会话 "{self._session_id}" 的知识库？',
            self._delete_session_scope,
        )

    def _delete_session_scope(self) -> None:
        if not self._session_id:
            return
        if self._rag_service.delete_session(self._session_id):
            self._invalidate_cache()
            self._set_status(f"[success][OK] 已删除会话知识库: {self._session_id}[/]")
        else:
            self._set_status("[error][X] 删除会话知识库失败[/]")
