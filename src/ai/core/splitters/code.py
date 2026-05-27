"""代码语言感知切割器。"""

from pathlib import Path
from typing import Any

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

from .base import SplitChunk, SplitterStrategy

#: 文件扩展名 → Language 枚举映射
EXTENSION_LANGUAGE: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".js": Language.JS,
    ".mjs": Language.JS,
    ".ts": Language.TS,
    ".java": Language.JAVA,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".rb": Language.RUBY,
    ".php": Language.PHP,
    ".swift": Language.SWIFT,
    ".kt": Language.KOTLIN,
    ".cs": Language.CSHARP,
    ".cpp": Language.CPP,
    ".cxx": Language.CPP,
    ".cc": Language.CPP,
    ".c": Language.C,
    ".scala": Language.SCALA,
    ".html": Language.HTML,
    ".htm": Language.HTML,
}


class CodeSplitter(SplitterStrategy):
    """基于语言感知的代码切割器。

    使用 RecursiveCharacterTextSplitter.from_language() 按代码结构
    （函数、类、块）切割，保留完整的语法单元。

    Args:
        language: 目标编程语言，None 时从文件扩展名自动推断。
        chunk_size: 每个切片的最大字符数。
        chunk_overlap: 相邻切片的重叠字符数。
    """

    def __init__(
        self,
        language: Language | None = None,
        *,
        chunk_size: int = 1500,
        chunk_overlap: int = 200,
    ) -> None:
        self._language = language
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._splitter: RecursiveCharacterTextSplitter | None = None

    def _get_splitter(self, language: Language) -> RecursiveCharacterTextSplitter:
        """获取或创建指定语言的切割器。"""
        if self._splitter is None or self._language != language:
            self._language = language
            self._splitter = RecursiveCharacterTextSplitter.from_language(
                language=language,
                chunk_size=self._chunk_size,
                chunk_overlap=self._chunk_overlap,
            )
        return self._splitter

    @classmethod
    def from_extension(cls, ext: str, **kwargs: int) -> "CodeSplitter | None":
        """从文件扩展名创建代码切割器。"""
        lang = EXTENSION_LANGUAGE.get(ext.lower())
        if lang is None:
            return None
        return cls(language=lang, **kwargs)

    def can_file_handle(self, file_path: Path) -> bool:
        """判断文件扩展名是否在支持的语言映射中。"""
        return file_path.suffix.lower() in EXTENSION_LANGUAGE

    def can_text_handle(self, text: str, metadata: dict[str, Any]) -> bool:
        """根据文件扩展名或元数据判断。"""
        source = metadata.get("source", "")
        if source:
            ext = Path(source).suffix.lower()
            if ext in EXTENSION_LANGUAGE:
                return True
        return metadata.get("file_label") == "code"

    def split_text(
        self, text: str, *, metadata: dict[str, Any] | None = None
    ) -> list[SplitChunk]:
        if not text.strip():
            return []

        # 确定语言
        language = self._language
        if language is None and metadata:
            source = metadata.get("source", "")
            if source:
                ext = Path(source).suffix.lower()
                language = EXTENSION_LANGUAGE.get(ext)

        if language is None:
            return []

        splitter = self._get_splitter(language)
        chunks = splitter.split_text(text)
        lang_name = language.value if hasattr(language, "value") else str(language)
        return [
            SplitChunk(
                index=i,
                content=c,
                strategy="code",
                metadata={"language": lang_name},
            )
            for i, c in enumerate(chunks)
        ]


# ── 自注册 ──────────────────────────────────────────────────────────────────
from .registry import splitter_registry  # noqa: E402

splitter_registry.register(CodeSplitter, priority=200, name="code")
