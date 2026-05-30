"""Jupyter Notebook 编辑工具。"""

import asyncio
import json
from pathlib import Path

from langchain_core.tools import tool

from src.ai.core.tools.register import register_tool


@tool
async def notebook_edit(
    path: str,
    cell_index: int,
    source: str = "",
    cell_type: str = "code",
    edit_mode: str = "replace",
) -> str:
    """编辑 Jupyter 笔记本单元格。

    Args:
        path: .ipynb 文件路径。
        cell_index: 目标单元格索引（从 0 开始）。
        source: 新的单元格源代码。
        cell_type: 单元格类型（code / markdown），insert 模式下使用。
        edit_mode: 编辑模式 — replace（替换）、insert（插入）、delete（删除）。
    """
    file_path = Path(path)

    def _edit() -> str:
        raw = file_path.read_text(encoding="utf-8")
        nb = json.loads(raw)

        if "cells" not in nb:
            return f"错误: {file_path} 不是有效的 notebook 文件（缺少 cells 字段）"

        cells = nb["cells"]

        if edit_mode == "delete":
            if cell_index < 0 or cell_index >= len(cells):
                return f"错误: 索引 {cell_index} 超出范围（共 {len(cells)} 个单元格）"
            cells.pop(cell_index)
            msg = f"已删除单元格 {cell_index}"

        elif edit_mode == "insert":
            new_cell = {
                "cell_type": cell_type,
                "metadata": {},
                "source": source.splitlines(keepends=True),
            }
            if cell_type == "code":
                new_cell["execution_count"] = None
                new_cell["outputs"] = []
            cells.insert(cell_index, new_cell)
            msg = f"已在索引 {cell_index} 插入 {cell_type} 单元格"

        else:  # replace
            if cell_index < 0 or cell_index >= len(cells):
                return f"错误: 索引 {cell_index} 超出范围（共 {len(cells)} 个单元格）"
            cells[cell_index]["source"] = source.splitlines(keepends=True)
            if cell_type:
                cells[cell_index]["cell_type"] = cell_type
            msg = f"已替换单元格 {cell_index}"

        file_path.write_text(
            json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        return f"{msg}（共 {len(cells)} 个单元格）"

    return await asyncio.to_thread(_edit)


# ── 自注册 ──────────────────────────────────────────────────────────────────

register_tool(
    notebook_edit, source_type="builtin", permissions=["file_read", "file_write"]
)
