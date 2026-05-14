"""工具注册工厂 — 提供工具分型、系统工具自动加载和按名称懒加载能力。"""

import importlib
import sys
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Self

from langchain_core.tools import BaseTool, tool


class ToolType(str, Enum):
    """工具固定分类。"""

    SYSTEM = "system"
    CUSTOM = "custom"
    MCP = "mcp"


@dataclass
class ToolRecord:
    """已加载工具及其注册元数据。"""

    tool: BaseTool
    tool_type: ToolType
    source_module: Optional[str]
    loaded: bool = True
    lazy_loaded: bool = False


class ToolRegistry:
    """工具注册工厂。"""

    _instance: Optional[Self] = None
    _lock: threading.Lock = threading.Lock()

    _tools: dict[str, ToolRecord]
    _init_lock: threading.Lock

    def __new__(cls) -> Self:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._tools = {}
                    instance._init_lock = threading.Lock()
                    instance._searched_modules = set()
                    instance._module_candidates = None
                    instance._current_loading_module = None
                    instance._module_tool_names = {}
                    cls._instance = instance
        return cls._instance

    @property
    def _system_modules(self) -> tuple[str, ...]:
        return (
            "src.ai_chat.tools.common",
            "src.ai_chat.tools.paths",
            "src.ai_chat.tools.search",
            "src.ai_chat.tools.command",
        )

    # ------------------------------------------------------------------
    # 注册
    # ------------------------------------------------------------------

    def register(
        self,
        tool_obj: BaseTool,
        *,
        tool_type: ToolType = ToolType.CUSTOM,
        source_module: Optional[str] = None,
        lazy_loaded: Optional[bool] = None,
    ) -> bool:
        """注册一个工具。同名工具已存在时静默跳过。"""
        name = tool_obj.name
        with self._init_lock:
            if name in self._tools:
                return False
            origin_module = source_module or getattr(tool_obj, "__module__", None)
            is_lazy = (
                lazy_loaded
                if lazy_loaded is not None
                else origin_module is not None and origin_module == self._current_loading_module
            )
            self._tools[name] = ToolRecord(
                tool=tool_obj,
                tool_type=tool_type,
                source_module=origin_module,
                loaded=True,
                lazy_loaded=is_lazy,
            )
            return True

    def register_many(
        self,
        tools_list: list[BaseTool],
        *,
        tool_type: ToolType = ToolType.CUSTOM,
        source_module: Optional[str] = None,
        lazy_loaded: Optional[bool] = None,
    ) -> int:
        """批量注册工具，返回新注册数量。"""
        count = 0
        for t in tools_list:
            if self.register(
                t,
                tool_type=tool_type,
                source_module=source_module,
                lazy_loaded=lazy_loaded,
            ):
                count += 1
        return count

    # ------------------------------------------------------------------
    # 获取
    # ------------------------------------------------------------------

    def get(self, name: str) -> BaseTool:
        """按名称获取工具；未命中时触发懒加载搜索。"""
        record = self._tools.get(name)
        if record is not None:
            return record.tool

        self.search_and_load(name)
        record = self._tools.get(name)
        if record is not None:
            return record.tool

        raise KeyError(f"未找到工具：'{name}'") from None

    def get_record(self, name: str) -> ToolRecord:
        """获取已加载工具的注册信息。"""
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(f"未找到工具：'{name}'") from None

    def get_all(self, tool_type: ToolType | None = None) -> list[BaseTool]:
        """获取当前已加载工具，可按类型过滤。"""
        records = self._tools.values()
        if tool_type is not None:
            records = [record for record in records if record.tool_type == tool_type]
        return [record.tool for record in records]

    def has(self, name: str) -> bool:
        """判断工具是否已加载。"""
        return name in self._tools

    def is_loaded(self, name: str) -> bool:
        """判断工具是否已在注册表中。"""
        return name in self._tools

    def resolve_tools(self, names: list[str]) -> list[BaseTool]:
        """按名称解析多个工具，按顺序返回结果。"""
        return [self.get(name) for name in names]

    # ------------------------------------------------------------------
    # 加载
    # ------------------------------------------------------------------

    def load_system_tools(self) -> int:
        """导入系统工具模块，注册系统工具。"""
        count = 0
        for module_name in self._system_modules:
            before = len(self._tools)
            importlib.import_module(module_name)
            self._searched_modules.add(module_name)
            count += len(self._tools) - before
        return count

    def search_and_load(self, name: str) -> bool:
        """按名称搜索未加载模块，找到目标工具后立即停止。"""
        for module_name in self._iter_searchable_modules():
            known_names = self._module_tool_names.get(module_name)
            if known_names is not None and name not in known_names:
                continue
            if module_name in self._searched_modules and name not in self._tools:
                continue

            before_names = set(self._tools)
            self._current_loading_module = module_name
            try:
                importlib.import_module(module_name)
            finally:
                self._current_loading_module = None

            new_names = {
                tool_name
                for tool_name in set(self._tools) - before_names
                if self._tools[tool_name].source_module == module_name
            }
            discovered_names = set(known_names or set()) | new_names
            self._module_tool_names[module_name] = discovered_names

            if name in self._tools:
                self._searched_modules.add(module_name)
                return True

            for tool_name in new_names:
                self._tools.pop(tool_name, None)
            sys.modules.pop(module_name, None)
        return False

    def scan(self, package_path: str) -> int:
        """兼容保留：导入指定包下所有子模块。"""
        package = importlib.import_module(package_path)
        if not hasattr(package, "__path__"):
            return 0

        count = 0
        for module_name in _iter_submodules(package.__path__[0], package_path):
            before = len(self._tools)
            importlib.import_module(module_name)
            self._searched_modules.add(module_name)
            count += len(self._tools) - before
        return count

    def _iter_searchable_modules(self) -> list[str]:
        if self._module_candidates is None:
            self._module_candidates = self._discover_local_modules()
        return self._module_candidates

    def _discover_local_modules(self) -> list[str]:
        package_name = "src.ai_chat.tools"
        package = importlib.import_module(package_name)
        package_paths = getattr(package, "__path__", [])
        if not package_paths:
            return []

        ignored = {
            f"{package_name}.registry",
            f"{package_name}.menu",
        }
        modules = []
        for module_name in _iter_submodules(package_paths[0], package_name):
            if module_name in ignored or module_name in self._system_modules:
                continue
            modules.append(module_name)
        return modules

    # ------------------------------------------------------------------
    # 调试
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __repr__(self) -> str:
        names = ", ".join(sorted(self._tools))
        return f"ToolRegistry({len(self)} tools: [{names}])"


