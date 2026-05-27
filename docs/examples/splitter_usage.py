"""文本切割器使用示例。

运行方式: uv run python -m docs.examples.splitter_usage
"""

import sys
import io

# Windows 终端 UTF-8 输出
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

from src.ai.core.loaders import ChainLoader
from src.ai.core.splitters import (
    ChainSplitter,
    CodeSplitter,
    MarkdownSplitter,
    RecursiveSplitter,
    TokenSplitter,
)

# 示例文件目录
SAMPLES = Path(__file__).parent / "samples"


def _safe_print(text: str) -> None:
    """安全打印 — 处理 Windows GBK 终端编码。"""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("gbk", errors="replace").decode("gbk"))


def _preview(text: str, max_len: int = 80) -> str:
    """安全截取预览文本。"""
    safe = text.replace("\n", "\\n")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def demo_recursive_splitter() -> None:
    """递归字符切割器 — 通用文本切割。"""
    print("=" * 60)
    print("RecursiveSplitter — 通用递归字符切割")
    print("=" * 60)

    text = "这是一段测试文本。" * 20
    splitter = RecursiveSplitter(chunk_size=80, chunk_overlap=20)
    chunks = splitter.split_text(text)

    print(f"  输入长度: {len(text)} 字符")
    print(f"  切片数量: {len(chunks)}")
    for chunk in chunks:
        print(f"  [{chunk.index}] ({len(chunk.content)}字) {_preview(chunk.content, 60)}")
    print()


def demo_markdown_splitter() -> None:
    """Markdown 标题切割器 — 按标题层级切割。"""
    print("=" * 60)
    print("MarkdownSplitter — Markdown 标题层级切割")
    print("=" * 60)

    splitter = MarkdownSplitter(chunk_size=300)
    chunks = splitter.split_text(SAMPLES.joinpath("demo_article.md").read_text(encoding="utf-8"))

    print(f"  切片数量: {len(chunks)}")
    for chunk in chunks:
        headers = chunk.metadata
        header_info = " | ".join(f"{k}={v}" for k, v in headers.items()) if headers else "(无标题)"
        print(f"  [{chunk.index}] {header_info}")
        print(f"       ({len(chunk.content)}字) {_preview(chunk.content, 70)}")
    print()


def demo_code_splitter() -> None:
    """代码语言感知切割器 — 按代码结构切割。"""
    print("=" * 60)
    print("CodeSplitter — 代码语言感知切割")
    print("=" * 60)

    splitter = CodeSplitter.from_extension(".py", chunk_size=300, chunk_overlap=50)
    assert splitter is not None

    code = SAMPLES.joinpath("demo_app.py").read_text(encoding="utf-8")
    chunks = splitter.split_text(code)

    print(f"  语言: {chunks[0].metadata.get('language', 'unknown') if chunks else 'N/A'}")
    print(f"  切片数量: {len(chunks)}")
    for chunk in chunks:
        print(f"  [{chunk.index}] ({len(chunk.content)}字) {_preview(chunk.content, 70)}")
    print()


def demo_token_splitter() -> None:
    """Token 切割器 — 按 token 数精确切割。"""
    print("=" * 60)
    print("TokenSplitter — Token 精确切割")
    print("=" * 60)

    text = "这是一段用于测试 token 切割器的中文文本。" * 10
    splitter = TokenSplitter(chunk_size=30, chunk_overlap=5)
    chunks = splitter.split_text(text)

    print(f"  输入长度: {len(text)} 字符")
    print(f"  切片数量: {len(chunks)}")
    for chunk in chunks:
        print(f"  [{chunk.index}] ({len(chunk.content)}字) {_preview(chunk.content, 60)}")
    print()


def demo_chain_splitter() -> None:
    """链式策略选择 — 根据文件类型自动选择切割器。"""
    print("=" * 60)
    print("ChainSplitter — 自动策略选择")
    print("=" * 60)

    loader = ChainLoader()
    splitter = ChainSplitter(chunk_size=500, chunk_overlap=80)

    test_files = [
        SAMPLES / "demo_article.md",
        SAMPLES / "demo_app.py",
        SAMPLES / "readme.txt",
    ]

    for file_path in test_files:
        if not file_path.exists():
            print(f"  [SKIP] {file_path.name}: 文件不存在")
            continue
        docs = loader.load_file(file_path)
        if not docs:
            print(f"  [SKIP] {file_path.name}: 加载结果为空")
            continue
        doc = docs[0]
        chunks = splitter.split_document(doc)

        strategies = set(c.strategy for c in chunks)
        print(f"  {file_path.name}")
        print(f"    策略: {', '.join(strategies)} | 切片: {len(chunks)}")
        if chunks:
            print(f"    首片: {_preview(chunks[0].content, 70)}")
    print()


def demo_split_chunk_metadata() -> None:
    """展示 SplitChunk 元数据的差异。"""
    print("=" * 60)
    print("SplitChunk 元数据对比")
    print("=" * 60)

    # Markdown 元数据包含标题层级
    md_text = "# 章节\n\n段落内容。\n\n## 小节\n\n更多内容。"
    md_chunks = MarkdownSplitter(chunk_size=500).split_text(md_text)
    print("  Markdown 切片元数据:")
    for c in md_chunks:
        print(f"    [{c.index}] strategy={c.strategy} metadata={c.metadata}")

    # 代码元数据包含语言名
    code_chunks = CodeSplitter.from_extension(".py", chunk_size=500).split_text("def f(): pass")
    if code_chunks:
        print(f"\n  代码切片元数据: {code_chunks[0].metadata}")

    # 递归切割无额外元数据
    rec_chunks = RecursiveSplitter(chunk_size=500).split_text("普通文本")
    if rec_chunks:
        print(f"  递归切片元数据: {rec_chunks[0].metadata}")
    print()



if __name__ == "__main__":
    demo_recursive_splitter()
    demo_markdown_splitter()
    demo_code_splitter()
    demo_token_splitter()
    demo_chain_splitter()
    demo_split_chunk_metadata()
    print("全部示例运行完成。")
