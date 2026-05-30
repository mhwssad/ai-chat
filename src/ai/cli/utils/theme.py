"""Rich 主题常量 — 统一 CLI 视觉风格。"""

from rich.theme import Theme


# ── 主题 ─────────────────────────────────────────────────────

THEME = Theme(
    {
        "title": "bold cyan",
        "subtitle": "bold white",
        "header": "bold blue on grey11",
        "active": "bold green",
        "inactive": "dim white",
        "warning": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "info": "cyan",
        "muted": "dim white",
        "highlight": "bold magenta",
        "border": "blue",
        "selected": "reverse",
        "key": "bold yellow",
        "value": "white",
    }
)


# ── 图标常量 ─────────────────────────────────────────────────


class Icons:
    """终端图标集（兼容 Unicode 和 ASCII）。"""

    # 状态
    ACTIVE: str = "●"
    INACTIVE: str = "○"
    RUNNING: str = "◉"
    PAUSED: str = "◈"
    SUCCESS: str = "✓"
    FAILED: str = "✗"
    WARNING: str = "⚠"
    INFO: str = "ℹ"

    # 导航
    ARROW_RIGHT: str = "▸"
    ARROW_DOWN: str = "▾"
    ARROW_LEFT: str = "◂"
    POINTER: str = "❯"
    BULLET: str = "•"

    # 操作
    ADD: str = "+"
    DELETE: str = "×"
    EDIT: str = "✎"
    SEARCH: str = "⌕"
    REFRESH: str = "↻"

    # 分隔
    LINE: str = "─"
    DOUBLE_LINE: str = "═"
    CORNER_TL: str = "┌"
    CORNER_TR: str = "┐"
    CORNER_BL: str = "└"
    CORNER_BR: str = "┘"

    # 面板标签
    TAB_CHAT: str = "💬"
    TAB_TOOLS: str = "🔧"
    TAB_MEMORY: str = "🧠"
    TAB_SCHEDULER: str = "⏰"
