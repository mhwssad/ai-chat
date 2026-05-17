"""纯文本和 Markdown 文件加载器。"""

from pathlib import Path

from ..factory import register_loader
from ..models import DocumentLoader, LoaderNotFoundException


@register_loader()
class TextLoader(DocumentLoader):
    """支持 .txt 和 .md 文件的加载器。"""

    SUPPORTED_EXTENSIONS = [".txt", ".md"]

    def load(self, file_path: str) -> list[dict]:
        path = Path(file_path)
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise LoaderNotFoundException(path.suffix, []) from None
        except UnicodeDecodeError as e:
            raise ValueError(f"文件编码错误: {file_path}: {e}") from e
        return [{"content": content, "metadata": {"source": str(path), "suffix": path.suffix}}]
