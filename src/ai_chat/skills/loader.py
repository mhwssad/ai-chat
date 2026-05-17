"""技能文件加载器 — 解析 Markdown + YAML frontmatter 格式的技能定义文件。"""

from pathlib import Path
from typing import Optional

import yaml

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.skills.models import SkillConfig

logger = get_logger(__name__)


def load_skill_file(path: Path) -> Optional[SkillConfig]:
    """从 .md 文件加载技能定义。

    格式::

        ---
        name: translate
        description: 翻译文本
        tools: [read_file, write_file]
        enabled: true
        priority: 0
        ---

        技能指令正文（作为 system_prompt）
    """
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("技能文件不存在: %s", path)
        return None
    except UnicodeDecodeError as e:
        logger.error("技能文件编码错误: %s (%s)", path, e)
        return None

    if not content.startswith("---"):
        logger.warning("技能文件缺少 frontmatter: %s", path)
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        logger.warning("技能文件格式错误（缺少闭合 ---）: %s", path)
        return None

    yaml_text = parts[1].strip()
    body = parts[2].strip()

    if not body:
        logger.warning("技能文件缺少正文内容: %s", path)
        return None

    meta = _parse_yaml(yaml_text)

    name = meta.get("name") or path.parent.stem
    description = meta.get("description", "")
    tools = _parse_tools(meta.get("tools"))
    model = meta.get("model") or None
    args_template = meta.get("args_template") or None
    enabled = meta.get("enabled", True)
    priority = int(meta.get("priority", 0))

    return SkillConfig(
        name=name,
        description=description,
        system_prompt=body,
        tools=tools,
        model=model,
        args_template=args_template,
        enabled=enabled,
        priority=priority,
        skill_dir=path.parent,
    )


def _parse_yaml(text: str) -> dict:
    """使用 yaml.safe_load 解析 frontmatter，失败时回退到简易解析。"""
    try:
        result = yaml.safe_load(text)
        if isinstance(result, dict):
            return result
    except yaml.YAMLError:
        pass
    # 回退到简易解析
    return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict[str, str]:
    """简易 YAML 解析，只处理 key: value 格式（回退方案）。"""
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _parse_tools(raw) -> list[str]:
    """解析 tools 字段，支持列表和逗号分隔字符串。"""
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    # 字符串格式："[a, b]" 或 "a, b"
    text = str(raw).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    items = [item.strip().strip("'\"") for item in text.split(",")]
    return [item for item in items if item]
