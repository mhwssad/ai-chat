"""字节流文档加载器 — 从内存字节数据加载文档。"""

from src.ai.config.logging_setup import get_logger
import mimetypes
import os
import tempfile
from pathlib import Path

from langchain_core.documents import Document

from src.ai.exception.loader_exception import LoaderError
from .base import LoaderStrategy

logger = get_logger(__name__)


class StreamLoader(LoaderStrategy):
    """从字节流加载文档并委托下游 LoaderStrategy 解析。

    继承 ``LoaderStrategy``，实现 ``load_stream()`` 统一入口。
    不注册到 LoaderRegistry（``_skip_registry = True``），
    因为它是一个源适配器，而非文件格式加载器。

    工作流程：
    1. 根据 MIME 类型 / 文件名推断文件扩展名
    2. 将字节数据写入临时文件
    3. 委托下游 ``LoaderStrategy.load_file()`` 解析临时文件
    4. 自动清理临时文件
    5. 补充 mime_type、size_bytes 元数据

    Args:
        delegate: 下游加载器（通常是 ChainLoader），用于解析临时文件。
    """

    _skip_registry = True

    def __init__(self, delegate: LoaderStrategy) -> None:
        self._delegate = delegate

    def can_handle(self, file_path: Path) -> bool:
        """字节流适配器不参与文件加载链。"""
        return False

    def _load_single(self, file_path: Path) -> list[Document]:
        """字节流适配器不支持直接文件加载。"""
        raise LoaderError(f"StreamLoader 不支持直接文件加载: {file_path}")

    def load_stream(
        self,
        data: bytes,
        *,
        mime_type: str | None = None,
        filename: str | None = None,
    ) -> list[Document]:
        """从字节流加载文档。

        Args:
            data: 文档的字节数据。
            mime_type: MIME 类型，用于推断文件扩展名。
            filename: 原始文件名，辅助推断扩展名。

        Returns:
            Document 列表。

        Raises:
            LoaderError: 解析失败时抛出。
        """
        suffix = self._guess_suffix(mime_type, filename)
        tmp_path: Path | None = None

        try:
            # 1. 写入临时文件
            fd, tmp_name = tempfile.mkstemp(suffix=suffix)
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
            except Exception:
                os.close(fd)
                raise
            tmp_path = Path(tmp_name)

            # 2. 委托下游加载器解析
            docs = self._delegate.load_file(tmp_path)

            # 3. 补充元数据
            for doc in docs:
                if mime_type:
                    doc.metadata["mime_type"] = mime_type
                doc.metadata["size_bytes"] = len(data)

            return docs

        except LoaderError:
            raise
        except Exception as e:
            raise LoaderError(  # type: ignore[call-arg]
                "字节流文档加载失败",
                context={
                    "mime_type": mime_type,
                    "size_bytes": len(data),
                    "error": str(e),
                },
            ) from e
        finally:
            # 4. 清理临时文件
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    logger.warning("临时文件清理失败: %s", tmp_path)

    def _guess_suffix(self, mime_type: str | None, filename: str | None) -> str:
        """推断文件扩展名。

        优先级：filename 扩展名 > MIME 类型 > 默认 .bin

        Args:
            mime_type: MIME 类型。
            filename: 原始文件名。

        Returns:
            文件扩展名（含点号）。
        """
        # 优先从文件名提取扩展名
        if filename:
            p = Path(filename)
            if p.suffix:
                return p.suffix.lower()

        # 通过 MIME 类型推断
        if mime_type:
            ext = mimetypes.guess_extension(mime_type)
            if ext:
                return ext

        return ".bin"
