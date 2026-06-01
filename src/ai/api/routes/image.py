"""图像 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from src.ai.api.deps import ModelServiceDep
from src.ai.api.schemas.image import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageMetaResponse,
)
from src.ai.api.services.image_service import ImageService

router = APIRouter(prefix="/image", tags=["image"])


def _get_image_service(model_service: ModelServiceDep) -> ImageService:
    """创建 ImageService 实例。"""
    return ImageService(model_service=model_service)


@router.post("/generate", response_model=ImageGenerateResponse)
async def generate_image(
    request: ImageGenerateRequest,
    model_service: ModelServiceDep,
):
    """生成图像。

    调用配置的图像生成模型（DALL-E 3、Stability AI 等）生成图像并保存到本地。
    """
    service = _get_image_service(model_service)
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
    model_service: ModelServiceDep,
):
    """列出已生成的图像。"""
    service = _get_image_service(model_service)
    images = service.list_images()
    return [ImageMetaResponse(**img) for img in images]


@router.get("/{filename}")
async def get_image(
    filename: str,
    model_service: ModelServiceDep,
):
    """返回图像文件流。"""
    service = _get_image_service(model_service)
    filepath = service.get_image_path(filename)
    return FileResponse(
        path=str(filepath),
        media_type=f"image/{filepath.suffix.lstrip('.')}",
        filename=filename,
    )


@router.delete("/{filename}")
async def delete_image(
    filename: str,
    model_service: ModelServiceDep,
):
    """删除指定图像。"""
    service = _get_image_service(model_service)
    message = service.delete_image(filename)
    return {"message": message}
