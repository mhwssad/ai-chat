"""AI Chat 统一 CLI 入口。"""

from src.ai_chat.chains import ChatChain, SummarizeChain, TranslateChain, ExtractionChain, RefineChain
from src.ai_chat.graphs.chat_agent import ChatAgent
from src.ai_chat.graphs.chat_graph import ChatGraph
from src.ai_chat.graphs.unified_agent import UnifiedAgent
from src.ai_chat.memory import memory_factory
from src.ai_chat.tools import tool_registry


# ── 工具函数 ──────────────────────────────────────────────


def _choose(prompt: str, options: list[str]) -> int:
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def _choose_model() -> str:
    model = input("  模型名称（回车默认 qwen-turbo）: ").strip()
    return model or "qwen-turbo"


# ── 1. 对话 ──────────────────────────────────────────────


def menu_chat():
    print("\n── 对话模式 ──")
    idx = _choose("选择 Agent: ", [
        "UnifiedAgent（记忆 + 工具 + RAG）",
        "ChatAgent（ReAct + 工具）",
        "ChatGraph（意图分类 + RAG）",
    ])
    model = _choose_model()

    if idx == 1:
        agent = UnifiedAgent(model_name=model)
        agent.chat()
    elif idx == 2:
        agent = ChatAgent(model_name=model)
        _chat_loop(agent)
    else:
        agent = ChatGraph(model_name=model)
        _chat_loop(agent)


def _chat_loop(agent):
    print("输入 'quit' 或 'exit' 退出\n")
    while True:
        user_input = input("你: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            break
        response = agent.invoke(user_input)
        print(f"AI: {response}\n")


# ── 2. 调用链 ────────────────────────────────────────────


def menu_chains():
    print("\n── 调用链 ──")
    idx = _choose("选择链: ", [
        "ChatChain — 简单对话",
        "SummarizeChain — 文本摘要",
        "TranslateChain — 翻译",
        "ExtractionChain — 结构化抽取",
        "RefineChain — 文本优化",
    ])
    model = _choose_model()

    if idx == 1:
        chain = ChatChain(model_name=model)
        text = input("  输入消息: ")
        print(f"\n结果: {chain.invoke(text)}\n")

    elif idx == 2:
        chain = SummarizeChain(model_name=model)
        text = input("  输入待摘要文本: ")
        print(f"\n摘要: {chain.invoke(text)}\n")

    elif idx == 3:
        chain = TranslateChain(model_name=model)
        target = input("  目标语言（默认中文）: ").strip() or "中文"
        text = input("  输入待翻译文本: ")
        print(f"\n译文: {chain.invoke(text, target=target)}\n")

    elif idx == 4:
        chain = ExtractionChain(model_name=model)
        text = input("  输入文本: ")
        fields = input("  提取字段（逗号分隔，如: 姓名,年龄,地址）: ")
        field_list = [f.strip() for f in fields.split(",") if f.strip()]
        print(f"\n结果: {chain.invoke(text, field_list)}\n")

    elif idx == 5:
        chain = RefineChain(model_name=model)
        text = input("  输入原始文本: ")
        instruction = input("  优化指令: ")
        print(f"\n结果: {chain.invoke(instruction, text)}\n")


# ── 3. 工具管理 ──────────────────────────────────────────


def menu_tools():
    print("\n── 已注册工具 ──")
    tools = tool_registry.get_all()
    if not tools:
        print("  （无）\n")
        return
    for t in tools:
        desc = t.description.split("\n")[0] if t.description else "无描述"
        print(f"  {t.name}: {desc}")
    print()


# ── 4. 记忆管理 ──────────────────────────────────────────


def menu_memory():
    print("\n── 记忆管理 ──")
    idx = _choose("操作: ", [
        "列出历史会话",
        "查看会话摘要",
        "删除会话",
    ])

    store = memory_factory.create()

    if idx == 1:
        sessions = store.list_sessions()
        if not sessions:
            print("  （无历史会话）\n")
            return
        for s in sessions:
            msg_count = store.count_messages(s.session_id)
            print(f"  [{s.session_id[:8]}...] {s.updated_at.strftime('%Y-%m-%d %H:%M')} | {msg_count} 条消息 | {s.title or '无标题'}")
        print()

    elif idx == 2:
        sid = input("  会话 ID: ").strip()
        summary = store.load_summary(sid)
        print(f"\n  摘要: {summary or '（无摘要）'}\n")

    elif idx == 3:
        sid = input("  会话 ID: ").strip()
        store.delete_session(sid)
        print("  已删除。\n")


# ── 主菜单 ────────────────────────────────────────────────


def main():
    while True:
        print("\n=== AI Chat ===")
        idx = _choose("请选择: ", [
            "对话",
            "调用链",
            "工具管理",
            "记忆管理",
            "退出",
        ])

        if idx == 1:
            menu_chat()
        elif idx == 2:
            menu_chains()
        elif idx == 3:
            menu_tools()
        elif idx == 4:
            menu_memory()
        else:
            print("再见！")
            break


if __name__ == "__main__":
    main()
