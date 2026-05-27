"""AI Chat 命令行入口。"""


import typer

from src.ai.security.crypto import generate_key

app = typer.Typer(help="AI Chat local workbench")


@app.command("generate-key")
def generate_encryption_key() -> None:
    """生成用于 API Key 加密保存的 ENCRYPTION_KEY。"""
    typer.echo(generate_key())


if __name__ == "__main__":
    app()
