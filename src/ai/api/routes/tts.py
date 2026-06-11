"""TTS 路由 — 语音合成、列表、删除。"""

from __future__ import annotations

from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException

from src.ai.api.schemas.common import MessageResponse
from src.ai.api.schemas.tts import (
    AudioInfoResponse,
    TtsSynthesizeRequest,
    TtsSynthesizeResponse,
)
from src.ai.core.container import AppContainer
from src.ai.service.tts_service import TTSService

router = APIRouter()


@router.post("/synthesize", response_model=TtsSynthesizeResponse, summary="合成语音")
@inject
async def synthesize(
    req: TtsSynthesizeRequest,
    svc: Annotated[
        TTSService, Depends(Provide[AppContainer.service_container.tts_service])
    ],
) -> TtsSynthesizeResponse:
    """调用模型合成语音。"""
    result = await svc.synthesize(
        text=req.text,
        voice=req.voice,
        speed=req.speed,
        output_format=req.output_format,
    )
    return TtsSynthesizeResponse(**result)


@router.get("", response_model=list[AudioInfoResponse], summary="列出音频")
@inject
async def list_audio(
    svc: Annotated[
        TTSService, Depends(Provide[AppContainer.service_container.tts_service])
    ],
) -> list[AudioInfoResponse]:
    """列出已合成的音频。"""
    audios = await svc.alist_audio()
    return [
        AudioInfoResponse(
            filename=a["filename"],
            path=a["path"],
            size_bytes=a["size_bytes"],
            format=a["format"],
            created_at=str(a["created_at"]),
        )
        for a in audios
    ]


@router.delete("/{filename}", response_model=MessageResponse, summary="删除音频")
@inject
async def delete_audio(
    filename: str,
    svc: Annotated[
        TTSService, Depends(Provide[AppContainer.service_container.tts_service])
    ],
) -> MessageResponse:
    """删除指定音频。"""
    try:
        msg = await svc.adelete_audio(filename)
        return MessageResponse(message=msg)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"音频不存在: {filename}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
