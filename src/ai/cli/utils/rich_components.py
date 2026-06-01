"""Rich 组件封装层 — 统一样式的 Table、分页列表等工厂函数。"""

from rich.table import Table
from rich.text import Text


def create_styled_table(
    title: str,
    columns: list[tuple[str, str, int]],
    *,
    show_lines: bool = False,
    padding: int = 0,
) -> Table:
    """创建统一样式的 Rich Table。

    Args:
        title: 表格标题。
        columns: 列定义列表，每项为 (header, style, min_width)。
        show_lines: 是否显示行间分隔线。
        padding: 单元格内边距。

    Returns:
        配置好的 Rich Table 对象。
    """
    table = Table(
        title=title,
        show_lines=show_lines,
        padding=(padding, padding),
        expand=True,
        title_style="subtitle",
        border_style="muted",
        header_style="bold cyan",
    )
    for header, style, min_width in columns:
        table.add_column(header, style=style, min_width=min_width, no_wrap=True)
    return table


def render_paginated_list(
    items: list[str],
    selected_index: int,
    visible_count: int,
    total_count: int,
) -> Text:
    """渲染带分页指示器的列表文本。

    Args:
        items: 当前可见项的渲染文本列表。
        selected_index: 当前选中索引。
        visible_count: 每页可见数量。
        total_count: 总项目数。

    Returns:
        包含分页指示器的 Rich Text。
    """
    text = Text()

    for item in items:
        text.append_text(Text.from_markup(item))

    # 分页指示器
    if total_count > visible_count:
        page = (selected_index // visible_count) + 1
        total_pages = max(1, (total_count + visible_count - 1) // visible_count)
        text.append("\n")
        text.append(
            f"  -- 第 {page}/{total_pages} 页 ({selected_index + 1}/{total_count}) --\n",
            style="muted",
        )

    return text
