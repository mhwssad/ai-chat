"""通用字符串处理工具类 — 集中管理项目中所有字符串操作。

供各模块统一调用，消除散落的字符串处理代码。

Usage::

    from src.ai.utils.strings import StringUtils as S

    S.truncate("长文本...", length=200)       # 截断
    S.mask_secret("sk-abcdefgh1234")          # 脱敏
    S.preview("多行\n文本", length=50)         # 预览
    S.normalize_input("  Hello  ")            # 归一化 → "hello"
    S.hash_key("a", "b", "c")                # 生成哈希键
"""

from __future__ import annotations

import hashlib
import re


class StringUtils:
    """静态方法集合，统一处理项目中的字符串操作。"""

    # ── 截断 ────────────────────────────────────────────

    @staticmethod
    def truncate(text: str, length: int = 200, end: str = "...") -> str:
        """截断文本到指定长度，超出部分用 end 替换。

        Args:
            text: 原始文本。
            length: 最大长度（含 end）。
            end: 截断标记，默认 "..."。

        Returns:
            截断后的文本，未超长则原样返回。
        """
        if len(text) <= length:
            return text
        cut = length - len(end)
        if cut <= 0:
            return end[:length]
        return text[:cut] + end

    @staticmethod
    def truncate_with_notice(text: str, length: int = 10_000) -> str:
        """截断文本并附加总长度提示。

        适用于命令输出、日志等需要告知用户完整大小的场景。

        Args:
            text: 原始文本。
            length: 最大保留长度。

        Returns:
            截断后的文本，末尾附加长度信息；未超长则原样返回。
        """
        if len(text) <= length:
            return text
        return text[:length] + f"\n... [输出已截断，共 {len(text)} 字符]"

    @staticmethod
    def abbreviate(text: str, length: int = 8) -> str:
        """取文本前 N 个字符作为缩写。

        常用于 session_id、哈希值等短标识的显示。

        Args:
            text: 原始文本。
            length: 保留长度，默认 8。

        Returns:
            前 N 个字符。
        """
        return text[:length]

    # ── 脱敏与遮蔽 ──────────────────────────────────────

    @staticmethod
    def mask_secret(secret: str, visible: int = 4) -> str:
        """遮蔽密钥/敏感字符串，仅保留首尾各 visible 位。

        Args:
            secret: 明文密钥。
            visible: 首尾各保留的字符数，默认 4。

        Returns:
            脱敏后的字符串，如 "abcd****efgh"。
        """
        if len(secret) <= visible * 2:
            return "****"
        return f"{secret[:visible]}****{secret[-visible:]}"

    # ── 显示与预览 ──────────────────────────────────────

    @staticmethod
    def preview(text: str, length: int = 50, end: str = "...") -> str:
        """生成适合 UI 展示的单行预览文本。

        换行符替换为空格，超出长度截断。

        Args:
            text: 原始文本。
            length: 最大预览长度（含 end）。
            end: 截断标记。

        Returns:
            单行预览文本。
        """
        clean = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
        return StringUtils.truncate(clean, length=length, end=end)

    @staticmethod
    def first_line(text: str) -> str:
        """提取文本的第一行。

        常用于 description、备注等多行文本的摘要显示。

        Args:
            text: 原始文本。

        Returns:
            第一行内容，空文本返回空字符串。
        """
        if not text:
            return ""
        return text.split("\n", 1)[0]

    # ── 归一化 ──────────────────────────────────────────

    @staticmethod
    def normalize_input(text: str) -> str:
        """归一化用户输入：去除首尾空白并转小写。

        Args:
            text: 用户输入。

        Returns:
            归一化后的文本。
        """
        return text.strip().lower()

    @staticmethod
    def safe_strip(text: str | None, default: str = "") -> str:
        """安全去除首尾空白，None 返回默认值。

        Args:
            text: 输入文本，可为 None。
            default: None 时返回的默认值。

        Returns:
            去除空白后的文本。
        """
        if text is None:
            return default
        return text.strip()

    # ── 哈希与编码 ──────────────────────────────────────

    @staticmethod
    def hash_key(*parts: str, length: int = 16) -> str:
        """将多个字符串部分拼接后生成 SHA-256 截断哈希。

        用于缓存键、去重标识等场景。

        Args:
            parts: 待哈希的字符串部分。
            length: 返回的哈希截断长度，默认 16。

        Returns:
            截断后的十六进制哈希字符串。
        """
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:length]

    # ── 命名转换 ────────────────────────────────────────

    @staticmethod
    def to_snake_case(text: str) -> str:
        """将 CamelCase / PascalCase 转换为 snake_case。

        Args:
            text: 原始名称。

        Returns:
            snake_case 格式字符串。
        """
        s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        return s.replace("-", "_").lower()

    @staticmethod
    def to_camel_case(text: str) -> str:
        """将 snake_case / kebab-case 转换为 camelCase。

        Args:
            text: 原始名称。

        Returns:
            camelCase 格式字符串。
        """
        parts = re.split(r"[_\-]+", text)
        if not parts:
            return ""
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])

    @staticmethod
    def slugify(text: str, max_length: int = 50) -> str:
        """将文本转换为 URL / 文件名友好的 slug。

        Args:
            text: 原始文本。
            max_length: 最大长度。

        Returns:
            仅含小写字母、数字和连字符的 slug 字符串。
        """
        s = text.lower().strip()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[\s_]+", "-", s)
        s = re.sub(r"-+", "-", s).strip("-")
        return s[:max_length]

    # ── 验证 ────────────────────────────────────────────

    @staticmethod
    def is_blank(text: str | None) -> bool:
        """判断字符串是否为空或仅含空白字符。

        Args:
            text: 待判断的字符串。

        Returns:
            为空或 None 返回 True。
        """
        return not text or not text.strip()

    @staticmethod
    def is_numeric(text: str) -> bool:
        """判断字符串是否为纯数字（正整数）。

        Args:
            text: 待判断的字符串。

        Returns:
            纯数字返回 True。
        """
        return text.isdigit()
