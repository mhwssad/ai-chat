"""Markdown 渲染器 — 使用 Rich 内置 Markdown 支持。"""

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text


def render_markdown(content: str, width: int = 80) -> Text:
    """将 Markdown 文本渲染为 Rich 可渲染对象。

    使用 rich.markdown.Markdown 进行渲染，无需额外依赖。

    Args:
        content: Markdown 格式的文本。
        width: 渲染宽度。

    Returns:
        Rich Text 对象（可直接嵌入 Panel）。
    """
    if not content:
        return Text()

    try:
        md = Markdown(content, code_theme="monokai")
        # 通过临时 Console 渲染为 Text
        console = Console(width=width, force_terminal=False, record=True)
        console.print(md)
        rendered = console.export_text(styles=True)
        return Text.from_ansi(rendered)
    except Exception:
        # 渲染失败时回退到纯文本
        return Text(content)
