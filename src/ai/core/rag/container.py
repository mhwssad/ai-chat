"""RAG 子系统 DI 容器。

整合 Loader、Splitter 注册表和 RagService 的创建。
"""

from typing import Any

from dependency_injector import containers, providers


def _create_loader_registry(settings):
    """导入加载器模块（触发 __init_subclass__ 自动注册），并注入配置工厂。

    使用 importlib 绕过包 __init__.py，避免循环导入。
    """
    import importlib.util
    import sys
    from pathlib import Path

    from src.ai.core.rag.loaders.registry import LoaderRegistry

    dir_path = Path(__file__).parent / "loaders"

    def _import(name: str):
        full = f"src.ai.core.rag.loaders.{name}"
        if full in sys.modules:
            return sys.modules[full]
        spec = importlib.util.spec_from_file_location(full, dir_path / f"{name}.py")
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载模块: {name}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full] = mod
        spec.loader.exec_module(mod)
        return mod

    # 导入触发 __init_subclass__ 自动注册
    text_mod = _import("text_loader")
    unstructured_mod = _import("unstructured_loader")
    ocr_mod = _import("ocr_loader")

    # 注入配置工厂
    text_mod.PlainTextLoader.settings_factory = lambda: settings.plain_text
    unstructured_mod.UnstructuredLoader.settings_factory = lambda: settings.unstructured
    ocr_mod.OcrImageLoader.settings_factory = lambda: settings.ocr

    return LoaderRegistry


def _create_loader_settings():
    """加载器统一配置。"""
    from src.ai.config.loader_settings import LoaderSettings

    return LoaderSettings()


def _create_splitter_registry():
    """构建 SplitterRegistry 并自动发现切割器。

    使用 importlib 从文件路径直接导入切割器模块，
    避免触发 splitters 包的 __init__.py 导致循环导入。
    """
    import importlib.util
    import sys
    from pathlib import Path

    from src.ai.core.rag.splitters.registry import SplitterRegistry

    dir_path = Path(__file__).parent / "splitters"

    def _import_splitter_module(module_name: str):
        """从文件路径直接导入切割器模块，绕过包 __init__.py。"""
        full_name = f"src.ai.core.rag.splitters.{module_name}"
        if full_name in sys.modules:
            return sys.modules[full_name]
        file_path = dir_path / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(full_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载模块: {module_name}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = mod
        spec.loader.exec_module(mod)
        return mod

    modules = [
        _import_splitter_module("markdown"),
        _import_splitter_module("code"),
        _import_splitter_module("token_splitter"),
        _import_splitter_module("recursive"),
    ]

    return SplitterRegistry.discover(modules)


def _create_index_meta_store(settings):
    """创建 IndexMetaStore。"""
    from src.ai.config.base_config import project_root
    from src.ai.core.rag.index_meta import IndexMetaStore

    rag = settings.rag
    return IndexMetaStore(
        persist_path=project_root / rag.rag_persist_dir / "index_meta.json"
    )


def _create_bm25_retriever():
    """创建 BM25Retriever。"""
    from src.ai.core.rag.bm25_retriever import BM25Retriever

    return BM25Retriever()


def _create_rag_service(
    model_service,
    loader_registry,
    splitter_registry,
    settings,
    prompt_service,
    meta_store=None,
    bm25_retriever=None,
):
    """构建 RagService，通过 ModelService 获取 Embedding。"""
    from src.ai.config.base_config import project_root
    from src.ai.core.rag.embeddings import HashEmbeddings
    from src.ai.core.rag.service import RagService
    from src.ai.core.rag.loaders.chain_loader import ChainLoader
    from src.ai.core.rag.splitters.chain_splitter import ChainSplitter

    rag = settings.rag

    if model_service.embedding_config.model_key:
        embeddings = model_service.get_embedding()
    else:
        embeddings = HashEmbeddings(dimension=rag.rag_fallback_dimension)

    return RagService(
        embeddings=embeddings,
        loader=ChainLoader(loader_registry),
        splitter=ChainSplitter(
            registry=splitter_registry,
            chunk_size=rag.rag_chunk_size,
            chunk_overlap=rag.rag_chunk_overlap,
        ),
        persist_directory=project_root / rag.rag_persist_dir,
        collection_name=rag.rag_collection_name,
        top_k=rag.rag_top_k,
        settings=settings,
        prompt_service=prompt_service,
        meta_store=meta_store,
        bm25_retriever=bm25_retriever,
    )


class RagContainer(containers.DeclarativeContainer):
    """RAG 子系统容器。"""

    model_service: Any = providers.Dependency()
    settings: Any = providers.Dependency()
    prompt_service: Any = providers.Dependency()

    # 子注册表（从 LoaderContainer/SplitterContainer 吸收）
    loader_settings = providers.Singleton(_create_loader_settings)
    loader_registry = providers.Singleton(
        _create_loader_registry,
        settings=loader_settings,
    )
    splitter_registry = providers.Singleton(_create_splitter_registry)

    # 增量索引元数据
    index_meta_store = providers.Singleton(
        _create_index_meta_store,
        settings=settings,
    )

    # BM25 检索器
    bm25_retriever = providers.Singleton(_create_bm25_retriever)

    # RAG 服务
    rag_service = providers.Singleton(
        _create_rag_service,
        model_service=model_service,
        loader_registry=loader_registry,
        splitter_registry=splitter_registry,
        settings=settings,
        prompt_service=prompt_service,
        meta_store=index_meta_store,
        bm25_retriever=bm25_retriever,
    )