# ======================================================================
# 注册装饰器 — @tool + 自动注册
# ======================================================================

def registered_tool(
    func=None,
    *,
    registry: ToolRegistry | None = None,
    tool_type: ToolType = ToolType.CUSTOM,
):
    """装饰器：等价于 ``@tool`` + 自动注册到全局工厂。

    用法::

        @registered_tool(tool_type=ToolType.SYSTEM)
        def my_tool(x: str) -> str:
            '''工具描述'''
            ...
    """
    reg = registry or tool_registry

    def decorator(fn):
        tool_obj = tool(fn)
        reg.register(tool_obj, tool_type=tool_type, source_module=fn.__module__)
        return tool_obj

    if func is not None:
        return decorator(func)
    return decorator


# ======================================================================
# 辅助函数
# ======================================================================

def _iter_submodules(pkg_dir: str, pkg_name: str):
    """遍历包目录，生成所有子模块的完整导入路径。"""
    pkg_path = Path(pkg_dir)
    for item in sorted(pkg_path.iterdir()):
        if item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
            yield f"{pkg_name}.{item.stem}"
        elif item.is_dir() and (item / "__init__.py").exists():
            yield f"{pkg_name}.{item.name}"
            yield from _iter_submodules(str(item), f"{pkg_name}.{item.name}")


# ======================================================================
# 全局单例
# ======================================================================

tool_registry = ToolRegistry()
