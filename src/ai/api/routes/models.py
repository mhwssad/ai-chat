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
            model_name=getattr(chat_config, "model_name", ""),
            temperature=getattr(chat_config, "temperature", None),  # type: ignore[arg-type]
            max_tokens=getattr(chat_config, "max_tokens", None),  # type: ignore[arg-type]
            timeout=getattr(chat_config, "timeout", None),  # type: ignore[arg-type]
        ),
        embedding=EmbeddingModelConfigResponse(
            backend=embedding_config.backend,
            model_name=getattr(embedding_config, "model_name", ""),
            dimensions=getattr(embedding_config, "dimensions", None),
        ),
    )
