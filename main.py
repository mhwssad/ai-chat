"""AI Chat 统一入口。"""

from __future__ import annotations

import sys
from pathlib import Path

_src = str(Path(__file__).resolve().parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import typer  # noqa: E402

app = typer.Typer(help="AI Chat — 本地 AI 工作台", no_args_is_help=True)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="监听地址"),
    port: int = typer.Option(8000, "--port", help="监听端口"),
    reload: bool = typer.Option(False, "--reload", help="启用热重载"),
) -> None:
    """启动 FastAPI 服务。"""
    import uvicorn

    uvicorn.run("src.ai.api:app", host=host, port=port, reload=reload)


@app.command(name="tui")
def tui() -> None:
    """启动统一 TUI 工作台。"""
    from src.ai.core.container import container
    from src.ai.core.container_wiring import initialize_container

    initialize_container()
    container.cli_container.dashboard().run()


if __name__ == "__main__":
    app()
