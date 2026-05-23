from enum import Enum
from typing import Any, Optional, Dict, TypeVar

T = TypeVar("T", bound="BaseEnum")


class BaseEnum(Enum):
    """
    枚举基类，提供常用的枚举操作方法
    """

    @classmethod
    def get_by_value(cls, value: Any) -> Optional[T]:
        """
        根据值获取枚举对象

        Args:
            value: 枚举值

        Returns:
            枚举对象，如果未找到则返回 None
        """
        for item in cls:
            if item.value == value:
                return item
        return None

    @classmethod
    def get_by_name(cls, name: str) -> Optional[T]:
        """
        根据名称获取枚举对象

        Args:
            name: 枚举名称

        Returns:
            枚举对象，如果未找到则返回 None
        """
        for item in cls:
            if item.name == name:
                return item
        return None

    @classmethod
    def get_by_value_ignore_case(cls, value: str) -> Optional[T]:
        """
        根据值获取枚举对象（不区分大小写）

        Args:
            value: 枚举值（字符串）

        Returns:
            枚举对象，如果未找到则返回 None
        """
        for item in cls:
            if isinstance(item.value, str) and item.value.lower() == value.lower():
                return item
        return None

    @classmethod
    def get_by_name_ignore_case(cls, name: str) -> Optional[T]:
        """
        根据名称获取枚举对象（不区分大小写）

        Args:
            name: 枚举名称

        Returns:
            枚举对象，如果未找到则返回 None
        """
        for item in cls:
            if item.name.lower() == name.lower():
                return item
        return None

    @classmethod
    def get_all_values(cls) -> list[Any]:
        """
        获取所有枚举值

        Returns:
            所有值列表
        """
        return [item.value for item in cls]

    @classmethod
    def get_all_names(cls) -> list[str]:
        """
        获取所有枚举名称

        Returns:
            所有名称列表
        """
        return [item.name for item in cls]

    @classmethod
    def is_valid_value(cls, value: Any) -> bool:
        """
        验证值是否有效

        Args:
            value: 待验证的值

        Returns:
            如果值有效返回 True，否则返回 False
        """
        return cls.get_by_value(value) is not None

    @classmethod
    def is_valid_name(cls, name: str) -> bool:
        """
        验证名称是否有效

        Args:
            name: 待验证的名称

        Returns:
            如果名称有效返回 True，否则返回 False
        """
        return cls.get_by_name(name) is not None

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """
        将枚举转换为字典（名称 -> 值）

        Returns:
            字典，键为枚举名称，值为枚举值
        """
        return {item.name: item.value for item in cls}

    @classmethod
    def to_reverse_dict(cls) -> Dict[Any, str]:
        """
        将枚举转换为反向字典（值 -> 名称）

        Returns:
            字典，键为枚举值，值为枚举名称
        """
        return {item.value: item.name for item in cls}

    @classmethod
    def get_name_by_value(cls, value: Any) -> Optional[str]:
        """
        根据值获取枚举名称

        Args:
            value: 枚举值

        Returns:
            枚举名称，如果未找到则返回 None
        """
        enum_item = cls.get_by_value(value)
        return enum_item.name if enum_item else None

    @classmethod
    def get_value_by_name(cls, name: str) -> Optional[Any]:
        """
        根据名称获取枚举值

        Args:
            name: 枚举名称

        Returns:
            枚举值，如果未找到则返回 None
        """
        enum_item = cls.get_by_name(name)
        return enum_item.value if enum_item else None

    def __str__(self) -> str:
        """
        返回枚举的字符串表示

        Returns:
            枚举的字符串表示（格式：name=value）
        """
        return f"{self.name}={self.value}"

    def __repr__(self) -> str:
        """
        返回枚举的详细字符串表示

        Returns:
            枚举的详细字符串表示
        """
        return f"<{self.__class__.__name__}.{self.name}: {self.value}>"
