from __future__ import annotations

"""PromptManager — 提示词持久化管理器。

负责:
- 数据库 CRUD 操作（通过 PromptStore）
- 内存注册表同步（通过 prompt_registry）
- 模板解析缓存（通过 LRUCache）
- Jinja2 高级渲染（通过 prompt_env — 支持 for/if/include/extends/filter）
- 内置提示词种子数据初始化
- Jinja2 模板文件管理（data/prompts/ 目录）
"""

import re
from pathlib import Path
from typing import Optional

from jinja2 import meta as jinja_meta
from langchain_core.prompts import ChatPromptTemplate

from src.ai_chat.config.base_config import project_root
from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.prompts.jinja_env import prompt_env
from src.ai_chat.prompts.models import (
    PromptCreateRequest,
    PromptRecord,
    PromptVersionRecord,
)
from src.ai_chat.prompts.registry import prompt_registry
from src.ai_chat.prompts.store import PromptStore
from src.ai_chat.utils.cache import LRUCache

logger = get_logger(__name__)

PROMPTS_DIR = project_root / "data" / "prompts"

_MESSAGE_SPLITTER = re.compile(r"^==\s*(\w+)\s*==\s*$", re.MULTILINE)

_template_cache = LRUCache[str, ChatPromptTemplate](maxsize=64)
_file_content_cache = LRUCache[str, str](maxsize=32)


def _extract_variables(content: str) -> list[str]:
    """通过 Jinja2 AST 提取所有未声明变量。

    比 regex 更准确：能识别 {% for item in items %} 中的 items、
    {% if condition %} 中的 condition，同时排除循环变量 item。
    """
    try:
        ast = prompt_env.parse(content)
        return sorted(jinja_meta.find_undeclared_variables(ast))
    except Exception:
        # 解析失败时回退到空列表
        return []


def _render_content(content: str, **context) -> str:
    """用 Jinja2 Environment 渲染模板内容。"""
    template = prompt_env.from_string(content)
    return template.render(**context)


def _parse_messages_content(content: str) -> list[tuple[str, str]]:
    """解析 '== role ==\\n内容' 分隔格式为 (role, content) 列表。"""
    parts = _MESSAGE_SPLITTER.split(content)
    messages: list[tuple[str, str]] = []
    i = 1
    while i + 1 < len(parts):
        role = parts[i].strip()
        text = parts[i + 1].strip()
        messages.append((role, text))
        i += 2
    return messages


def _content_to_template(content: str) -> ChatPromptTemplate:
    """将存储的内容转换为 ChatPromptTemplate。

    支持 Jinja2 高级语法：for、if、set、filter、include、extends 等。
    每个角色块的内容作为独立的 Jinja2 模板解析。
    """
    messages = _parse_messages_content(content)
    if messages:
        return ChatPromptTemplate.from_messages(messages, template_format="jinja2")
    return ChatPromptTemplate.from_template(content, template_format="jinja2")


