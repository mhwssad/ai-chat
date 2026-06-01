"""图像 API Schema 定义。"""

from datetime import datetime

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    """图像生成请求。"""

    prompt: str = Field(description="图像描述提示词", min_length=1, max_length=4000)
    size: str = Field(
        default="1024x1024", description="图像尺寸，如 1024x1024、1792x1024、1024x1792"
    )
    quality: str = Field(default="standard", description="图像质量: standard 或 hd")
    style: str = Field(default="vivid", description="图像风格: vivid 或 natural")
    n: int = Field(default=1, description="生成图像数量", ge=1, le=10)


class ImageGenerateResponse(BaseModel):
    """图像生成响应。"""

    files: list[str] = Field(description="保存的文件路径列表")
    images: list[str] = Field(description="Base64 编码的图像数据列表")
    revised_prompts: list[str | None] = Field(description="模型修订后的提示词列表")


class ImageMetaResponse(BaseModel):
    """图像元数据响应。"""

    filename: str = Field(description="文件名")
    size_bytes: int = Field(description="文件大小（字节）")
    format: str = Field(description="图像格式")
    created_at: datetime = Field(description="创建时间")
