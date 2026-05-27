"""core/splitters 模块测试。"""


from pathlib import Path

import pytest
from langchain_text_splitters import Language

from src.ai.core.loaders.base import DocumentMetadata, LoadedDocument
from src.ai.core.splitters import (
    AutoSplitter,
    CodeSplitter,
    EXTENSION_LANGUAGE,
    MarkdownSplitter,
    RecursiveSplitter,
    SplitChunk,
    SplitterError,
    TextSplitter,
    TokenSplitter,
)
from src.ai.core.splitters.code import EXTENSION_LANGUAGE as CODE_EXT_MAP


# ============================================================
# RecursiveSplitter
# ============================================================


class TestRecursiveSplitter:
    def test_split_basic_text(self) -> None:
        splitter = RecursiveSplitter(chunk_size=50, chunk_overlap=10)
        text = "短文。这只是一段很短的测试文本。"
        chunks = splitter.split_text(text)
        assert len(chunks) >= 1
        assert all(c.strategy == "recursive" for c in chunks)
        assert all(c.index == i for i, c in enumerate(chunks))

    def test_split_empty_string(self) -> None:
        splitter = RecursiveSplitter()
        assert splitter.split_text("") == []
        assert splitter.split_text("   \n\t") == []

    def test_split_short_text_returns_single_chunk(self) -> None:
        splitter = RecursiveSplitter(chunk_size=800)
        text = "很简短的文本"
        chunks = splitter.split_text(text)
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].index == 0

    def test_split_long_text_multiple_chunks(self) -> None:
        splitter = RecursiveSplitter(chunk_size=50, chunk_overlap=10)
        text = "这是第一段内容。" * 20
        chunks = splitter.split_text(text)
        assert len(chunks) > 1

    def test_split_preserves_content(self) -> None:
        """所有 chunk 拼接后应覆盖原文大部分内容。"""
        splitter = RecursiveSplitter(chunk_size=100, chunk_overlap=20)
        text = "测试文本内容。" * 30
        chunks = splitter.split_text(text)
        combined = "".join(c.content for c in chunks)
        for segment in ["测试文本内容。"]:
            assert segment in combined


# ============================================================
# MarkdownSplitter
# ============================================================


class TestMarkdownSplitter:
    SAMPLE_MD = """\
# 标题一

第一段内容，属于标题一下面。

## 标题二

第二段内容，属于标题二下面。

### 标题三

第三段内容。
"""

    def test_split_by_headers(self) -> None:
        splitter = MarkdownSplitter(chunk_size=500)
        chunks = splitter.split_text(self.SAMPLE_MD)
        assert len(chunks) >= 2
        assert all(c.strategy == "markdown" for c in chunks)

    def test_header_metadata(self) -> None:
        splitter = MarkdownSplitter(chunk_size=500)
        chunks = splitter.split_text(self.SAMPLE_MD)
        has_header_meta = any("h1" in c.metadata or "h2" in c.metadata for c in chunks)
        assert has_header_meta

    def test_split_empty(self) -> None:
        splitter = MarkdownSplitter()
        assert splitter.split_text("") == []
        assert splitter.split_text("   ") == []

    def test_no_headers_falls_through(self) -> None:
        """无标题的 Markdown 按纯文本切割。"""
        splitter = MarkdownSplitter(chunk_size=500)
        chunks = splitter.split_text("纯文本无标题。")
        assert len(chunks) >= 1

    def test_long_section_re_split(self) -> None:
        """超长段落会被二次切割。"""
        long_md = "# 标题\n\n" + "长内容。" * 200
        splitter = MarkdownSplitter(chunk_size=100, chunk_overlap=10)
        chunks = splitter.split_text(long_md)
        assert len(chunks) > 1


# ============================================================
# CodeSplitter
# ============================================================


class TestCodeSplitter:
    PYTHON_CODE = '''\
def hello():
    print("Hello, World!")

class Foo:
    def bar(self):
        return 42
'''

    def test_split_python(self) -> None:
        splitter = CodeSplitter(Language.PYTHON, chunk_size=200)
        chunks = splitter.split_text(self.PYTHON_CODE)
        assert len(chunks) >= 1
        assert all(c.strategy == "code" for c in chunks)
        assert all(c.metadata.get("language") == "python" for c in chunks)

    def test_split_empty(self) -> None:
        splitter = CodeSplitter(Language.PYTHON)
        assert splitter.split_text("") == []

    def test_from_extension_known(self) -> None:
        splitter = CodeSplitter.from_extension(".py")
        assert splitter is not None

    def test_from_extension_unknown(self) -> None:
        splitter = CodeSplitter.from_extension(".xyz")
        assert splitter is None

    def test_extension_mapping_completeness(self) -> None:
        """至少支持 15 种语言映射。"""
        assert len(CODE_EXT_MAP) >= 15

    def test_from_extension_case_insensitive(self) -> None:
        splitter = CodeSplitter.from_extension(".PY")
        assert splitter is not None


# ============================================================
# TokenSplitter
# ============================================================


