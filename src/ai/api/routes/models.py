"""模型配置路由。"""

from fastapi import APIRouter

from src.ai.api.deps import ModelServiceDep
from src.ai.api.schemas.models import (
    ChatModelConfigResponse,
    EmbeddingModelConfigResponse,
    ModelConfigResponse,
)

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/config", response_model=ModelConfigResponse)
async def get_model_config(model_service: ModelServiceDep):
    """获取模型配置。

    返回当前配置的 Chat 和 Embedding 模型信息。
    """
    chat_config = model_service.chat_config
    embedding_config = model_service.embedding_config

    return ModelConfigResponse(
        chat=ChatModelConfigResponse(
            backend=chat_config.backend,
            model_name=chat_config.model_name,
            temperature=chat_config.temperature,
            max_tokens=chat_config.max_tokens,
            timeout=chat_config.timeout,
        ),
        embedding=EmbeddingModelConfigResponse(
            backend=embedding_config.backend,
            model_name=embedding_config.model_name,
            dimensions=embedding_config.dimensions,
        ),
    )
