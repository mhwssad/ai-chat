"""Memory 模块管理入口。"""

from src.ai_chat.memory import memory_factory


def _choose(prompt: str, options: list[str]) -> int:
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def menu_memory():
    """记忆管理 — 查看、删除会话。"""
    while True:
        print("\n── 记忆管理 ──")
        idx = _choose("操作: ", [
            "列出历史会话",
            "查看会话摘要",
            "删除会话",
            "返回上级",
        ])
        if idx == 4:
            return

        store = memory_factory.create()

        if idx == 1:
            sessions = store.list_sessions()
            if not sessions:
                print("  （无历史会话）\n")
                continue
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