class TestTokenSplitter:
    def test_split_basic(self) -> None:
        splitter = TokenSplitter(chunk_size=50, chunk_overlap=5)
        text = "这是一段测试文本，用于验证 token 切割器的功能。" * 5
        chunks = splitter.split_text(text)
        assert len(chunks) >= 1
        assert all(c.strategy == "token" for c in chunks)

    def test_split_empty(self) -> None:
        splitter = TokenSplitter()
        assert splitter.split_text("") == []

    def test_short_text_single_chunk(self) -> None:
        splitter = TokenSplitter(chunk_size=800)
        chunks = splitter.split_text("短文本")
        assert len(chunks) == 1


# ============================================================
# AutoSplitter
# ============================================================


class TestAutoSplitter:
    def _make_doc(self, content: str, source_path: str) -> LoadedDocument:
        return LoadedDocument(
            content=content,
            metadata=DocumentMetadata(source_path=source_path),
        )

    def test_markdown_file_uses_markdown_splitter(self) -> None:
        doc = self._make_doc("# 标题\n\n内容。", "test.md")
        splitter = AutoSplitter(chunk_size=500)
        chunks = splitter.split_document(doc)
        assert all(c.strategy == "markdown" for c in chunks)

    def test_python_file_uses_code_splitter(self) -> None:
        doc = self._make_doc("def hello(): pass", "test.py")
        splitter = AutoSplitter()
        chunks = splitter.split_document(doc)
        assert all(c.strategy == "code" for c in chunks)
        assert all(c.metadata.get("language") == "python" for c in chunks)

    def test_unknown_file_uses_recursive(self) -> None:
        doc = self._make_doc("普通文本内容。", "data.txt")
        splitter = AutoSplitter()
        chunks = splitter.split_document(doc)
        assert all(c.strategy == "recursive" for c in chunks)

    def test_no_extension_uses_recursive(self) -> None:
        doc = self._make_doc("无扩展名文件内容。", "README")
        splitter = AutoSplitter()
        chunks = splitter.split_document(doc)
        assert all(c.strategy == "recursive" for c in chunks)

    def test_split_text_uses_recursive(self) -> None:
        splitter = AutoSplitter()
        chunks = splitter.split_text("纯文本内容")
        assert all(c.strategy == "recursive" for c in chunks)

    def test_empty_document(self) -> None:
        doc = self._make_doc("", "empty.md")
        splitter = AutoSplitter()
        assert splitter.split_document(doc) == []

    def test_js_file(self) -> None:
        doc = self._make_doc("function hello() { return 1; }", "app.js")
        splitter = AutoSplitter()
        chunks = splitter.split_document(doc)
        assert all(c.strategy == "code" for c in chunks)

    def test_java_file(self) -> None:
        doc = self._make_doc("public class Main { }", "Main.java")
        splitter = AutoSplitter()
        chunks = splitter.split_document(doc)
        assert all(c.strategy == "code" for c in chunks)


# ============================================================
# SplitterError
# ============================================================


class TestSplitterError:
    def test_create_error(self) -> None:
        err = SplitterError("切割失败", strategy="recursive")
        assert "切割失败" in str(err)
        assert err.strategy == "recursive"

    def test_error_with_cause(self) -> None:
        cause = ValueError("原始错误")
        err = SplitterError("切割异常", cause=cause)
        assert err.cause is cause

    def test_error_inherits_base_exceptions(self) -> None:
        from src.ai.exception.base_exception import BaseExceptions

        err = SplitterError("测试")
        assert isinstance(err, BaseExceptions)


# ============================================================
# SplitChunk
# ============================================================


class TestSplitChunk:
    def test_frozen(self) -> None:
        chunk = SplitChunk(index=0, content="text", strategy="recursive")
        with pytest.raises(AttributeError):
            chunk.content = "changed"  # type: ignore[misc]

    def test_default_metadata(self) -> None:
        chunk = SplitChunk(index=0, content="text", strategy="recursive")
        assert chunk.metadata == {}

    def test_custom_metadata(self) -> None:
        chunk = SplitChunk(index=0, content="text", strategy="markdown", metadata={"h1": "标题"})
        assert chunk.metadata == {"h1": "标题"}


# ============================================================
# RAG 兼容
# ============================================================


class TestRagCompatibility:
    def test_rag_text_splitter_interface(self) -> None:
        from src.ai.rag.splitters import RagTextSplitter, TextChunk

        splitter = RagTextSplitter()
        chunks = splitter.split("测试文本内容。")
        assert all(isinstance(c, TextChunk) for c in chunks)
        assert all(isinstance(c.index, int) for c in chunks)

    def test_rag_text_splitter_empty(self) -> None:
        from src.ai.rag.splitters import RagTextSplitter

        splitter = RagTextSplitter()
        assert splitter.split("") == []

    def test_rag_split_document(self) -> None:
        from src.ai.rag.splitters import RagTextSplitter

        splitter = RagTextSplitter()
        doc = LoadedDocument(
            content="# 标题\n\n内容。",
            metadata=DocumentMetadata(source_path="test.md"),
        )
        chunks = splitter.split_document(doc)
        assert all(isinstance(c, SplitChunk) for c in chunks)
        assert all(c.strategy == "markdown" for c in chunks)
