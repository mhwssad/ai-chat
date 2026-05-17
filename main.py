"""AI Chat 统一 CLI 入口 — 各模块管理入口的编排层。"""

import warnings

warnings.filterwarnings("ignore", category=PendingDeprecationWarning, module="langgraph")

from src.ai_chat.graphs import menu_chat
from src.ai_chat.chains import menu_chains
from src.ai_chat.workflows import menu_workflows
from src.ai_chat.tools import menu_tools
from src.ai_chat.memory import menu_memory
from src.ai_chat.mcp import menu_mcp
from src.ai_chat.skills import menu_skills
from src.ai_chat.llm import menu_llm
from src.ai_chat.prompts import menu_prompts
from src.ai_chat.utils.error_handler import cli_run


def _choose(prompt: str, options: list[str]) -> int:
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


@cli_run
def main():
    while True:
        print("\n=== AI Chat ===")
        idx = _choose("请选择: ", [
            "对话",
            "调用链",
            "工作流",
            "LLM 管理",
            "提示词管理",
            "工具管理",
            "记忆管理",
            "MCP 管理",
            "技能管理",
            "退出",
        ])

        if idx == 1:
            menu_chat()
        elif idx == 2:
            menu_chains()
        elif idx == 3:
            menu_workflows()
        elif idx == 4:
            menu_llm()
        elif idx == 5:
            menu_prompts()
        elif idx == 6:
            menu_tools()
        elif idx == 7:
            menu_memory()
        elif idx == 8:
            menu_mcp()
        elif idx == 9:
            menu_skills()
        else:
            print("再见！")
            break


if __name__ == "__main__":
    main()
