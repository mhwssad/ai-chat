"""文档加载器使用示例。

运行方式: uv run python -m docs.examples.loader_usage
"""

from pathlib import Path

from src.ai.core.loaders import ChainLoader, UnstructuredSettings
from src.ai.exception.loader_exception import LoaderError

# 示例文件目录
SAMPLES = Path(__file__).parent / "samples"


def demo_load_file() -> None:
    """加载单个文件。"""
    loader = ChainLoader()
    docs = loader.load_file(SAMPLES / "readme.txt")
    doc = docs[0]
    print("=== load_file ===")
    print(f"  标题: {doc.metadata.get('title')}")
    print(f"  MIME: {doc.metadata.get('mime_type')}")
    print(f"  大小: {doc.metadata.get('size_bytes')} bytes")
    print(f"  内容: {doc.page_content[:100]}")


def demo_load_batch() -> None:
    """批量加载多个文件。"""
    loader = ChainLoader()
    files = [
        SAMPLES / "readme.txt",
        SAMPLES / "article.md",
        SAMPLES / "script.py",
        SAMPLES / "garbled_sample.txt",
        SAMPLES / "sample.html",
        SAMPLES / "sample.xml",
        SAMPLES / "sample.json",
    ]
    docs = loader.load_batch(files)
    print(f"\n=== load_batch ({len(docs)} 个文档) ===")
    for doc in docs:
        title = doc.metadata.get("title", "?")
        preview = doc.page_content[:50].replace("\n", " ")
        print(f"  [{title}] {preview}")


def demo_load_dir() -> None:
    """加载目录下所有文件。"""
    loader = ChainLoader()
    docs = loader.load_dir(SAMPLES)
    print(f"\n=== load_dir ({len(docs)} 个文档) ===")
    for doc in docs:
        title = doc.metadata.get("title", "?")
        print(f"  [{title}] {len(doc.page_content)} 字符")


def demo_various_formats() -> None:
    """测试各种格式的文件加载。"""
    loader = ChainLoader()
    formats = [
        SAMPLES / "sample.html",
        SAMPLES / "sample.xml",
        SAMPLES / "sample.json",
        SAMPLES / "sample_data.tsv",
        SAMPLES / "sample.eml",
        SAMPLES / "config.yaml",
        SAMPLES / "notes.rst",
        SAMPLES / "garbled_sample.txt",
    ]
    print(f"\n=== 各种格式测试 ({len(formats)} 个文件) ===")
    for file_path in formats:
        try:
            docs = loader.load_file(file_path)
            print(f"  [OK] {file_path.name}: {len(docs[0].page_content)} 字符")
        except LoaderError as e:
            print(f"  [FAIL] {file_path.name}: {e.message}")


def demo_custom_settings() -> None:
    """使用自定义 UnstructuredSettings。"""
    custom_settings = UnstructuredSettings(
        mode="local",
        strategy="fast",
        max_characters=500_000,
    )
    loader = ChainLoader(settings=custom_settings)
    docs = loader.load_file(SAMPLES / "article.md")
    doc = docs[0]
    print("\n=== 自定义 UnstructuredSettings ===")
    print(f"  内容: {doc.page_content[:100]}")


def demo_error_handling() -> None:
    """错误处理示例。"""
    loader = ChainLoader()
    print("\n=== 错误处理 ===")

    try:
        loader.load_file("/nonexistent/file.txt")
    except LoaderError as e:
        print(f"  文件不存在: {e.message}")

    try:
        loader.load_file(SAMPLES)
    except LoaderError as e:
        print(f"  不是文件: {e.message}")


if __name__ == "__main__":
    demo_load_file()
    demo_load_batch()
    demo_load_dir()
    demo_various_formats()
    demo_custom_settings()
    demo_error_handling()
    print("\n全部示例运行完成。")
