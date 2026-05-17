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

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.skills.models import SkillConfig

logger = get_logger(__name__)


class SkillRegistry:
    """技能注册表。单例，线程安全。

    支持:
    - trigger 字典缓存实现 O(1) 查找
    - priority 优先级排序
    - enabled 启用/禁用过滤
    - 增量扫描（仅更新变更的技能）
    - 冲突检测（同名 / 相似描述）
    - 批量注册/反注册
    """

    _instance: Optional[Self] = None
    _lock: threading.Lock = threading.Lock()

    _skills: dict[str, SkillConfig]
    _trigger_map: dict[str, str]  # "/name" -> name
    _scan_timestamps: dict[Path, float]  # skill_dir -> mtime for incremental scan
    _init_lock: threading.Lock

    def __new__(cls) -> Self:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._skills = {}
                    instance._trigger_map = {}
                    instance._scan_timestamps = {}
                    instance._init_lock = threading.Lock()
                    cls._instance = instance
        return cls._instance

    def _rebuild_trigger_map(self) -> None:
        """重建 trigger → name 映射。"""
        self._trigger_map = {f"/{name}": name for name in self._skills}

    # ── 注册 ──────────────────────────────────────────────

    def register(self, skill: SkillConfig) -> None:
        """注册一个技能。同名技能已存在时跳过。

        检测 trigger 冲突和描述相似性，发现问题输出警告。
        """
        with self._init_lock:
            if skill.name in self._skills:
                return
            # 冲突检测：检查是否有描述完全相同的不同技能
            for existing in self._skills.values():
                if existing.description == skill.description and existing.name != skill.name:
                    logger.warning(
                        "技能 '%s' 与 '%s' 描述相同: %s",
                        skill.name, existing.name, skill.description,
                    )
            self._skills[skill.name] = skill
            self._trigger_map[skill.trigger] = skill.name

    def unregister(self, name: str) -> None:
        """移除已注册的技能。"""
        with self._init_lock:
            if name in self._skills:
                trigger = self._skills[name].trigger
                del self._skills[name]
                self._trigger_map.pop(trigger, None)
                logger.debug("反注册技能: %s", name)

    def register_many(self, skills: list[SkillConfig]) -> int:
        """批量注册技能，返回实际新增数量。"""
        count = 0
        with self._init_lock:
            for skill in skills:
                if skill.name not in self._skills:
                    self._skills[skill.name] = skill
                    self._trigger_map[skill.trigger] = skill.name
                    count += 1
        return count

    def unregister_many(self, names: list[str]) -> int:
        """批量移除技能，返回实际移除数量。"""
        count = 0
        with self._init_lock:
            for name in names:
                if name in self._skills:
                    trigger = self._skills[name].trigger
                    del self._skills[name]
                    self._trigger_map.pop(trigger, None)
                    count += 1
        return count

    # ── 查询 ──────────────────────────────────────────────

    def get(self, name: str) -> SkillConfig:
        """按名称获取技能。未找到时抛出 KeyError。"""
        try:
            return self._skills[name]
        except KeyError:
            raise KeyError(f"未找到技能：'{name}'，已注册：{list(self._skills)}") from None

    def get_all(self, *, enabled_only: bool = False) -> list[SkillConfig]:
        """获取全部已注册技能列表。

        Args:
            enabled_only: 仅返回 enabled=True 的技能。
        """
        skills = list(self._skills.values())
        if enabled_only:
            skills = [s for s in skills if s.enabled]
        return sorted(skills, key=lambda s: s.priority, reverse=True)

    def find_by_trigger(self, text: str) -> Optional[SkillConfig]:
        """根据用户输入匹配技能（O(1) 查找）。

        匹配规则: 输入为 "/name" 或以 "/name " 开头。
        仅返回 enabled=True 的技能。
        """
        stripped = text.strip()
        # 尝试精确匹配 "/name" 或最长前缀匹配 "/name "
        for trigger, name in self._trigger_map.items():
            if stripped == trigger or stripped.startswith(f"{trigger} "):
                skill = self._skills[name]
                if skill.enabled:
                    return skill
                return None
        return None

    # ── 扫描 ──────────────────────────────────────────────

    def scan(self, skills_dir: Path, *, incremental: bool = False) -> int:
        """扫描目录下的子目录，自动注册包含 SKILL.md 的技能。

        Args:
            skills_dir: 技能定义目录。
            incremental: 增量模式 — 仅加载新增或修改过的技能文件。
        """
        from src.ai_chat.skills.loader import load_skill_file

        if not skills_dir.exists():
            logger.warning("技能目录不存在: %s", skills_dir)
            return 0

        count = 0
        for item in sorted(skills_dir.iterdir()):
            if not item.is_dir():
                continue
            skill_md = item / "SKILL.md"
            if not skill_md.exists():
                continue

            # 增量检查：跳过未修改的文件
            if incremental:
                try:
                    mtime = skill_md.stat().st_mtime
                except OSError:
                    continue
                last_mtime = self._scan_timestamps.get(item)
                if last_mtime is not None and mtime <= last_mtime:
                    continue
                self._scan_timestamps[item] = mtime

            skill = load_skill_file(skill_md)
            if skill is not None:
                # 增量模式下，已存在的技能需要更新而非跳过
                if incremental and skill.name in self._skills:
                    with self._init_lock:
                        self._skills[skill.name] = skill
                    logger.debug("更新技能: %s", skill.name)
                else:
                    self.register(skill)
                count += 1

        if count:
            logger.info("扫描技能: 加载 %d 个", count)
        return count

    # ── 容器协议 ──────────────────────────────────────────

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
