"""测试 LoaderRegistry 注册表。"""

from pathlib import Path
from collections.abc import Iterator

from langchain_core.documents import Document

from src.ai.core.loaders.base import LoaderStrategy
from src.ai.core.loaders.registry import LoaderRegistry


class MockLoaderA(LoaderStrategy):
    """模拟加载器 A。"""

    def __init__(self, file_path: str, **kwargs) -> None:
        self._file_path = file_path

    def can_handle(self, file_path: Path) -> bool:
        return True

    def lazy_load(self) -> Iterator[Document]:
        yield Document(page_content="A", metadata={})


class MockLoaderB(LoaderStrategy):
    """模拟加载器 B。"""

    def __init__(self, file_path: str, **kwargs) -> None:
        self._file_path = file_path

    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix == ".mock"

    def lazy_load(self) -> Iterator[Document]:
        yield Document(page_content="B", metadata={})


class TestLoaderRegistry:
    """测试 LoaderRegistry 类。"""

    def test_register_and_get_entries(self) -> None:
        """注册后能获取条目。"""
        registry = LoaderRegistry()
        registry.register(MockLoaderA, priority=100, name="a")
        registry.register(MockLoaderB, priority=200, name="b")

        entries = registry.get_entries()
        assert len(entries) == 2
        assert entries[0].name == "a"
        assert entries[1].name == "b"

    def test_priority_sorting(self) -> None:
        """条目按优先级排序。"""
        registry = LoaderRegistry()
        registry.register(MockLoaderA, priority=300)
        registry.register(MockLoaderB, priority=100)

        entries = registry.get_entries()
        assert entries[0].loader_cls is MockLoaderB
        assert entries[1].loader_cls is MockLoaderA

    def test_default_name_from_class(self) -> None:
        """未指定 name 时取类名。"""
        registry = LoaderRegistry()
        registry.register(MockLoaderA, priority=100)
        entries = registry.get_entries()
        assert entries[0].name == "MockLoaderA"

    def test_clear(self) -> None:
        """清空注册表。"""
        registry = LoaderRegistry()
        registry.register(MockLoaderA, priority=100)
        registry.clear()
        assert len(registry.get_entries()) == 0

    def test_register_duplicate_priority(self) -> None:
        """相同优先级的条目按注册顺序排列。"""
        registry = LoaderRegistry()
        registry.register(MockLoaderA, priority=100, name="first")
        registry.register(MockLoaderB, priority=100, name="second")

        entries = registry.get_entries()
        assert entries[0].name == "first"
        assert entries[1].name == "second"

    def test_auto_registration_from_init(self) -> None:
        """导入 loaders 模块后内置加载器自动注册。"""
        from src.ai.core.loaders import loader_registry

        entries = loader_registry.get_entries()
        names = [e.name for e in entries]
        assert "unstructured" in names
        assert "ocr_image" in names
        assert "plain_text" in names

        # 验证优先级顺序
        priorities = [e.priority for e in entries]
        assert priorities == sorted(priorities)
