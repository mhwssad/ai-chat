"""AI Chat CLI 控制台包。

提供 TUI 仪表盘（Rich Live）和管理子命令（Typer）。
"""

from src.ai.security.crypto import generate_key

import typer

# ── generate-key 命令（从旧 cli.py 迁移） ────────────────────

app = typer.Typer(help="AI Chat CLI 控制台")


@app.command("generate-key")
def generate_encryption_key() -> None:
    """生成用于 API Key 加密保存的 ENCRYPTION_KEY。"""
    typer.echo(generate_key())


__all__ = ["app", "generate_encryption_key"]
