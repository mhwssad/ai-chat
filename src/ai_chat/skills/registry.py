"""技能注册表 — 提供统一的技能注册、获取和自动扫描能力。

用法::

    from ai_chat.skills.registry import skill_registry

    # 按名称获取技能
    skill = skill_registry.get("translate")

    # 获取全部已注册技能
    skills = skill_registry.get_all()

    # 自动扫描 .md 文件
    skill_registry.scan(Path(__file__).parent / "skills")
"""

import threading
from pathlib import Path
from typing import Optional, Self

from src.ai_chat.skills.models import SkillConfig


class SkillRegistry:
    """技能注册表。单例，线程安全。"""

    _instance: Optional[Self] = None
    _lock: threading.Lock = threading.Lock()

    _skills: dict[str, SkillConfig]
    _init_lock: threading.Lock

    def __new__(cls) -> Self:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._skills = {}
                    instance._init_lock = threading.Lock()
                    cls._instance = instance
        return cls._instance

    def register(self, skill: SkillConfig) -> None:
        """注册一个技能。同名技能已存在时跳过。"""
        with self._init_lock:
            if skill.name not in self._skills:
                self._skills[skill.name] = skill

    def get(self, name: str) -> SkillConfig:
        """按名称获取技能。未找到时抛出 KeyError。"""
        try:
            return self._skills[name]
        except KeyError:
            raise KeyError(f"未找到技能：'{name}'，已注册：{list(self._skills)}") from None

    def get_all(self) -> list[SkillConfig]:
        """获取全部已注册技能列表。"""
        return list(self._skills.values())

    def find_by_trigger(self, text: str) -> Optional[SkillConfig]:
        """根据用户输入匹配技能（/name 或 /name args）。"""
        stripped = text.strip()
        for skill in self._skills.values():
            if stripped == f"/{skill.name}" or stripped.startswith(f"/{skill.name} "):
                return skill
        return None

    def scan(self, skills_dir: Path) -> int:
        """扫描目录下的子目录，自动注册包含 SKILL.md 的技能。"""
        from src.ai_chat.skills.loader import load_skill_file

        if not skills_dir.exists():
            return 0

        count = 0
        for item in sorted(skills_dir.iterdir()):
            if item.is_dir():
                skill_md = item / "SKILL.md"
                if skill_md.exists():
                    skill = load_skill_file(skill_md)
                    if skill is not None:
                        self.register(skill)
                        count += 1
        return count

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __repr__(self) -> str:
        names = ", ".join(sorted(self._skills))
        return f"SkillRegistry({len(self)} skills: [{names}])"


def registered_skill(func=None, *, registry: Optional[SkillRegistry] = None):
    """装饰器：将函数返回的 SkillConfig 注册为技能。"""
    reg = registry or skill_registry

    def decorator(fn):
        config = fn()
        if isinstance(config, SkillConfig):
            reg.register(config)
        return config

    if func is not None:
        return decorator(func)
    return decorator


skill_registry = SkillRegistry()
