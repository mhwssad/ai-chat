"""纯文本和 Markdown 文件加载器。"""

from pathlib import Path

from ..factory import register_loader
from ..models import DocumentLoader


@register_loader()
class TextLoader(DocumentLoader):
    """支持 .txt 和 .md 文件的加载器。"""

    SUPPORTED_EXTENSIONS = [".txt", ".md"]

    def load(self, file_path: str) -> list[dict]:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        return [{"content": content, "metadata": {"source": str(path), "suffix": path.suffix}}]
