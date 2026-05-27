"""统一记忆服务 — 集成文件系统记忆、对话历史和上下文构建。"""

import logging

from src.ai.config.settings import settings
from .extractor import MemoryExtractor
from .paths import MemoryPathResolver
from .prompt import MemoryPromptBuilder
from .store import MemoryStore
from .types import (
    ContextBuildRequest,
    ContextBuildResult,
    MemoryEntry,
    MemorySearchResult,
    MemoryType,
    MemoryWriteRequest,
)

logger = logging.getLogger(__name__)


class MemoryService:
    """统一记忆服务。

    文件系统为长期记忆存储（MEMORY.md 索引 + 详情文件），
    对话历史和上下文构建通过 LangChain 策略管理。
    """

    def __init__(
        self,
        *,
        store: MemoryStore | None = None,
        extractor: MemoryExtractor | None = None,
        prompt_builder: MemoryPromptBuilder | None = None,
    ) -> None:
        path_resolver = MemoryPathResolver()
        memory_dir = path_resolver.auto_memory_dir()

        self._store = store or MemoryStore(memory_dir)
        self._extractor = extractor or MemoryExtractor()
        self._prompt = prompt_builder or MemoryPromptBuilder()

        # 策略相关（延迟初始化）
        self._history_manager = None
        self._strategy = None
        self._context_builder = None
        self._file_store = None

    @property
    def store(self) -> MemoryStore:
        return self._store

    # ── 延迟初始化策略 ──────────────────────────────────────

    def _ensure_strategy(self) -> None:
        """确保策略和上下文构建器已初始化。"""
        if self._strategy is not None:
            return

        from .history import get_chat_history_manager
        from .strategies import create_memory_strategy

        # 如果启用文件存储，创建 FileHistoryStore
        if settings.memory.history_file_enabled and self._file_store is None:
            from .history_store import FileHistoryStore
            from src.ai.config.base_config import project_root

            self._file_store = FileHistoryStore(
                project_root / settings.memory.memory_dir
            )

        self._history_manager = get_chat_history_manager(file_store=self._file_store)

        from .llm_utils import get_chat_llm

        llm = get_chat_llm()
        self._strategy = create_memory_strategy(self._history_manager, llm=llm)
        logger.info("记忆策略已初始化: %s", self._strategy.strategy_name)

    def _ensure_context_builder(self) -> None:
        """确保上下文构建器已初始化。"""
        if self._context_builder is not None:
            return
        self._ensure_strategy()

        from .context import ContextBuilder

        # 如果配置了 RAG 优化，创建 RAG 编码器
        rag_encoder = None
        if settings.memory.rag_optimize_query:
            try:
                from .llm_utils import get_chat_llm
                from .rag_encoder import RAGQueryEncoder

                rag_encoder = RAGQueryEncoder(get_chat_llm())
            except Exception:
                logger.warning("RAG 编码器初始化失败", exc_info=True)

        self._context_builder = ContextBuilder(self._strategy, rag_encoder=rag_encoder)

    # ── 核心操作 ──────────────────────────────────────────────

    def save(self, request: MemoryWriteRequest, *, session_id: str | None = None) -> MemoryEntry:
        """保存记忆到文件系统。"""
        if not request.name:
            from hashlib import sha256
            import re

            hash_part = sha256(request.content.encode("utf-8")).hexdigest()[:8]
            slug = request.content[:30].replace(" ", "-")
            slug = re.sub(r"[^a-zA-Z0-9一-鿿-]+", "", slug)[:30]
            request.name = f"{request.memory_type}-{slug}-{hash_part}"

        if not request.description:
            request.description = request.content[:120].replace("\n", " ")

        entry = MemoryEntry(
            name=request.name,
            memory_type=request.memory_type,
            description=request.description,
            content=request.content,
            session_id=session_id,
            metadata=request.metadata,
        )

        file_path = self._store.write(entry)
        entry = MemoryEntry(
            name=entry.name,
            memory_type=entry.memory_type,
            description=entry.description,
            content=entry.content,
            file_path=file_path,
            session_id=session_id,
            created_at=entry.created_at,
            metadata=entry.metadata,
        )

        logger.info("记忆已保存: %s (%s) [session=%s]", entry.name, entry.memory_type, session_id or "default")
        return entry

    def get(self, name: str) -> MemoryEntry | None:
        """按 name 获取单个记忆。"""
        return self._store.get_by_name(name)

    def delete(self, name: str) -> bool:
        """删除记忆。"""
        success = self._store.delete(name)
        if success:
            logger.info("记忆已删除: %s", name)
        return success

    def list_entries(
        self, *, memory_type: MemoryType | None = None
    ) -> list[MemoryEntry]:
        """列出记忆条目。"""
        if memory_type:
            return self._store.list_by_type(memory_type)
        return self._store.list_all()

    # ── 搜索 ──────────────────────────────────────────────────

    def search(self, query: str, *, limit: int = 5) -> list[MemorySearchResult]:
        """搜索记忆（使用文件内容关键词匹配）。"""
        results = self._store.search_files(query, limit=limit)
        return [
            MemorySearchResult(entry=entry, score=score, match_type="keyword")
            for entry, score in results
        ]

    # ── 聊天管线集成 ──────────────────────────────────────────

    def get_context_for_prompt(self) -> str:
        """获取注入系统 prompt 的记忆上下文（MEMORY.md 内容）。"""
        index_content = self._store.read_index()
        if not index_content.strip():
            return ""
        return self._prompt.build_system_context(index_content)

    def _ensure_extractor(self) -> None:
        """确保提取器已初始化 LLM。"""
        if self._extractor._llm is not None:
            return

        try:
            from .llm_utils import get_chat_llm

            self._extractor = MemoryExtractor(llm=get_chat_llm())
            logger.info("记忆提取器已初始化 LLM")
        except Exception:
            logger.warning("提取器 LLM 初始化失败，将使用快速模式", exc_info=True)

    def extract_from_conversation(
        self, user_msg: str, assistant_msg: str
    ) -> list[MemoryWriteRequest]:
        """从对话中提取候选记忆（快速模式）。"""
        combined = f"{user_msg}\n{assistant_msg}"
        return self._extractor.extract(combined)

    async def aextract_from_conversation(
        self, user_msg: str, assistant_msg: str
    ) -> list[MemoryWriteRequest]:
        """从对话中提取候选记忆（增强模式，使用 LLM）。"""
        self._ensure_extractor()
        combined = f"{user_msg}\n{assistant_msg}"
        return await self._extractor.aextract_with_llm(combined)

    def save_extracted(
        self, candidates: list[MemoryWriteRequest], *, session_id: str | None = None
    ) -> int:
        """保存提取的候选记忆。"""
        saved = 0
        existing_names = {e.name for e in self._store.list_all()}
        for candidate in candidates:
            if candidate.name in existing_names:
                continue
            try:
                self.save(candidate, session_id=session_id)
                saved += 1
            except Exception:
                logger.debug("保存候选记忆失败: %s", candidate.name, exc_info=True)
        return saved

    # ── 上下文构建（策略驱动） ────────────────────────────────

    def build_context(self, request: ContextBuildRequest) -> ContextBuildResult:
        """使用策略构建 LLM 上下文（同步）。"""
        self._ensure_context_builder()
        return self._context_builder.build(request)

    async def abuild_context(self, request: ContextBuildRequest) -> ContextBuildResult:
        """使用策略构建 LLM 上下文（异步，支持摘要等异步策略）。"""
        self._ensure_context_builder()
        return await self._context_builder.abuild(request)

    def get_context_builder(self):
        """获取上下文构建器。"""
        self._ensure_context_builder()
        return self._context_builder

    def get_history_manager(self):
        """获取对话历史管理器。"""
        self._ensure_strategy()
        return self._history_manager

    # ── 索引管理 ──────────────────────────────────────────────

    def rebuild_index(self) -> None:
        """重建 MEMORY.md 索引。"""
        self._store.rebuild_index()

    def get_stats(self) -> dict[str, int]:
        """获取记忆统计。"""
        return self._store.get_stats()


# 模块级单例
memory_service = MemoryService()
