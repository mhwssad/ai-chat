"""FastAPI 依赖注入 — 桥接 DI 容器。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from src.ai.core.container import container

if TYPE_CHECKING:
    from src.ai.core.agent.orchestrator import AgentOrchestrator
    from src.ai.core.context.service import ContextService
    from src.ai.core.memory.service import MemoryService
    from src.ai.core.models.service import ModelService
    from src.ai.core.prompts.service import PromptService
    from src.ai.core.rag.service import RagService
    from src.ai.core.scheduler.service import SchedulerService
    from src.ai.core.skills.service import SkillService
    from src.ai.core.tools.manager import ToolManager
    from src.ai.core.tools.registry import ToolRegistry
    from src.ai.service.chat_service import ChatService
    from src.ai.service.image_service import ImageService
    from src.ai.service.tool_service import ToolService
    from src.ai.service.tts_service import TTSService


def get_model_service():
    """获取 ModelService 实例。"""
    return container.model_container.model_service()


def get_tool_registry():
    """获取 ToolRegistry 实例。"""
    return container.tool_container.tool_registry()


def get_tool_manager():
    """获取 ToolManager 实例。"""
    return container.tool_container.tool_manager()


def get_skill_service():
    """获取 SkillService 实例。"""
    return container.skill_container.skill_service()


def get_memory_service():
    """获取 MemoryService 实例。"""
    return container.memory_container.memory_service()


def get_prompt_service():
    """获取 PromptService 实例。"""
    return container.prompt_container.prompt_service()


def get_scheduler_service():
    """获取 SchedulerService 实例。"""
    return container.scheduler_container.scheduler_service()


def get_rag_service():
    """获取 RagService 实例。"""
    return container.rag_container.rag_service()


def get_context_service():
    """获取 ContextService 实例。"""
    return container.context_container.context_service()


def get_agent_orchestrator():
    """获取 AgentOrchestrator 实例。"""
    return container.agent_container.agent_orchestrator()


# ── 共享服务依赖 ─────────────────────────────────────────────


def get_chat_service():
    """获取共享 ChatService 实例。"""
    return container.service_container.chat_service()


def get_image_service():
    """获取共享 ImageService 实例。"""
    return container.service_container.image_service()


def get_tts_service():
    """获取共享 TTSService 实例。"""
    return container.service_container.tts_service()


def get_tool_service():
    """获取共享 ToolService 实例。"""
    return container.service_container.tool_service()


# 类型别名（用于路由函数签名）
ModelServiceDep = Annotated[ModelService, Depends(get_model_service)]
ToolRegistryDep = Annotated[ToolRegistry, Depends(get_tool_registry)]
ToolManagerDep = Annotated[ToolManager, Depends(get_tool_manager)]
SkillServiceDep = Annotated[SkillService, Depends(get_skill_service)]
MemoryServiceDep = Annotated[MemoryService, Depends(get_memory_service)]
PromptServiceDep = Annotated[PromptService, Depends(get_prompt_service)]
SchedulerServiceDep = Annotated[SchedulerService, Depends(get_scheduler_service)]
RagServiceDep = Annotated[RagService, Depends(get_rag_service)]
ContextServiceDep = Annotated[ContextService, Depends(get_context_service)]
AgentOrchestratorDep = Annotated[AgentOrchestrator, Depends(get_agent_orchestrator)]

# 共享服务类型别名
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
ImageServiceDep = Annotated[ImageService, Depends(get_image_service)]
TTSServiceDep = Annotated[TTSService, Depends(get_tts_service)]
ToolServiceDep = Annotated[ToolService, Depends(get_tool_service)]
