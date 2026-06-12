"""图像生成模型构建器 + 工厂。

内置三种构建策略：OpenAI DALL-E 3 / Stability AI / 本地 ComfyUI & Automatic1111。

扩展方式：实现 ``ImageModelBuilder`` 并注册到 ``image_model_factory``。
"""

from __future__ import annotations

import base64
from src.ai.config.logging_setup import get_logger
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from src.ai.core.models.base import ImageModelBuilder, ModelFactory
from src.ai.core.models.types import ImageData
from src.ai.exception.media_exception import ImageGenerationException

if TYPE_CHECKING:
    from src.ai.config.model_settings import ImageModelConfig

logger = get_logger(__name__)


# ── 图像生成器抽象 ──────────────────────────────────────


class ImageGenerator(ABC):
    """图像生成器抽象接口。"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        size: str | None = None,
        quality: str | None = None,
        style: str | None = None,
        n: int = 1,
        **kwargs: Any,
    ) -> list[ImageData]:
        """根据提示词生成图像。

        Args:
            prompt: 图像描述提示词。
            size: 图像尺寸（如 "1024x1024"）。
            quality: 图像质量（如 "standard", "hd"）。
            style: 图像风格（如 "vivid", "natural"）。
            n: 生成图像数量。
            **kwargs: 后端特定参数。

        Returns:
            图像数据列表。
        """


# ── 私有实现 ────────────────────────────────────────────


class _OpenAIImageGenerator(ImageGenerator):
    """OpenAI DALL-E 3 图像生成器。"""

    def __init__(self, client: Any, model_key: str) -> None:
        self._client = client
        self._model_key = model_key

    async def generate(
        self,
        prompt: str,
        *,
        size: str | None = None,
        quality: str | None = None,
        style: str | None = None,
        n: int = 1,
        **kwargs: Any,
    ) -> list[ImageData]:
        try:
            params: dict[str, Any] = {
                "model": self._model_key,
                "prompt": prompt,
                "n": n,
                "response_format": "b64_json",
            }
            if size:
                params["size"] = size
            if quality:
                params["quality"] = quality
            if style:
                params["style"] = style
            params.update(kwargs)

            response = await self._client.images.generate(**params)

            results: list[ImageData] = []
            for item in response.data:
                image_bytes = base64.b64decode(item.b64_json)
                results.append(
                    ImageData(
                        image_bytes=image_bytes,
                        format="png",
                        revised_prompt=getattr(item, "revised_prompt", None),
                        metadata={"model": self._model_key},
                    )
                )
            return results
        except Exception as exc:
            raise ImageGenerationException(
                f"OpenAI 图像生成失败: {exc}",
                context={"prompt": prompt, "model": self._model_key},
            ) from exc


class _StabilityAIGenerator(ImageGenerator):
    """Stability AI 图像生成器。"""

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url or "https://api.stability.ai/v2beta"

    async def generate(
        self,
        prompt: str,
        *,
        size: str | None = None,
        quality: str | None = None,
        style: str | None = None,
        n: int = 1,
        **kwargs: Any,
    ) -> list[ImageData]:
        from src.ai.utils.http.client import http_aclient

        try:
            # 解析尺寸
            width, height = 1024, 1024
            if size:
                parts = size.split("x")
                if len(parts) == 2:
                    width, height = int(parts[0]), int(parts[1])

            response = await http_aclient.post(
                f"{self._base_url}/stable-image/generate/sd3",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "application/json",
                },
                data={
                    "prompt": prompt,
                    "output_format": "png",
                    "aspect_ratio": f"{width}:{height}",
                },
                timeout=120,
            )
            data = response.json()

            results: list[ImageData] = []
            image_b64 = data.get("image", "")
            if image_b64:
                results.append(
                    ImageData(
                        image_bytes=base64.b64decode(image_b64),
                        format="png",
                        metadata={"provider": "stability_ai"},
                    )
                )
            return results
        except ImageGenerationException:
            raise
        except Exception as exc:
            raise ImageGenerationException(
                f"Stability AI 图像生成失败: {exc}",
                context={"prompt": prompt},
            ) from exc


class _LocalImageGenerator(ImageGenerator):
    """本地图像生成器（ComfyUI / Automatic1111）。"""

    def __init__(self, base_url: str, backend: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._backend = backend

    async def generate(
        self,
        prompt: str,
        *,
        size: str | None = None,
        quality: str | None = None,
        style: str | None = None,
        n: int = 1,
        **kwargs: Any,
    ) -> list[ImageData]:
        from src.ai.utils.http.client import http_aclient

        try:
            width, height = 1024, 1024
            if size:
                parts = size.split("x")
                if len(parts) == 2:
                    width, height = int(parts[0]), int(parts[1])

            if self._backend == "comfyui":
                results = await self._comfyui_generate(
                    http_aclient, prompt, width, height, n
                )
            else:
                results = await self._automatic1111_generate(
                    http_aclient, prompt, width, height, n
                )
            return results
        except ImageGenerationException:
            raise
        except Exception as exc:
            raise ImageGenerationException(
                f"本地图像生成失败: {exc}",
                context={"prompt": prompt, "backend": self._backend},
            ) from exc

    async def _comfyui_generate(
        self,
        client: Any,
        prompt: str,
        width: int,
        height: int,
        n: int,
    ) -> list[ImageData]:
        """ComfyUI API 调用。"""
        workflow = self._build_comfyui_workflow(prompt, width, height)
        response = await client.post(
            f"{self._base_url}/prompt",
            json={"prompt": workflow},
            timeout=300,
        )
        data = response.json()
        prompt_id = data.get("prompt_id", "")

        # 轮询获取结果
        import asyncio

        for _ in range(120):  # 最多等 60 秒
            history_resp = await client.get(
                f"{self._base_url}/history/{prompt_id}",
                timeout=10,
            )
            if history_resp.status_code == 200:
                history = history_resp.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    results: list[ImageData] = []
                    for node_output in outputs.values():
                        images = node_output.get("images", [])
                        for img_info in images:
                            img_resp = await client.get(
                                f"{self._base_url}/view",
                                params={
                                    "filename": img_info["filename"],
                                    "subfolder": img_info.get("subfolder", ""),
                                    "type": img_info.get("type", "output"),
                                },
                                timeout=30,
                            )
                            results.append(
                                ImageData(
                                    image_bytes=img_resp.content,
                                    format="png",
                                    metadata={"provider": "comfyui"},
                                )
                            )
                    return results
            await asyncio.sleep(0.5)

        raise ImageGenerationException(
            "ComfyUI 图像生成超时",
            context={"prompt_id": prompt_id},
        )

    async def _automatic1111_generate(
        self,
        client: Any,
        prompt: str,
        width: int,
        height: int,
        n: int,
    ) -> list[ImageData]:
        """Automatic1111 API 调用。"""
        response = await client.post(
            f"{self._base_url}/sdapi/v1/txt2img",
            json={
                "prompt": prompt,
                "width": width,
                "height": height,
                "batch_size": n,
            },
            timeout=300,
        )
        data = response.json()

        results: list[ImageData] = []
        for img_b64 in data.get("images", []):
            results.append(
                ImageData(
                    image_bytes=base64.b64decode(img_b64),
                    format="png",
                    metadata={"provider": "automatic1111"},
                )
            )
        return results

    @staticmethod
    def _build_comfyui_workflow(prompt: str, width: int, height: int) -> dict[str, Any]:
        """构建 ComfyUI 最小工作流。"""
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 0,
                    "steps": 20,
                    "cfg": 7,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "model.safetensors"},
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]},
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": "low quality", "clip": ["4", 1]},
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]},
            },
        }


# ── 构建器 ──────────────────────────────────────────────


class OpenAIImageBuilder(ImageModelBuilder):
    """OpenAI DALL-E 3 图像生成构建策略。"""

    backend = ["openai"]

    def build(self, config: ImageModelConfig) -> _OpenAIImageGenerator:  # type: ignore[override]
        from openai import AsyncOpenAI

        client_kwargs: dict[str, Any] = {}
        if config.api_key:
            client_kwargs["api_key"] = config.api_key
        if config.base_url:
            client_kwargs["base_url"] = config.base_url

        client = AsyncOpenAI(**client_kwargs)
        return _OpenAIImageGenerator(client, config.model_key)


class StabilityAIImageBuilder(ImageModelBuilder):
    """Stability AI 图像生成构建策略。"""

    backend = ["stability_ai"]

    def build(self, config: ImageModelConfig) -> _StabilityAIGenerator:  # type: ignore[override]
        if not config.api_key:
            raise ImageGenerationException(
                "Stability AI 需要配置 API Key",
                context={"backend": "stability_ai"},
            )
        return _StabilityAIGenerator(
            api_key=config.api_key,
            base_url=config.base_url,
        )


class LocalImageBuilder(ImageModelBuilder):
    """本地图像生成构建策略（ComfyUI / Automatic1111）。"""

    backend = ["comfyui", "automatic1111"]

    def build(self, config: ImageModelConfig) -> _LocalImageGenerator:  # type: ignore[override]
        if not config.base_url:
            raise ImageGenerationException(
                "本地图像生成需要配置 base_url",
                context={"backend": config.backend},
            )
        return _LocalImageGenerator(
            base_url=config.base_url,
            backend=config.backend,
        )


# ── 图像工厂 ────────────────────────────────────────────


class ImageModelFactory(ModelFactory[ImageModelBuilder]):
    """图像生成模型工厂。"""

    def create_builder(self, backend: str) -> ImageModelBuilder:
        return self._resolve(backend, "Image")
