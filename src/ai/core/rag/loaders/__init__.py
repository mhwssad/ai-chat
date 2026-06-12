"""文档加载器模块。

采用职责链模式，各加载器通过继承 ``LoaderStrategy`` 自动注册，
``ChainLoader`` 按优先级遍历执行。

支持三种统一加载入口：文件路径、字节流、URL，均通过 ``ChainLoader`` 调用，
无需手动创建 StreamLoader / UrlLoader。

示例::

    from src.ai.core.rag.loaders import ChainLoader
    from src.ai.core.rag.loaders.registry import LoaderRegistry

    loader = ChainLoader(LoaderRegistry)

    # 加载本地文件
    docs = loader.load_file("report.pdf")

    # 从字节流加载
    docs = loader.load_stream(data, mime_type="application/pdf", filename="report.pdf")

    # 从 URL 加载
    docs = loader.load_url("https://example.com/doc.pdf")

    # 自定义加载器只需继承 LoaderStrategy
    class MyLoader(LoaderStrategy):
        priority = 150
        name = "my_loader"
        ...
"""

from src.ai.config.loader_settings import (
    LoaderSettings,
    OcrSettings,
    PlainTextSettings,
    UnstructuredSettings,
)
from src.ai.exception.loader_exception import (
    LoaderError,
    LoadPermissionError,
    UnsupportedFileTypeError,
)
from .base import LangchainAdapter, LoaderStrategy
from .chain_loader import ChainLoader
from .registry import LoaderRegistry

# 惰性导入：具体加载器类和 DI 容器单例
# 延迟到首次访问时，避免循环导入
_LAZY_IMPORTS = {
    "UnstructuredLoader": ".unstructured_loader",
    "OcrImageLoader": ".ocr_loader",
    "PlainTextLoader": ".text_loader",
    "UrlLoader": ".url_loader",
    "StreamLoader": ".stream_loader",
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # 基类
    "LoaderStrategy",
    "LangchainAdapter",
    # 注册表
    "LoaderRegistry",
    # 编排器
    "ChainLoader",
    # 加载器
    "UnstructuredLoader",
    "OcrImageLoader",
    "PlainTextLoader",
    "UrlLoader",
    "StreamLoader",
    # 配置
    "LoaderSettings",
    "PlainTextSettings",
    "OcrSettings",
    "UnstructuredSettings",
    # 异常
    "LoaderError",
    "UnsupportedFileTypeError",
    "LoadPermissionError",
]
