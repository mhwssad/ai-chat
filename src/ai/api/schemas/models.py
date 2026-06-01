"""模型配置 Schema。"""

from pydantic import BaseModel, Field


class ChatModelConfigResponse(BaseModel):
    """Chat 模型配置响应。"""

    backend: str = Field(description="模型后端")
    model_name: str = Field(description="模型名称")
    temperature: float = Field(description="温度参数")
    max_tokens: int = Field(description="最大输出 token 数")
    timeout: int = Field(description="超时时间（秒）")


class EmbeddingModelConfigResponse(BaseModel):
    """Embedding 模型配置响应。"""

    backend: str = Field(description="模型后端")
    model_name: str = Field(description="模型名称")
    dimensions: int | None = Field(default=None, description="向量维度")


class ModelConfigResponse(BaseModel):
    """模型配置响应。"""

    chat: ChatModelConfigResponse = Field(description="Chat 模型配置")
    embedding: EmbeddingModelConfigResponse = Field(description="Embedding 模型配置")
