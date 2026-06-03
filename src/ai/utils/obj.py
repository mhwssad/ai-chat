"""通用对象操作工具集。

集中项目内反复出现的 dict/attr/类型检测 模式，避免各处重复实现。
"""

import dataclasses
import functools
import importlib
import pkgutil
from pathlib import Path
from typing import Any, TypeVar

from src.ai.config.logging_setup import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=type)


def singleton(cls: F) -> F:
    """单例模式装饰器，确保类只有一个实例。

    使用实例缓存实现，第一次实例化后返回缓存的实例。

    Args:
        cls: 要装饰的类

    Returns:
        装饰后的类（仍是原类，只是强制单例行为）

    示例:
        ```python
        @singleton
        class MySingleton:
            def __init__(self):
                self.value = 1

        a = MySingleton()
        b = MySingleton()
        assert a is b  # True，单例生效
        ```
    """

    @functools.wraps(cls)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not hasattr(wrapper, "_instance"):  # type: ignore[attr-defined]
            wrapper._instance = cls(*args, **kwargs)  # type: ignore[attr-defined]
        return wrapper._instance  # type: ignore[attr-defined]

    return wrapper  # type: ignore[return-value]


class Obj:
    """通用对象操作工具集。"""

    # ==================================================================
    # 内容提取
    # ==================================================================

    @staticmethod
    def extract_text(content: Any) -> str:
        """从消息 content 中提取纯文本。

        兼容三种格式：
        - ``str`` — 直接返回
        - ``list`` — 拼接所有 str 元素和 dict 元素的 ``text`` 字段
        - 其他 — ``str()`` 转换
        """
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item if isinstance(item, str) else str(item.get("text", ""))
                for item in content
            )
        return str(content)

    @staticmethod
    def safe_content_str(msg: Any) -> str:
        """安全获取消息的文本内容。

        处理 ``msg.content`` 为 str / list / 其他类型的情况，
        不会因 content 为 None 而报错。
        """
        content = getattr(msg, "content", "")
        if not content:
            return ""
        return Obj.extract_text(content)

    # ==================================================================
    # 字典操作
    # ==================================================================

    @staticmethod
    def merge(*dicts: dict | None) -> dict:
        """合并多个字典，右侧覆盖左侧，返回新字典。

        跳过 ``None`` 参数，适合 ``base | override | final`` 三层合并场景。
        """
        result: dict = {}
        for d in dicts:
            if d:
                result.update(d)
        return result

    @staticmethod
    def deep_get(d: dict, key: str, default: Any = None, *, sep: str = ".") -> Any:
        """安全访问嵌套字典。

        Args:
            d: 字典
            key: 点分隔的嵌套路径，如 ``"a.b.c"``
            default: 路径不存在时的返回值
            sep: 路径分隔符

        Returns:
            嵌套值或 default
        """
        current = d
        for part in key.split(sep):
            if not isinstance(current, dict):
                return default
            current = current.get(part)  # type: ignore[assignment]
            if current is None:
                return default
        return current

    @staticmethod
    def first_of(d: dict, *keys: str, default: Any = None) -> Any:
        """从字典中按优先级取值，返回第一个非 None 的结果。

        典型场景：``first_of(usage, "prompt_tokens", "input_tokens", default=0)``
        """
        for key in keys:
            val = d.get(key)
            if val is not None:
                return val
        return default

    # ==================================================================
    # 属性操作
    # ==================================================================

    @staticmethod
    def pluck(obj: Any, *attrs: str, default: Any = None) -> dict[str, Any]:
        """从对象上批量提取属性为字典。

        属性不存在时使用 default 值。

        Returns:
            ``{attr_name: attr_value, ...}``
        """
        return {attr: getattr(obj, attr, default) for attr in attrs}

    @staticmethod
    def safe_update(
        obj: Any, fields: dict[str, Any], *, ignore_none: bool = True
    ) -> None:
        """安全地将字段字典更新到对象属性上。

        仅更新对象实际拥有的属性（``hasattr`` 检查），
        默认跳过值为 ``None`` 的字段。
        """
        for key, value in fields.items():
            if ignore_none and value is None:
                continue
            if hasattr(obj, key):
                setattr(obj, key, value)

    # ==================================================================
    # 类型检测 & 序列化
    # ==================================================================

    @staticmethod
    def is_pydantic(obj: Any) -> bool:
        """判断是否为 Pydantic model 实例或类。"""
        try:
            from pydantic import BaseModel

            return isinstance(obj, BaseModel) or (
                isinstance(obj, type) and issubclass(obj, BaseModel)
            )
        except ImportError:
            return False

    @staticmethod
    def is_dataclass(obj: Any) -> bool:
        """判断是否为 dataclass 实例（不包括类本身）。"""
        return dataclasses.is_dataclass(obj) and not isinstance(obj, type)

    @staticmethod
    def to_dict(obj: Any) -> dict:
        """将 Pydantic model 或 dataclass 实例转为纯字典。

        不兼容的类型直接抛 TypeError。
        """
        try:
            from pydantic import BaseModel

            if isinstance(obj, BaseModel):
                return obj.model_dump(by_alias=True)
        except ImportError:
            pass

        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)

        raise TypeError(
            f"无法将 {type(obj).__name__} 转换为 dict，仅支持 Pydantic model 和 dataclass"
        )

    # ==================================================================
    # 模块发现
    # ==================================================================

    @staticmethod
    def discover_classes(
        package_dir: str | Path,
        base_class: type,
        *,
        package_name: str = "",
        recursive: bool = False,
    ) -> dict[str, type]:
        """自动发现子包中某个基类的所有子类。

        遍历 ``package_dir`` 下的 Python 模块，导入后收集 ``base_class`` 的子类。

        Args:
            package_dir: 包目录路径
            base_class: 要收集的基类
            package_name: 模块前缀（默认用 ``base_class`` 所在包名推导）
            recursive: 是否递归搜索子目录

        Returns:
            ``{类名: 类对象}`` 字典
        """
        package_dir = Path(package_dir)
        if not package_name:
            package_name = base_class.__module__

        exported: dict[str, type] = {}

        for info in pkgutil.iter_modules([str(package_dir)]):
            mod = importlib.import_module(f"{package_name}.{info.name}")
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, base_class)
                    and attr is not base_class
                ):
                    exported[attr_name] = attr

        return exported
