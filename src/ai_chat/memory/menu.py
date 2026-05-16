"""Memory 模块管理入口 — 提供交互式 CLI 菜单查看和管理会话。

使用 SessionManager 高层接口，避免直接操作 MemoryProvider 产生 N+1 查询。
"""

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.memory import SessionManager

logger = get_logger(__name__)


def _choose(prompt: str, options: list[str]) -> int:
    """显示选项列表并等待用户输入，返回选择的序号（从 1 开始）。"""
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def _print_session(detail) -> None:
    """格式化打印单个会话摘要行。"""
    summary_flag = "有摘要" if detail.has_summary else "无摘要"
    print(
        f"  [{detail.session_id[:8]}] "
        f"{detail.updated_at.strftime('%Y-%m-%d %H:%M')} | "
        f"{detail.message_count} 条消息 | "
        f"{summary_flag} | "
        f"{detail.title or '无标题'}"
    )


def menu_memory():
    """记忆管理 — 交互式 CLI 菜单。

    功能:
    1. 列出历史会话（带消息数、摘要状态，无 N+1 查询）
    2. 按标题关键词搜索会话
    3. 查看会话详情（token 使用量、摘要、模型信息）
    4. 重命名会话
    5. 重置会话上下文（清空消息和摘要，保留会话）
    6. 删除会话
    7. 返回上级菜单
    """
    logger.info("进入记忆管理菜单")
    mgr = SessionManager()

    while True:
        print("\n── 记忆管理 ──")
        idx = _choose("操作: ", [
            "列出历史会话",
            "搜索会话",
            "查看会话详情",
            "重命名会话",
            "重置会话上下文",
            "删除会话",
            "返回上级",
        ])
        if idx == 7:
            logger.debug("退出记忆管理菜单")
            return

        if idx == 1:
            # 列出历史会话
            total = mgr.count_sessions()
            sessions = mgr.list_sessions()
            if not sessions:
                print("  （无历史会话）\n")
                continue
            print(f"  共 {total} 个会话:\n")
            for s in sessions:
                _print_session(s)
            print()

        elif idx == 2:
            # 搜索会话
            keyword = input("  关键词: ").strip()
            if not keyword:
                continue
            results = mgr.search_sessions(keyword)
            if not results:
                print(f"  未找到包含 \"{keyword}\" 的会话\n")
                continue
            print(f"  找到 {len(results)} 个会话:\n")
            for s in results:
                _print_session(s)
            print()

        elif idx == 3:
            # 查看会话详情
            sid = input("  会话 ID: ").strip()
            try:
                detail = mgr.get_session_detail(sid)
            except Exception as e:
                print(f"  错误: {e}\n")
                continue
            print(f"\n  ID:       {detail.session_id}")
            print(f"  标题:     {detail.title or '无标题'}")
            print(f"  消息数:   {detail.message_count}")
            print(f"  摘要:     {'有' if detail.has_summary else '无'}")
            print(f"  创建时间: {detail.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  更新时间: {detail.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if detail.model_name:
                print(f"  模型:     {detail.model_name}")
            if detail.last_prompt_tokens:
                print(f"  上次 prompt tokens: {detail.last_prompt_tokens}")
            print()

        elif idx == 4:
            # 重命名会话
            sid = input("  会话 ID: ").strip()
            title = input("  新标题: ").strip()
            if not title:
                continue
            mgr.rename_session(sid, title)
            print("  已重命名。\n")

        elif idx == 5:
            # 重置会话上下文
            sid = input("  会话 ID: ").strip()
            confirm = input(f"  确认重置 [{sid[:8]}] 的所有消息和摘要？(y/N): ").strip().lower()
            if confirm != "y":
                print("  已取消。\n")
                continue
            mgr.reset_session(sid)
            print("  上下文已重置。\n")

        elif idx == 6:
            # 删除会话
            sid = input("  会话 ID: ").strip()
            confirm = input(f"  确认删除会话 [{sid[:8]}]？(y/N): ").strip().lower()
            if confirm != "y":
                print("  已取消。\n")
                continue
            mgr.delete_session(sid)
            print("  已删除。\n")
