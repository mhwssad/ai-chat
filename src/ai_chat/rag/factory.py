"""RAG 抽象工厂 — 整合向量存储、文档加载与文本分割。"""

from pathlib import Path
from typing import Callable, Optional

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.rag.models import (
    DocumentLoader,
    LoaderNotFoundException,
    SplitterNotFoundException,
    TextSplitter,
    VectorStoreConfig,
    VectorStoreProvider,
    StoreNotFoundException,
)

logger = get_logger(__name__)

# 分批入库的 chunk 数量阈值
_BATCH_SIZE = 500


class RAGFactory:
    """RAG 抽象工厂，整合向量存储、文档加载、文本分割。"""

    def __init__(self) -> None:
        self._store_registry: dict[str, type[VectorStoreProvider]] = {}
        self._store_configs: dict[str, Callable[[], VectorStoreConfig]] = {}
        self._loader_registry: dict[str, type[DocumentLoader]] = {}
        self._splitter_registry: dict[str, type[TextSplitter]] = {}
        self._default_splitter: Optional[str] = None

    # ── 注册 ────────────────────────────────────────────

    def register_store(
        self,
        name: str,
        store_cls: type[VectorStoreProvider],
        config_fn: Callable[[], VectorStoreConfig],
    ) -> None:
        self._store_registry[name] = store_cls
        self._store_configs[name] = config_fn

    def register_loader(self, loader_cls: type[DocumentLoader]) -> None:
        for ext in getattr(loader_cls, "SUPPORTED_EXTENSIONS", []):
            self._loader_registry[ext] = loader_cls

    def register_splitter(
        self,
        name: str,
        splitter_cls: type[TextSplitter],
        default: bool = False,
    ) -> None:
        """注册文本分割器。default=True 设为默认分割器。"""
        self._splitter_registry[name] = splitter_cls
        if default or self._default_splitter is None:
            self._default_splitter = name

    # ── 创建 ────────────────────────────────────────────

    def create_store(
        self,
        name: str,
        config: Optional[VectorStoreConfig] = None,
    ) -> VectorStoreProvider:
        if name not in self._store_registry:
            raise StoreNotFoundException(name, list(self._store_registry))
        if config is None:
            config = self._store_configs[name]()
        return self._store_registry[name](config)

    def get_loader(self, file_path: str) -> DocumentLoader:
        ext = Path(file_path).suffix.lower()
        if ext not in self._loader_registry:
            raise LoaderNotFoundException(ext, list(self._loader_registry))
        return self._loader_registry[ext]()

    def create_splitter(
        self,
        name: Optional[str] = None,
        **kwargs,
    ) -> TextSplitter:
        """创建文本分割器，不传 name 则使用默认。"""
        splitter_name = name or self._default_splitter
        if splitter_name is None or splitter_name not in self._splitter_registry:
            raise SplitterNotFoundException(
                splitter_name or "<none>", list(self._splitter_registry)
            )
        return self._splitter_registry[splitter_name](**kwargs)

    # ── 便捷方法 ────────────────────────────────────────

    def index_directory(
        self,
        dir_path: str,
        store_name: str = "faiss",
        config: Optional[VectorStoreConfig] = None,
        splitter_name: Optional[str] = None,
    ) -> VectorStoreProvider:
        """扫描目录 → 加载文档 → 分割 → 入库（分批写入 + 进度日志）。"""
        store = self.create_store(store_name, config)
        cfg = config or self._store_configs[store_name]()
        splitter = self.create_splitter(splitter_name, chunk_size=cfg.chunk_size, chunk_overlap=cfg.chunk_overlap)
        directory = Path(dir_path)

        all_chunks: list[str] = []
        all_metadata: list[dict] = []
        total_files = 0
        total_indexed = 0

        sorted_files = sorted(f for f in directory.rglob("*") if f.is_file())
        total_files = len(sorted_files)

        for i, file_path in enumerate(sorted_files, 1):
            ext = file_path.suffix.lower()
            if ext not in self._loader_registry:
                continue
            try:
                loader = self.get_loader(str(file_path))
                documents = loader.load(str(file_path))
            except Exception as e:
                logger.warning("加载文件失败，跳过: %s (%s)", file_path, e)
                continue
            chunks = splitter.split(documents)
            for chunk in chunks:
                all_chunks.append(chunk["content"])
                all_metadata.append(chunk["metadata"])

            # 分批入库
            if len(all_chunks) >= _BATCH_SIZE:
                store.add_texts(all_chunks, all_metadata)
                total_indexed += len(all_chunks)
                all_chunks, all_metadata = [], []

            if i % 10 == 0 or i == total_files:
                logger.info("索引进度: %d/%d 文件, %d chunks", i, total_files, total_indexed + len(all_chunks))

        # 最后一批
        if all_chunks:
            store.add_texts(all_chunks, all_metadata)
            total_indexed += len(all_chunks)

        logger.info("索引完成: %d 文件, %d chunks", total_files, total_indexed)
        return store

    def query(self, question: str, store: VectorStoreProvider, k: int = 4) -> list[dict]:
        return store.similarity_search(question, k=k)

    def list_stores(self) -> list[str]:
        return list(self._store_registry)

    def list_supported_extensions(self) -> list[str]:
        return list(self._loader_registry)

    def list_splitters(self) -> list[str]:
        return list(self._splitter_registry)


# ======================================================================
# 装饰器
# ======================================================================

rag_factory = RAGFactory()


def register_vectorstore(name: str, config_fn: Callable[[], VectorStoreConfig]):
    """类装饰器：自动注册向量存储后端。"""
    def decorator(cls: type[VectorStoreProvider]) -> type[VectorStoreProvider]:
        rag_factory.register_store(name, cls, config_fn)
        return cls
    return decorator


def register_loader():
    """类装饰器：自动注册文档加载器。"""
    def decorator(cls: type[DocumentLoader]) -> type[DocumentLoader]:
        rag_factory.register_loader(cls)
        return cls
    return decorator


def register_splitter(name: str, *, default: bool = False):
    """类装饰器：自动注册文本分割器。"""
    def decorator(cls: type[TextSplitter]) -> type[TextSplitter]:
        rag_factory.register_splitter(name, cls, default=default)
        return cls
    return decorator
