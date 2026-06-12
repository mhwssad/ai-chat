"""Skill 领域类型 — Agent Skills 开放标准。

索引仅保留控制发现/匹配行为的最小字段：
- name, description, source_path — 索引键值和文件路径
- disable_model_invocation, user_invocable — 控制注入行为的标准字段
- argument_hint — 上下文注入提示

其余 frontmatter 字段（model, context, agent, allowed-tools 等）
由 AI 从 SKILL.md 原始内容自行解读，不在索引中维护。
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillIndex:
    """技能索引条目 — 启动扫描阶段的轻量记录（仅 frontmatter，不含 body）。"""

    name: str
    description: str
    source_path: Path
    disable_model_invocation: bool = False
    user_invocable: bool = True
    argument_hint: str | None = None
