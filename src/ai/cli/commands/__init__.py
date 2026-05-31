"""管理子命令组 — Typer 子命令入口。"""

import typer

manage_app = typer.Typer(help="管理子命令（工具、记忆、定时任务、对话、RAG）")

# 延迟注册子命令，避免循环导入
from src.ai.cli.commands.chat_cmd import chat_app  # noqa: E402
from src.ai.cli.commands.tools_cmd import tools_app  # noqa: E402
from src.ai.cli.commands.memory_cmd import memory_app  # noqa: E402
from src.ai.cli.commands.scheduler_cmd import scheduler_app  # noqa: E402
from src.ai.cli.commands.rag_cmd import rag_app  # noqa: E402

manage_app.add_typer(chat_app, name="chat", help="对话管理")
manage_app.add_typer(tools_app, name="tools", help="工具管理")
manage_app.add_typer(memory_app, name="memory", help="记忆管理")
manage_app.add_typer(scheduler_app, name="scheduler", help="定时任务管理")
manage_app.add_typer(rag_app, name="rag", help="RAG 知识库管理")

__all__ = ["manage_app"]
