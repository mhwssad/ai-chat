"""格式化工具函数 — 统一 CLI 输出格式。"""

import unicodedata
from datetime import datetime


def format_timestamp(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """格式化时间戳。

    Args:
        dt: 待格式化的时间对象，None 返回占位符。
        fmt: strftime 格式字符串。

    Returns:
        格式化后的时间字符串。
    """
    if dt is None:
        return "-"
    # 统一转为本地时间显示
    if dt.tzinfo is not None:
        dt = dt.astimezone()
    return dt.strftime(fmt)


def format_duration(seconds: float | None) -> str:
    """格式化时长（秒 → 人类可读）。

    Args:
        seconds: 秒数，None 返回占位符。

    Returns:
        如 "1h 23m"、"45s"、"2d 3h"。
    """
    if seconds is None:
        return "-"
    if seconds < 0:
        return "-"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    if seconds < 86400:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    return f"{d}d {h}h"


def display_width(text: str) -> int:
    """计算文本的显示宽度（CJK 字符占 2 列，零宽字符不计）。

    Args:
        text: 原始文本。

    Returns:
        显示宽度。
    """
    width = 0
    for ch in text:
        cat = unicodedata.category(ch)
        # Mn=非间距标记, Cf=格式字符（含零宽空格等）→ 不占宽度
        if cat in ("Mn", "Cf"):
            continue
        eaw = unicodedata.east_asian_width(ch)
        width += 2 if eaw in ("W", "F") else 1
    return width


def truncate(text: str, max_len: int = 60, suffix: str = "...") -> str:
    """截断长文本（CJK 感知）。

    Args:
        text: 原始文本。
        max_len: 最大显示宽度（含 suffix）。
        suffix: 截断后缀。

    Returns:
        截断后的字符串。
    """
    if display_width(text) <= max_len:
        return text

    suffix_width = display_width(suffix)
    target = max_len - suffix_width
    result: list[str] = []
    current_width = 0
    for ch in text:
        eaw = unicodedata.east_asian_width(ch)
        w = 2 if eaw in ("W", "F") else 1
        if current_width + w > target:
            break
        result.append(ch)
        current_width += w
    return "".join(result) + suffix


def wrap_text(text: str, width: int) -> list[str]:
    """按显示宽度换行（CJK 感知）。

    Args:
        text: 原始文本。
        width: 每行最大显示宽度。

    Returns:
        换行后的字符串列表。
    """
    lines: list[str] = []
    current: list[str] = []
    current_width = 0

    for ch in text:
        if ch == "\n":
            lines.append("".join(current))
            current = []
            current_width = 0
            continue

        eaw = unicodedata.east_asian_width(ch)
        w = 2 if eaw in ("W", "F") else 1

        if current_width + w > width:
            lines.append("".join(current))
            current = [ch]
            current_width = w
        else:
            current.append(ch)
            current_width += w

    if current:
        lines.append("".join(current))

    return lines


def format_status(status: str) -> str:
    """格式化状态标签（带 Rich 标记）。

    Args:
        status: 状态字符串（active/paused/completed/failed/disabled 等）。

    Returns:
        Rich 可渲染的状态标签。
    """
    mapping = {
        "active": "[active]* 活跃[/]",
        "paused": "[warning][H] 暂停[/]",
        "completed": "[success][OK] 完成[/]",
        "failed": "[error][X] 失败[/]",
        "disabled": "[inactive]o 禁用[/]",
        "running": "[active][R] 运行中[/]",
        "success": "[success][OK] 成功[/]",
        "timeout": "[warning][T] 超时[/]",
        "cancelled": "[inactive]o 取消[/]",
    }
    return mapping.get(status, f"[muted]{status}[/]")


def format_count(count: int, label: str = "条") -> str:
    """格式化数量标签。

    Args:
        count: 数量。
        label: 单位标签。

    Returns:
        如 "5 条"、"0 条"。
    """
    return f"{count} {label}"


def format_table_row(
    columns: list[str], widths: list[int], separator: str = " | "
) -> str:
    """格式化固定宽度表格行。

    Args:
        columns: 列内容列表。
        widths: 各列宽度。
        separator: 列分隔符。

    Returns:
        格式化后的行字符串。
    """
    parts: list[str] = []
    for i, col in enumerate(columns):
        w = widths[i] if i < len(widths) else 20
        # 截断超宽内容
        if display_width(col) > w:
            col = truncate(col, max_len=w)
        parts.append(col.ljust(w))
    return separator.join(parts)
