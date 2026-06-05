"""Rich 主题常量 — 统一 CLI 视觉风格，支持多主题切换。"""

from rich.theme import Theme


# ── 主题定义 ─────────────────────────────────────────────────

DARK_THEME = Theme(
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

LIGHT_THEME = Theme(
    {
        "title": "bold blue",
        "subtitle": "bold black",
        "header": "bold white on blue",
        "active": "bold green",
        "inactive": "dim black",
        "warning": "bold dark_orange",
        "error": "bold red",
        "success": "bold green",
        "info": "dark_cyan",
        "muted": "dim black",
        "highlight": "bold magenta",
        "border": "blue",
        "selected": "reverse",
        "key": "bold dark_orange",
        "value": "black",
    }
)

HIGH_CONTRAST_THEME = Theme(
    {
        "title": "bold bright_cyan",
        "subtitle": "bold bright_white",
        "header": "bold bright_white on black",
        "active": "bold bright_green",
        "inactive": "dim bright_white",
        "warning": "bold bright_yellow",
        "error": "bold bright_red",
        "success": "bold bright_green",
        "info": "bright_cyan",
        "muted": "dim bright_white",
        "highlight": "bold bright_magenta",
        "border": "bright_blue",
        "selected": "reverse",
        "key": "bold bright_yellow",
        "value": "bright_white",
    }
)

# ── 主题注册表 ───────────────────────────────────────────────

THEMES: dict[str, Theme] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "high_contrast": HIGH_CONTRAST_THEME,
}

# 当前主题名称
_current_theme_name: str = "dark"

# 默认主题（向后兼容）
THEME = DARK_THEME


def get_theme(name: str | None = None) -> Theme:
    """获取主题。

    Args:
        name: 主题名称（None 返回当前主题）。

    Returns:
        Rich Theme 对象。
    """
    if name is None:
        return THEMES.get(_current_theme_name, DARK_THEME)
    return THEMES.get(name, DARK_THEME)


def set_theme(name: str) -> Theme:
    """切换主题。

    Args:
        name: 主题名称。

    Returns:
        切换后的 Theme 对象。
    """
    global _current_theme_name, THEME
    _current_theme_name = name
    THEME = THEMES.get(name, DARK_THEME)
    return THEME


def get_theme_names() -> list[str]:
    """获取所有可用主题名称。"""
    return list(THEMES.keys())


def next_theme() -> str:
    """切换到下一个主题（循环）。

    Returns:
        新主题名称。
    """
    names = get_theme_names()
    try:
        idx = names.index(_current_theme_name)
    except ValueError:
        idx = 0
    new_name = names[(idx + 1) % len(names)]
    set_theme(new_name)
    return new_name


# ── 图标常量（ASCII 兼容） ──────────────────────────────────


class Icons:
    """终端图标集 — 全部使用 ASCII 字符，兼容 GBK 等非 UTF-8 终端。"""

    # 状态
    ACTIVE: str = "*"
    INACTIVE: str = "o"
    RUNNING: str = ">"
    PAUSED: str = "||"
    SUCCESS: str = "OK"
    FAILED: str = "X"
    WARNING: str = "!"
    INFO: str = "i"

    # 导航
    ARROW_RIGHT: str = ">"
    ARROW_DOWN: str = "v"
    ARROW_LEFT: str = "<"
    POINTER: str = ">"
    BULLET: str = "-"

    # 操作
    ADD: str = "+"
    DELETE: str = "x"
    EDIT: str = "~"
    SEARCH: str = "?"
    REFRESH: str = "R"

    # 分隔
    LINE: str = "-"
    DOUBLE_LINE: str = "="
    CORNER_TL: str = "+"
    CORNER_TR: str = "+"
    CORNER_BL: str = "+"
    CORNER_BR: str = "+"

    # 面板标签
    TAB_CHAT: str = "[C]"
    TAB_TOOLS: str = "[T]"
    TAB_MEMORY: str = "[M]"
    TAB_SCHEDULER: str = "[S]"
    TAB_STATS: str = "[#]"
    TAB_IMAGE: str = "[I]"
    TAB_TTS: str = "[A]"
    TAB_AGENT: str = "[G]"
    TAB_RAG: str = "[R]"
    TAB_SYSTEM: str = "[Y]"
