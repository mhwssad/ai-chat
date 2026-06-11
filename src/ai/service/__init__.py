"""共享服务层 — CLI 和 API 统一使用的服务模块。

包含：
- ChatService: 统一对话编排（流式/非流式 + 工具循环 + 记忆提取）
- ImageService: 图像生成与管理
- TTSService: 语音合成与管理
- ToolService: 工具查询、启禁、测试执行
"""

from src.ai.service.types import ChatOptions, ChatResult

_LAZY_EXPORTS = {
    "ChatService": "src.ai.service.chat_service",
    "ImageService": "src.ai.service.image_service",
    "SystemService": "src.ai.service.system_service",
    "ToolService": "src.ai.service.tool_service",
    "TTSService": "src.ai.service.tts_service",
    "RagApiService": "src.ai.service.rag_service",
    "AgentApiService": "src.ai.service.agent_service",
    "PromptApiService": "src.ai.service.prompt_service",
    "MemoryApiService": "src.ai.service.memory_service",
    "ModelConfigService": "src.ai.service.model_config_service",
    "SessionService": "src.ai.service.session_service",
    "SchedulerApiService": "src.ai.service.scheduler_service",
    "SkillApiService": "src.ai.service.skill_service",
}

__all__ = [
    "ChatOptions",
    "ChatResult",
    "ChatService",
    "ImageService",
    "SystemService",
    "ToolService",
    "TTSService",
    "RagApiService",
    "AgentApiService",
    "PromptApiService",
    "MemoryApiService",
    "ModelConfigService",
    "SessionService",
    "SchedulerApiService",
    "SkillApiService",
]


def __getattr__(name: str):
    """按需导入服务类，避免包初始化时触发循环依赖。"""
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    from importlib import import_module

    module = import_module(_LAZY_EXPORTS[name])
    value = getattr(module, name)
    globals()[name] = value
    return value
