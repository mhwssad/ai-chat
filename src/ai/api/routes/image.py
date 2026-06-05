"""图像 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from src.ai.api.deps import ImageServiceDep
from src.ai.api.schemas.image import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageMetaResponse,
)

router = APIRouter(prefix="/image", tags=["image"])


@router.post("/generate", response_model=ImageGenerateResponse)
async def generate_image(
    request: ImageGenerateRequest,
    service: ImageServiceDep,
):
    """生成图像。

    调用配置的图像生成模型（DALL-E 3、Stability AI 等）生成图像并保存到本地。
    """
    result = await service.generate(
        prompt=request.prompt,
        size=request.size,
        quality=request.quality,
        style=request.style,
        n=request.n,
    )
    return ImageGenerateResponse(**result)


@router.get("/list", response_model=list[ImageMetaResponse])
async def list_images(
    service: ImageServiceDep,
):
    """列出已生成的图像。"""
    images = await service.alist_images()
    return [ImageMetaResponse(**img) for img in images]


@router.get("/{filename}")
async def get_image(
    filename: str,
    service: ImageServiceDep,
):
    """返回图像文件流。"""
    filepath = service.get_image_path(filename)
    return FileResponse(
        path=str(filepath),
        media_type=f"image/{filepath.suffix.lstrip('.')}",
        filename=filename,
    )


@router.delete("/{filename}")
async def delete_image(
    filename: str,
    service: ImageServiceDep,
):
    """删除指定图像。"""
    message = await service.adelete_image(filename)
    return {"message": message}
