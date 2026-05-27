"""循环对话示例 — 集成记忆系统 + 工具调用的交互式聊天。

演示功能：
1. 循环对话（输入 /quit 退出）
2. 记忆自动注入系统提示词
3. 上下文压缩（长对话自动摘要）
4. 对话结束后自动提取记忆
5. 会话历史持久化（JSONL 文件）
6. 工具调用（AI 自动调用文件读写、搜索、Shell 等工具）

运行: uv run python docs/examples/chat_loop.py
"""

import asyncio
import json
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402

from src.ai.config.model_settings import chat_model_config  # noqa: E402
from src.ai.core.memory import (  # noqa: E402
    ContextBuildRequest,
    memory_service,
)
from src.ai.core.memory.llm_utils import get_chat_llm  # noqa: E402
from src.ai.core.tools.manager import tool_manager  # noqa: E402

# 会话 ID（用于持久化对话历史）
SESSION_ID = "demo-chat-session"


def print_separator(char: str = "-", length: int = 50) -> None:
    print(char * length)


def print_bot(content: str) -> None:
    """格式化输出机器人回复。"""
    print(f"\n🤖 助手: {content}\n")


def print_memory_info() -> None:
    """显示当前记忆状态。"""
    stats = memory_service.get_stats()
    total = stats.get("total", 0)
    types = [f"{k}:{v}" for k, v in stats.items() if k != "total"]
    type_str = ", ".join(types) if types else "无"
    print(f"  📝 记忆: {total} 条 ({type_str})")


def _format_tool_result(result: object) -> str:
    """将工具执行结果转为字符串。"""
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, default=str)


async def chat_once(llm, user_input: str, tools: list) -> str:
    """单轮对话：构建上下文 → 调用 LLM → 工具调用循环 → 返回回复。"""

    # 1. 构建上下文（含记忆注入 + 历史消息 + 自动压缩）
    request = ContextBuildRequest(
        messages=[HumanMessage(content=user_input)],
        model_config=chat_model_config,
        session_id=SESSION_ID,
        enable_memory=True,
        enable_tools=True,  # 注入工具使用指引到系统提示词
        enable_rag=False,  # 如需 RAG 检索，设为 True
    )
    result = await memory_service.abuild_context(request)

    # 2. 绑定工具并调用 LLM
    llm_with_tools = llm.bind_tools(tools)
    response: AIMessage = await llm_with_tools.ainvoke(result.messages)

    # 3. 工具调用循环
    max_rounds = 10
    round_count = 0
    while response.tool_calls and round_count < max_rounds:
        round_count += 1
        # 将 AI 消息（含 tool_calls）加入消息列表
        messages = result.messages + [response]

        # 执行每个工具调用
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]
            print(f"  🔧 调用工具: {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:80]})")

            try:
                tool_result = await tool_manager.execute(tool_name, tool_args)
                result_str = _format_tool_result(tool_result)
                # 截断过长的输出
                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "\n...(输出已截断)"
                print(f"  ✅ 工具结果: {result_str[:120]}{'...' if len(result_str) > 120 else ''}")
            except Exception as e:
                result_str = f"工具执行失败: {e}"
                print(f"  ❌ {result_str}")

            # 将工具结果作为 ToolMessage 加入消息
            messages.append(ToolMessage(content=result_str, tool_call_id=tool_id))

        # 再次调用 LLM（带工具结果）
        response = await llm_with_tools.ainvoke(messages)

    if round_count >= max_rounds:
        print("  ⚠️ 工具调用轮次已达上限")

    # 4. 保存对话历史（用户消息 + AI 回复）
    history_mgr = memory_service.get_history_manager()
    history_mgr.add_message(SESSION_ID, HumanMessage(content=user_input))
    history_mgr.add_message(SESSION_ID, response)

    return response.content


async def extract_and_save_memories(user_msg: str, assistant_msg: str) -> int:
    """从对话中提取并保存记忆。"""
    candidates = await memory_service.aextract_from_conversation(user_msg, assistant_msg)
    if candidates:
        return memory_service.save_extracted(candidates, session_id=SESSION_ID)
    return 0


async def chat_loop() -> None:
    """循环对话主函数。"""
    print("=" * 60)
    print("AI Chat — 记忆增强对话系统")
    print("=" * 60)
    print()
    print("功能说明:")
    print("  - 输入消息开始对话")
    print("  - 输入 /quit 退出")
    print("  - 输入 /memory 查看记忆")
    print("  - 输入 /stats 查看统计")
    print()

    # 初始化 LLM
    llm = get_chat_llm()
    print(f"  模型: {chat_model_config.model_key} ({chat_model_config.backend})")
    print_memory_info()

    # 加载可用工具
    tools = tool_manager.list_tools(enabled_only=True)
    print(f"  🔧 工具: {len(tools)} 个可用")
    if tools:
        names = ", ".join(t.name for t in tools[:8])
        suffix = f" 等{len(tools)}个" if len(tools) > 8 else ""
        print(f"     {names}{suffix}")
    print()

    # 轮次计数
    turn_count = 0

    while True:
        try:
            user_input = input("👤 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n再见！")
            break

        if not user_input:
            continue

        # 内置命令
        if user_input.lower() == "/quit":
            print("\n再见！")
            break

        if user_input.lower() == "/memory":
            print("\n--- 当前记忆 ---")
            for entry in memory_service.list_entries():
                print(f"  [{entry.memory_type}] {entry.name}")
                print(f"    {entry.description[:60]}")
            print("--- 记忆结束 ---\n")
            continue

        if user_input.lower() == "/stats":
            print()
            print_memory_info()
            history_mgr = memory_service.get_history_manager()
            if history_mgr:
                count = history_mgr.message_count(SESSION_ID)
                print(f"  💬 对话消息: {count} 条")
            print()
            continue

        # 对话
        turn_count += 1
        print(f"\n  [轮次 {turn_count}]")

        try:
            assistant_reply = await chat_once(llm, user_input, tools)
        except Exception as e:
            print(f"\n❌ 调用失败: {e}")
            continue

        print_bot(assistant_reply)

        # 异步提取记忆（不阻塞对话流）
        saved = await extract_and_save_memories(user_input, assistant_reply)
        if saved > 0:
            print(f"  💡 自动保存了 {saved} 条新记忆")

    # 对话结束，显示摘要
    print()
    print_separator("=")
    print("会话摘要:")
    print_memory_info()
    history_mgr = memory_service.get_history_manager()
    if history_mgr:
        count = history_mgr.message_count(SESSION_ID)
        print(f"  对话轮次: {turn_count}")
        print(f"  历史消息: {count} 条")
    print_separator("=")


# ── 主入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(chat_loop())
