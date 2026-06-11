"""图像相关请求/响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    """图像生成请求。"""

    prompt: str = Field(..., min_length=1, description="图像描述")
    size: str | None = Field(default=None, description="图像尺寸")
    quality: str | None = Field(default=None, description="图像质量")
    style: str | None = Field(default=None, description="图像风格")
    n: int = Field(default=1, ge=1, le=4, description="生成数量")


class ImageGenerateResponse(BaseModel):
    """图像生成响应。"""

    files: list[str] = Field(default_factory=list, description="保存的文件路径")
    images: list[str] = Field(default_factory=list, description="Base64 编码图像")
    revised_prompts: list[str | None] = Field(
        default_factory=list, description="修订后的提示词"
    )


class ImageInfoResponse(BaseModel):
    """图像信息。"""

    filename: str = Field(description="文件名")
    path: str = Field(description="文件路径")
    size_bytes: int = Field(description="文件大小（字节）")
    format: str = Field(description="图像格式")
    created_at: str = Field(description="创建时间")
