"""工具注册工厂 — 提供统一的工具注册、获取和自动扫描能力。

用法::

    from ai_chat.tools.registry import tool_registry

    # 按名称获取工具
    tool = tool_registry.get("read_file")

    # 获取全部已注册工具（供 Agent 绑定）
    tools = tool_registry.get_all()

    # 自动扫描包下所有 @tool 装饰的函数
    tool_registry.scan("ai_chat.tools")
"""

import importlib
import inspect
import threading
from typing import Self

from langchain_core.tools import BaseTool, tool


class ToolRegistry:
    """工具注册工厂。

    - 单例：全局唯一实例，通过 ``tool_registry`` 模块级变量暴露。
    - 线程安全：所有写操作受锁保护。
    - 不允许重复注册同名工具，重复时抛出 ``ValueError``。
    """

    _instance: Self | None = None
    _lock: threading.Lock = threading.Lock()

    _tools: dict[str, BaseTool]
    _init_lock: threading.Lock

    def __new__(cls) -> Self:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._tools = {}
                    instance._init_lock = threading.Lock()
                    cls._instance = instance
        return cls._instance

    # ------------------------------------------------------------------
    # 注册
    # ------------------------------------------------------------------

    def register(self, tool_obj: BaseTool) -> None:
        """注册一个工具。若同名工具已存在，抛出 ``ValueError``。"""
        name = tool_obj.name
        with self._init_lock:
            if name in self._tools:
                raise ValueError(f"工具名称重复：'{name}' 已注册")
            self._tools[name] = tool_obj

    def register_many(self, tools_list: list[BaseTool]) -> None:
        """批量注册工具。任一重名则整体中止。"""
        for t in tools_list:
            self.register(t)

    # ------------------------------------------------------------------
    # 获取
    # ------------------------------------------------------------------

    def get(self, name: str) -> BaseTool:
        """按名称获取工具。未找到时抛出 ``KeyError``。"""
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(f"未找到工具：'{name}'") from None

    def get_all(self) -> list[BaseTool]:
        """获取全部已注册工具列表，可直接传给 LangChain Agent。"""
        return list(self._tools.values())

    # ------------------------------------------------------------------
    # 自动扫描
    # ------------------------------------------------------------------

    def scan(self, package_path: str) -> int:
        """扫描指定包路径下所有模块，自动注册其中的 ``BaseTool`` 实例。

        Args:
            package_path: 点分隔的包路径，如 ``"ai_chat.tools"``。

        Returns:
            本次扫描新注册的工具数量。
        """
        package = importlib.import_module(package_path)
        count = 0

        if hasattr(package, "__path__"):
            pkg_dir = package.__path__[0]
            for module_info in _iter_submodules(pkg_dir, package_path):
                mod = importlib.import_module(module_info)
                for _attr_name, obj in inspect.getmembers(mod):
                    if isinstance(obj, BaseTool) and obj.name not in self._tools:
                        self._tools[obj.name] = obj
                        count += 1

        return count

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

def registered_tool(func=None, *, registry: ToolRegistry | None = None):
    """装饰器：等价于 ``@tool`` + 自动注册到全局工厂。

    用法::

        @registered_tool
        def my_tool(x: str) -> str:
            '''工具描述'''
            ...
    """
    reg = registry or tool_registry

    def decorator(fn):
        tool_obj = tool(fn)
        reg.register(tool_obj)
        return tool_obj

    if func is not None:
        return decorator(func)
    return decorator


# ======================================================================
# 辅助函数
# ======================================================================

def _iter_submodules(pkg_dir: str, pkg_name: str):
    """遍历包目录，生成所有子模块的完整导入路径。"""
    from pathlib import Path

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