class PromptManager:
    """提示词持久化管理器。

    统一管理数据库中的提示词，并同步到内存注册表。
    使用 Jinja2 Environment 进行模板解析和渲染。
    """

    def __init__(self, store: Optional[PromptStore] = None) -> None:
        self._store = store or PromptStore()
        self._ensure_prompts_dir()
        self._init_builtin_prompts()
        self._load_to_registry()

    def _ensure_prompts_dir(self) -> None:
        PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    def _init_builtin_prompts(self) -> None:
        """初始化内置提示词 — 逐个检查，缺失则创建，tags 为空则补充。"""
        from src.ai_chat.prompts.builtin_data import BUILTIN_PROMPTS

        created = 0
        patched = 0
        for data in BUILTIN_PROMPTS:
            expected_tags = data.get("tags", "")
            if not self._store.exists(data["name"]):
                request = PromptCreateRequest(
                    name=data["name"],
                    content=data.get("content", ""),
                    file_path=data.get("file_path", ""),
                    source_type=data.get("source_type", "inline"),
                    description=data.get("description", ""),
                    tags=expected_tags,
                )
                variables = _extract_variables(data.get("content", ""))
                record = self._store.create(request, is_builtin=True, input_variables=variables)
                if record.source_type == "file" and record.file_path:
                    self._write_file(record.file_path, record.content)
                created += 1
            elif expected_tags:
                # 已存在但 tags 为空，从 seed data 补充
                try:
                    existing = self._store.get(data["name"])
                    if not existing.tags and expected_tags:
                        self._store.update(data["name"], tags=expected_tags)
                        patched += 1
                except KeyError:
                    pass

        if created or patched:
            logger.info("内置提示词: 新建 %d 个, 补充 tags %d 个", created, patched)

    def _load_to_registry(self) -> None:
        """将数据库中所有提示词加载到内存注册表并预热缓存。"""
        records = self._store.list(limit=10000)
        loaded = 0
        for record in records:
            content = self._get_content(record)
            if not content:
                continue
            try:
                template = _content_to_template(content)
                prompt_registry.register(record.name, template)
                _template_cache.put(record.name, template)
                loaded += 1
            except Exception as e:
                logger.warning("注册提示词 '%s' 失败: %s", record.name, e)
        logger.info("加载 %d/%d 条提示词到注册表", loaded, len(records))

    def _get_content(self, record: PromptRecord) -> str:
        """获取提示词的实际内容。file 类型优先读缓存。"""
        if record.source_type == "file" and record.file_path:
            cached = _file_content_cache.get(record.file_path)
            if cached is not None:
                return cached
            path = PROMPTS_DIR / record.file_path
            if path.exists():
                content = path.read_text(encoding="utf-8")
                _file_content_cache.put(record.file_path, content)
                return content
            if record.content:
                return record.content
        return record.content

    def _write_file(self, file_path: str, content: str) -> None:
        path = PROMPTS_DIR / file_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _delete_file(self, file_path: str) -> None:
        path = PROMPTS_DIR / file_path
        if path.exists():
            path.unlink()

    def _register_and_cache(self, name: str, content: str) -> None:
        template = _content_to_template(content)
        prompt_registry.register(name, template)
        _template_cache.put(name, template)

    def _invalidate(self, name: str) -> None:
        _template_cache.invalidate(name)
        prompt_registry.unregister(name)

    # ── CRUD ──────────────────────────────────────────

    def create_prompt(
        self,
        name: str,
        *,
        content: str = "",
        file_path: str = "",
        source_type: str = "inline",
        description: str = "",
        tags: str = "",
    ) -> PromptRecord:
        """创建提示词（事务一致性：DB 先写，文件后写，失败回滚）。"""
        if source_type == "file" and not file_path:
            file_path = f"{name.replace('.', '_')}.jinja2"

        request = PromptCreateRequest(
            name=name,
            content=content,
            file_path=file_path,
            source_type=source_type,
            description=description,
            tags=tags,
        )
        variables = _extract_variables(content)

        try:
            record = self._store.create(request, input_variables=variables)
        except Exception:
            logger.error("创建提示词 DB 失败: %s", name)
            raise

        if source_type == "file" and content:
            try:
                self._write_file(file_path, content)
            except Exception:
                logger.error("写入文件失败: %s, 回滚 DB", file_path)
                self._store.delete(name)
                raise

        self._register_and_cache(name, content)
        logger.info("创建提示词: %s (type=%s, vars=%s)", name, source_type, variables)
        return record

    def get_prompt(self, name: str) -> PromptRecord:
        """获取提示词详情。"""
        record = self._store.get(name)
        if record.source_type == "file" and record.file_path:
            actual = self._get_content(record)
            if actual:
                record.content = actual
        return record

    def get_template(self, name: str) -> ChatPromptTemplate:
        """获取 ChatPromptTemplate（带缓存）。"""
        cached = _template_cache.get(name)
        if cached is not None:
            return cached
        record = self.get_prompt(name)
        content = self._get_content(record)
        template = _content_to_template(content)
        _template_cache.put(name, template)
        return template

    def render(self, name: str, **context) -> str:
        """用 Jinja2 Environment 直接渲染模板为文本。

        支持 Jinja2 高级功能：for、if、set、filter、include 等。
        对于多消息模板（含 == role ==），渲染完整内容为纯文本。
        """
        record = self.get_prompt(name)
        content = self._get_content(record)
        return _render_content(content, **context)

    def update_prompt(self, name: str, **fields) -> PromptRecord:
        """更新提示词（自动备份旧版本到版本历史表）。"""
        content = fields.get("content")
        if content:
            fields["input_variables"] = _extract_variables(content)

        record = self._store.get(name)
        if record.is_builtin and not fields.get("_force"):
            raise ValueError(f"内置提示词 '{name}' 不可修改")

        self._store.create_version(record)

        updated = self._store.update(name, **fields)

        if record.source_type == "file" and content:
            _file_content_cache.invalidate(record.file_path)
            self._write_file(record.file_path, content)

        _template_cache.invalidate(name)
        actual_content = self._get_content(updated)
        if actual_content:
            self._register_and_cache(name, actual_content)

        logger.info("更新提示词: %s, fields=%s", name, list(fields.keys()))
        return updated

    def delete_prompt(self, name: str) -> None:
        """删除提示词（内置不可删）。"""
        record = self._store.get(name)
        if record.is_builtin:
            raise ValueError(f"内置提示词 '{name}' 不可删除")

        self._store.delete(name)
        self._invalidate(name)

        if record.source_type == "file" and record.file_path:
            _file_content_cache.invalidate(record.file_path)
            self._delete_file(record.file_path)

        logger.info("删除提示词: %s", name)

    # ── 列表与搜索 ────────────────────────────────────

    def list_prompts(self, limit: int = 50, offset: int = 0) -> list[PromptRecord]:
        return self._store.list(limit=limit, offset=offset)

    def search_prompts(self, keyword: str, limit: int = 50, offset: int = 0) -> list[PromptRecord]:
        return self._store.search(keyword, limit=limit, offset=offset)

    def count_prompts(self) -> int:
        return self._store.count()

    # ── 版本历史 ──────────────────────────────────────

    def list_versions(self, name: str, limit: int = 20) -> list[PromptVersionRecord]:
        """查看提示词的版本历史。"""
        return self._store.list_versions(name, limit=limit)

    def restore_version(self, name: str, version_id: int) -> PromptRecord:
        """回滚到指定版本。"""
        version = self._store.get_version(version_id)
        if version.prompt_name != name:
            raise ValueError(f"版本 {version_id} 不属于提示词 '{name}'")

        current = self._store.get(name)
        self._store.create_version(current)

        updated = self._store.update(
            name,
            content=version.content,
            file_path=version.file_path,
            source_type=version.source_type,
            input_variables=version.input_variables,
            description=version.description,
            tags=version.tags,
        )

        _template_cache.invalidate(name)
        actual_content = self._get_content(updated)
        if actual_content:
            self._register_and_cache(name, actual_content)

        logger.info("回滚提示词 %s 到版本 %d", name, version_id)
        return updated
