"""提示词子系统 DI 容器。"""

from typing import Any

from dependency_injector import containers, providers


def _create_prompt_service(store):
    """提示词模板服务。"""
    from src.ai.core.prompts.renderer import PromptRenderer
    from src.ai.core.prompts.service import PromptService

    return PromptService(renderer=PromptRenderer(), store=store)


class PromptContainer(containers.DeclarativeContainer):
    """提示词子系统容器。"""

    # 外部依赖
    store: Any = providers.Dependency()

    prompt_service = providers.Singleton(_create_prompt_service, store=store)
