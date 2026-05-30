"""技能子系统 DI 容器。"""

from dependency_injector import containers, providers


def _create_skill_service():
    """技能发现服务。"""
    from src.ai.core.skills.loader import SkillLoader
    from src.ai.core.skills.matcher import SkillMatcher
    from src.ai.core.skills.renderer import SkillRenderer
    from src.ai.core.skills.resolver import SkillResolver
    from src.ai.core.skills.service import SkillService

    return SkillService(
        loader=SkillLoader(),
        renderer=SkillRenderer(),
        resolver=SkillResolver(),
        matcher=SkillMatcher(),
    )


class SkillContainer(containers.DeclarativeContainer):
    """技能子系统容器。"""

    skill_service = providers.Singleton(_create_skill_service)
