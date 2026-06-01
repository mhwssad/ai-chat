"""终端图像渲染器 — 自适应 Sixel / ASCII 渲染。"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from rich.text import Text

logger = logging.getLogger(__name__)

# ASCII 亮度映射字符（从暗到亮）
_ASCII_CHARS = " .:-=+*#%@"


class ImageRenderer:
    """终端图像渲染器。

    优先使用 Sixel 协议渲染，不支持时降级为 ASCII 字符画。
    """

    @staticmethod
    def detect_sixel() -> bool:
        """检测终端是否支持 Sixel 协议。

        通过环境变量推断：
        - TERM_PROGRAM: WezTerm / iTerm2 / mlterm
        - TERM: 含 "sixel" 或 "mlterm"

        Returns:
            True 表示终端可能支持 Sixel。
        """
        term_program = os.environ.get("TERM_PROGRAM", "").lower()
        term = os.environ.get("TERM", "").lower()

        # 已知支持 Sixel 的终端
        sixel_terminals = {"wezterm", "iterm2", "mlterm"}
        if term_program in sixel_terminals:
            return True

        if "sixel" in term or "mlterm" in term:
            return True

        return False

    def render(
        self,
        image_path: str | Path,
        width: int = 40,
        height: int = 20,
    ) -> Text:
        """自适应渲染图像到 Rich Text。

        Args:
            image_path: 图像文件路径。
            width: 渲染宽度（字符列数）。
            height: 渲染高度（字符行数）。

        Returns:
            Rich Text 对象，包含渲染后的图像文本。
        """
        path = Path(image_path)
        if not path.exists():
            return Text(f"  图像不存在: {path.name}", style="error")

        try:
            from PIL import Image

            img = Image.open(path)
        except Exception as e:
            logger.debug("打开图像失败: %s", e)
            return Text(f"  无法打开图像: {path.name}", style="error")

        if self.detect_sixel():
            return self._render_sixel(img, width, height)
        return self._render_ascii(img, width, height)

    @staticmethod
    def _render_sixel(
        img: object,
        width: int,
        height: int,
    ) -> Text:
        """Sixel 编码渲染。

        Args:
            img: PIL Image 对象。
            width: 渲染宽度。
            height: 渲染高度。

        Returns:
            Rich Text 对象。
        """
        try:
            from PIL import Image as PILImage

            pil_img: PILImage.Image = img  # type: ignore[assignment]
            # 缩放到目标尺寸（Sixel 每字符约 6x10 像素）
            pixel_w = width * 6
            pixel_h = height * 10
            pil_img = pil_img.convert("RGB")
            pil_img = pil_img.resize((pixel_w, pixel_h), PILImage.Resampling.LANCZOS)

            # 简化 Sixel 编码：将图像转为 256 色 Sixel
            sixel_data = _encode_sixel(pil_img)
            text = Text(sixel_data)
            return text
        except Exception as e:
            logger.debug("Sixel 渲染失败，降级为 ASCII: %s", e)
            return ImageRenderer._render_ascii(img, width, height)

    @staticmethod
    def _render_ascii(
        img: object,
        width: int,
        height: int,
    ) -> Text:
        """ASCII 字符画渲染。

        Args:
            img: PIL Image 对象。
            width: 渲染宽度。
            height: 渲染高度。

        Returns:
            Rich Text 对象。
        """
        from PIL import Image as PILImage

        pil_img: PILImage.Image = img  # type: ignore[assignment]
        pil_img = pil_img.convert("L")  # 灰度
        pil_img = pil_img.resize((width, height), PILImage.Resampling.LANCZOS)

        text = Text()
        pixels = list(pil_img.getdata())
        chars = len(_ASCII_CHARS)

        for row in range(height):
            for col in range(width):
                idx = row * width + col
                if idx < len(pixels):
                    brightness = pixels[idx]
                    char_idx = min(brightness * chars // 256, chars - 1)
                    text.append(_ASCII_CHARS[char_idx])
            text.append("\n")

        return text


def _encode_sixel(img: object) -> str:
    """将 PIL Image 编码为 Sixel 字符串。

    简化实现：使用 256 色映射。

    Args:
        img: PIL RGB Image 对象。

    Returns:
        Sixel 编码字符串。
    """
    from PIL import Image as PILImage

    pil_img: PILImage.Image = img  # type: ignore[assignment]
    width, height = pil_img.size
    pixels = list(pil_img.getdata())

    # Sixel 头
    lines: list[str] = []
    lines.append("\033Pq")

    # 简化：将颜色量化为 16 色
    sixel_chars = "?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefgh"

    for row_start in range(0, height, 6):
        lines.append("#1;2;100;100;100")  # 白色
        for col in range(width):
            sixlet = 0
            for bit in range(6):
                y = row_start + bit
                if y < height:
                    idx = y * width + col
                    if idx < len(pixels):
                        r, g, b = pixels[idx][0], pixels[idx][1], pixels[idx][2]
                        # 简单亮度判断
                        brightness = (r + g + b) / 3
                        if brightness > 128:
                            sixlet |= 1 << bit
            char_idx = min(sixlet + 63, ord(sixel_chars[-1]))
            lines.append(chr(char_idx))
        lines.append("$\n")  # 行结束

    lines.append("\033\\")
    return "".join(lines)
