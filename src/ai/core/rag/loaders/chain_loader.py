"""职责链加载器编排器。"""

from src.ai.config.logging_setup import get_logger
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from src.ai.exception.loader_exception import LoaderError
from .base import LoaderStrategy
from .registry import LoaderRegistry
from .stream_loader import StreamLoader
from .url_loader import UrlLoader

logger = get_logger(__name__)


class ChainLoader(LoaderStrategy):
    """职责链编排器。

    遍历注册表中的加载器类，按优先级依次尝试。
    首个成功产出文档的加载器胜出，后续加载器不再执行。
    不硬编码任何具体加载器，新增策略只需注册即可。

    同时提供 ``load_stream()`` 和 ``load_url()`` 统一入口，
    内部委托给 StreamLoader / UrlLoader 适配器（均继承自 LoaderStrategy），
    调用方无需手动创建。

    Args:
        registry: 加载器注册表类。
        **kwargs: 传递给各加载器构造函数的额外参数。
    """

    priority = 0
    _skip_registry = True

    def __init__(
        self,
        registry: type[LoaderRegistry],
        **kwargs: Any,
    ) -> None:
        self._registry = registry
        self._kwargs = kwargs
        # 预创建源适配器，统一调用入口
        # StreamLoader / UrlLoader 均继承 LoaderStrategy，不注册到注册表
        self._stream_adapter = StreamLoader(self)
        self._url_adapter = UrlLoader(self)

    def can_handle(self, file_path: Path) -> bool:
        """编排器始终可以尝试。"""
        return True

    def _load_single(self, file_path: Path) -> list[Document]:
        """按优先级遍历加载器链，首个成功的返回结果。"""
        for loader_cls in self._registry.all():
            settings = loader_cls.settings_factory()  # type: ignore[attr-defined]
            loader = loader_cls(settings, **self._kwargs)
            if not loader.can_handle(file_path):
                continue
            try:
                docs = loader._load_single(file_path)
                if docs:
                    logger.debug(
                        "加载器 %s 成功加载 %d 个文档",
                        loader_cls.name,  # type: ignore[attr-defined]
                        len(docs),
                    )
                    return docs
            except LoaderError:
                raise
            except Exception as e:
                logger.debug(
                    "加载器 %s 失败 (%s: %s)，尝试下一个",
                    loader_cls.name,  # type: ignore[attr-defined]
                    type(e).__name__,
                    e,
                )
                continue

        raise LoaderError(
            f"所有加载策略均失败: {file_path}",
            path=str(file_path),
        )

    def load_stream(
        self,
        data: bytes,
        *,
        mime_type: str | None = None,
        filename: str | None = None,
    ) -> list[Document]:
        """从字节流加载文档，委托给内部 StreamLoader。

        Args:
            data: 文档字节数据。
            mime_type: MIME 类型。
            filename: 原始文件名。

        Returns:
            Document 列表。
        """
        return self._stream_adapter.load_stream(
            data, mime_type=mime_type, filename=filename
        )

    def load_url(self, url: str) -> list[Document]:
        """从 URL 下载并加载文档，委托给内部 UrlLoader。

        Args:
            url: 文档 URL。

        Returns:
            Document 列表。
        """
        return self._url_adapter.load_url(url)
