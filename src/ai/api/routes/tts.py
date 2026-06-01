"""TTS API 路由。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from src.ai.api.deps import ModelServiceDep
from src.ai.api.schemas.tts import (
    AudioMetaResponse,
    TTSSynthesizeRequest,
    TTSSynthesizeResponse,
)
from src.ai.api.services.tts_service import TTSService

router = APIRouter(prefix="/tts", tags=["tts"])


def _get_tts_service(model_service: ModelServiceDep) -> TTSService:
    """创建 TTSService 实例。"""
    return TTSService(model_service=model_service)


@router.post("/synthesize", response_model=TTSSynthesizeResponse)
async def synthesize_speech(
    request: TTSSynthesizeRequest,
    model_service: ModelServiceDep,
):
    """合成语音。

    调用配置的 TTS 模型（OpenAI TTS、Edge TTS 等）合成语音并保存到本地。
    """
    service = _get_tts_service(model_service)
    result = await service.synthesize(
        text=request.text,
        voice=request.voice,
        speed=request.speed,
        output_format=request.output_format,
    )
    return TTSSynthesizeResponse(**result)


@router.get("/list", response_model=list[AudioMetaResponse])
async def list_audio(
    model_service: ModelServiceDep,
):
    """列出已合成的音频。"""
    service = _get_tts_service(model_service)
    audio_list = service.list_audio()
    return [AudioMetaResponse(**audio) for audio in audio_list]


@router.get("/{filename}")
async def get_audio(
    filename: str,
    model_service: ModelServiceDep,
):
    """返回音频文件流。"""
    service = _get_tts_service(model_service)
    filepath, mime_type = service.get_audio_path(filename)
    return FileResponse(
        path=str(filepath),
        media_type=mime_type,
        filename=filename,
    )


@router.delete("/{filename}")
async def delete_audio(
    filename: str,
    model_service: ModelServiceDep,
):
    """删除指定音频。"""
    service = _get_tts_service(model_service)
    message = service.delete_audio(filename)
    return {"message": message}
