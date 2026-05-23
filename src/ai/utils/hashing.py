"""通用哈希工具类 — 集中管理项目中所有哈希和唯一标识操作。

供各模块统一调用，消除散落的 hashlib/uuid 调用。

Usage::

    from src.ai.utils.hashing import HashUtils as H

    H.sha256("content")                       # 完整 SHA-256
    H.sha256("a", "b", length=16)             # 截断哈希（缓存键）
    H.md5("content")                          # MD5 指纹
    H.content_key("长文本...")                 # 内容去重键
    H.uuid()                                  # 生成 UUID4 字符串
    H.config_hash(base_url="...", timeout=30) # 配置哈希
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any


class HashUtils:
    """静态方法集合，统一处理项目中的哈希和唯一标识操作。"""

    # ── SHA-256 ─────────────────────────────────────────

    @staticmethod
    def sha256(*parts: str, length: int = 0) -> str:
        """计算 SHA-256 哈希，支持多部分拼接和截断。

        Args:
            parts: 待哈希的字符串部分，用 "|" 拼接。
            length: 截断长度，0 表示返回完整 64 位十六进制。

        Returns:
            十六进制哈希字符串。
        """
        raw = "|".join(parts)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return digest[:length] if length > 0 else digest

    # ── MD5 ─────────────────────────────────────────────

    @staticmethod
    def md5(*parts: str, length: int = 0) -> str:
        """计算 MD5 哈希，适用于轻量级内容指纹。

        Args:
            parts: 待哈希的字符串部分，用 "|" 拼接。
            length: 截断长度，0 表示返回完整 32 位十六进制。

        Returns:
            十六进制哈希字符串。
        """
        raw = "|".join(parts)
        digest = hashlib.md5(raw.encode()).hexdigest()
        return digest[:length] if length > 0 else digest

    # ── 内容去重键 ──────────────────────────────────────

    @staticmethod
    def content_key(text: str, length: int = 200) -> str:
        """从文本生成稳定的去重键。

        截取前 N 个字符作为去重标识，适用于 RAG 检索结果去重等场景。
        与直接切片不同，空白字符会被归一化，提高匹配率。

        Args:
            text: 原始文本。
            length: 参与去重的前缀长度，默认 200。

        Returns:
            去重键（归一化后的文本前缀）。
        """
        normalized = " ".join(text.split())
        return normalized[:length]

    @staticmethod
    def content_hash(text: str, length: int = 16) -> str:
        """从文本生成哈希指纹，适用于超长文本的去重。

        比 content_key 更节省内存，但不可逆。

        Args:
            text: 原始文本。
            length: 截断哈希长度，默认 16。

        Returns:
            截断后的 SHA-256 哈希字符串。
        """
        return HashUtils.sha256(text, length=length)

    # ── UUID ────────────────────────────────────────────

    @staticmethod
    def uuid() -> str:
        """生成 UUID4 字符串。

        用于会话 ID、任务 ID 等需要全局唯一标识的场景。

        Returns:
            UUID4 字符串，如 "550e8400-e29b-41d4-a716-446655440000"。
        """
        return str(uuid.uuid4())

    # ── 配置哈希 ────────────────────────────────────────

    @staticmethod
    def config_hash(**kwargs: Any) -> int:
        """为配置参数生成稳定的哈希值，用作内存缓存键。

        将所有参数值转为字符串后排序拼接，再取 Python 内置 hash。
        适用于 LLM Provider 实例缓存等场景。

        Args:
            **kwargs: 配置参数。

        Returns:
            整数哈希值。
        """
        key_parts = tuple(
            str(v) if v is not None else "" for _, v in sorted(kwargs.items())
        )
        return hash(key_parts)
