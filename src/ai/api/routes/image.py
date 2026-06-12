"""图像生成路由 — 生成、列表、删除。"""


from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.image import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageInfoResponse,
)
from src.ai.core.container import AppContainer
from src.ai.service.image_service import ImageService

router = APIRouter()


@router.post("/generate", response_model=ImageGenerateResponse, summary="生成图像")
@inject
async def generate_image(
    req: ImageGenerateRequest,
    svc: Annotated[
        ImageService, Depends(Provide[AppContainer.service_container.image_service])
    ],
) -> ImageGenerateResponse:
    """调用模型生成图像。"""
    result = await svc.generate(
        prompt=req.prompt,
        size=req.size,
        quality=req.quality,
        style=req.style,
        n=req.n,
    )
    return ImageGenerateResponse(**result)


@router.get("", response_model=list[ImageInfoResponse], summary="列出图像")
@inject
async def list_images(
    svc: Annotated[
        ImageService, Depends(Provide[AppContainer.service_container.image_service])
    ],
) -> list[ImageInfoResponse]:
    """列出已生成的图像。"""
    images = await svc.alist_images()
    return [
        ImageInfoResponse(
            filename=img["filename"],
            path=img["path"],
            size_bytes=img["size_bytes"],
            format=img["format"],
            created_at=str(img["created_at"]),
        )
        for img in images
    ]


@router.delete("/{filename}", response_model=MessageResponse, summary="删除图像")
@inject
async def delete_image(
    filename: str,
    svc: Annotated[
        ImageService, Depends(Provide[AppContainer.service_container.image_service])
    ],
) -> MessageResponse:
    """删除指定图像。"""
    try:
        msg = await svc.adelete_image(filename)
        return MessageResponse(message=msg)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"图像不存在: {filename}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
