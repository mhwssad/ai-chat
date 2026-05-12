"""技能文件加载器 — 解析 Markdown + YAML frontmatter 格式的技能定义文件。"""

from pathlib import Path
from typing import Optional

from src.ai_chat.skills.models import SkillConfig


def load_skill_file(path: Path) -> Optional[SkillConfig]:
    """从 .md 文件加载技能定义。

    格式::

        ---
        name: translate
        description: 翻译文本
        tools: [read_file, write_file]
        ---

        技能指令正文（作为 system_prompt）
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    yaml_text = parts[1].strip()
    body = parts[2].strip()

    if not body:
        return None

    meta = _parse_simple_yaml(yaml_text)

    name = meta.get("name") or path.parent.stem
    description = meta.get("description", "")
    tools = _parse_tools_list(meta.get("tools", ""))
    model = meta.get("model") or None
    args_template = meta.get("args_template") or None

    return SkillConfig(
        name=name,
        description=description,
        system_prompt=body,
        tools=tools,
        model=model,
        args_template=args_template,
        skill_dir=path.parent,
    )


def _parse_simple_yaml(text: str) -> dict[str, str]:
    """简易 YAML 解析，只处理 key: value 格式。"""
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _parse_tools_list(raw: str) -> list[str]:
    """解析 tools 字段，支持 [a, b] 和逗号分隔格式。"""
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1]
    items = [item.strip().strip("'\"") for item in raw.split(",")]
    return [item for item in items if item]
