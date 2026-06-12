"""URL 文档加载器 — 从网络 URL 下载并解析文档。"""

from src.ai.config.logging_setup import get_logger
import mimetypes
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from langchain_core.documents import Document

from src.ai.exception.loader_exception import LoaderError
from .base import LoaderStrategy

logger = get_logger(__name__)

# 默认超时（秒）
_DEFAULT_TIMEOUT = 60


class UrlLoader(LoaderStrategy):
    """从 URL 下载文档并委托下游 LoaderStrategy 解析。

    继承 ``LoaderStrategy``，实现 ``load_url()`` 统一入口。
    不注册到 LoaderRegistry（``_skip_registry = True``），
    因为它是一个源适配器，而非文件格式加载器。

    工作流程：
    1. 通过 HTTP GET 下载内容到临时文件
    2. 根据 MIME 类型和 URL 路径推断文件扩展名
    3. 委托下游 ``LoaderStrategy.load_file()`` 解析临时文件
    4. 自动清理临时文件
    5. 补充 source_url 元数据

    Args:
        delegate: 下游加载器（通常是 ChainLoader），用于解析下载的文件。
        timeout: HTTP 请求超时秒数。
    """

    _skip_registry = True

    def __init__(
        self,
        delegate: LoaderStrategy,
        *,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self._delegate = delegate
        self._timeout = timeout

    def can_handle(self, file_path: Path) -> bool:
        """URL 适配器不参与文件加载链。"""
        return False

    def _load_single(self, file_path: Path) -> list[Document]:
        """URL 适配器不支持直接文件加载。"""
        raise LoaderError(f"UrlLoader 不支持直接文件加载: {file_path}")

    def load_url(self, url: str) -> list[Document]:
        """从 URL 下载并解析文档。

        Args:
            url: 文档 URL。

        Returns:
            Document 列表。

        Raises:
            LoaderError: 下载失败或解析失败时抛出。
        """
        suffix = self._guess_suffix(url)
        tmp_path: Path | None = None

        try:
            # 1. 下载到临时文件
            tmp_path = self._download(url, suffix)

            # 2. 委托下游加载器解析
            docs = self._delegate.load_file(tmp_path)

            # 3. 补充 source_url 元数据
            for doc in docs:
                doc.metadata["source_url"] = url

            return docs

        except LoaderError:
            raise
        except Exception as e:
            raise LoaderError(  # type: ignore[call-arg]
                f"URL 文档加载失败: {url}",
                path=url,
                context={"error": str(e)},
            ) from e
        finally:
            # 4. 清理临时文件
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    logger.warning("临时文件清理失败: %s", tmp_path)

    def _download(self, url: str, suffix: str) -> Path:
        """下载 URL 内容到临时文件。

        Args:
            url: 文档 URL。
            suffix: 文件扩展名（含点号）。

        Returns:
            临时文件路径。
        """
        with httpx.Client(follow_redirects=True, timeout=self._timeout) as client:
            response = client.get(url)
            response.raise_for_status()

        fd, tmp_name = tempfile.mkstemp(suffix=suffix)
        try:
            import os

            with os.fdopen(fd, "wb") as f:
                f.write(response.content)
        except Exception:
            import os

            os.close(fd)
            raise

        return Path(tmp_name)

    def _guess_suffix(self, url: str) -> str:
        """根据 URL 和 MIME 类型推断文件扩展名。

        Args:
            url: 文档 URL。

        Returns:
            文件扩展名（含点号），如 ".pdf"。
        """
        parsed = urlparse(url)
        path = parsed.path

        # 优先从 URL 路径提取扩展名
        if "." in Path(path).name:
            ext = Path(path).suffix.lower()
            if ext:
                return ext

        # 尝试通过路径推断 MIME 类型
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type:
            ext = mimetypes.guess_extension(mime_type)  # type: ignore[assignment]
            if ext:
                return ext

        # 默认使用 .bin
        return ".bin"
