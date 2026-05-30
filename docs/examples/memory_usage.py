"""Memory 模块使用示例。

演示记忆系统的核心功能：
1. 记忆 CRUD（保存、查询、删除、列表）
2. 记忆搜索（关键词匹配）
3. 上下文构建（策略驱动 + token 预算）
4. 对话记忆提取（正则快速模式 + LLM 增强模式）
5. RAG 优化检索（双路查询 + 合并去重）

运行: uv run python docs/examples/memory_usage.py
"""

import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain_core.messages import HumanMessage

from src.ai.config.model_settings import chat_model_config
from src.ai.core.context import ContextBuildRequest
from src.ai.core.memory import (
    MemoryWriteRequest,
    memory_service,
)


# ── 1. 记忆 CRUD ──────────────────────────────────────────


def demo_memory_crud():
    """记忆的保存、查询、列表、删除。"""
    print("=== 1. 记忆 CRUD ===\n")

    # 保存记忆（指定 session_id，同一会话的记忆保存到同一文件）
    entry = memory_service.save(MemoryWriteRequest(
        content="用户偏好使用 Python 3.13 + uv 管理项目依赖",
        memory_type="user",
        name="user-python-pref",
        description="用户 Python 开发环境偏好",
    ), session_id="demo-session")
    print(f"  保存: {entry.name} ({entry.memory_type})")
    print(f"    文件: {entry.file_path}")

    # 保存更多记忆（同一 session_id）
    memory_service.save(MemoryWriteRequest(
        content="项目使用 FastAPI + SQLModel + LangChain 技术栈",
        memory_type="project",
        description="AI Chat 项目技术栈",
    ), session_id="demo-session")
    memory_service.save(MemoryWriteRequest(
        content="代码风格：注释用中文，类名函数名用英文，类型标注必须完整",
        memory_type="feedback",
        description="代码风格要求",
    ), session_id="demo-session")
    memory_service.save(MemoryWriteRequest(
        content="Grafana 监控面板: http://grafana.internal/d/api-latency",
        memory_type="reference",
        description="API 延迟监控面板地址",
    ), session_id="demo-session")

    # 列出所有记忆
    print("\n  所有记忆:")
    for e in memory_service.list_entries():
        print(f"    [{e.memory_type}] {e.name}: {e.description[:50]}")

    # 按类型列出
    user_memories = memory_service.list_entries(memory_type="user")
    print(f"\n  user 类型记忆: {len(user_memories)} 条")

    # 按名称查询
    found = memory_service.get("user-python-pref")
    print(f"  查询 user-python-pref: {found.content if found else '未找到'}")

    # 统计
    stats = memory_service.get_stats()
    print(f"  统计: {stats}")

    print()


# ── 2. 记忆搜索 ──────────────────────────────────────────


def demo_memory_search():
    """关键词搜索记忆。"""
    print("=== 2. 记忆搜索 ===\n")

    queries = ["Python", "代码风格", "监控", "FastAPI"]
    for query in queries:
        results = memory_service.search(query, limit=3)
        print(f'  搜索 "{query}": {len(results)} 条结果')
        for r in results:
            print(f"    [{r.score:.2f}] [{r.entry.memory_type}] {r.entry.description[:40]}")
    print()


# ── 3. 上下文构建 ──────────────────────────────────────────


def demo_context_build():
    """构建 LLM 上下文（同步模式）。"""
    print("=== 3. 上下文构建 ===\n")

    # 基础上下文构建
    request = ContextBuildRequest(
        messages=[HumanMessage(content="你好，帮我写个 Python 函数")],
        model_config=chat_model_config,
        enable_memory=True,
        memory_search_limit=3,
    )
    # 上下文构建已迁移到 ContextService（src.ai.core.context）
    # 此处跳过，仅展示 MemoryService 的记忆管理 API
    print("  (上下文构建已迁移到 ContextService.abuild，此处跳过)")
    print()

    # 预览系统提示词
    if result.system_message:
        preview = result.system_message[:200].replace("\n", "\n    ")
        print(f"  系统提示词预览:\n    {preview}...")
    print()


# ── 4. 对话记忆提取 ──────────────────────────────────────────


def demo_memory_extraction():
    """从对话中自动提取记忆。"""
    print("=== 4. 对话记忆提取 ===\n")

    # 模拟一段对话
    user_msg = "我习惯用 black 格式化代码，ruff 做 lint 检查"
    assistant_msg = "好的，我会使用 black 格式化和 ruff lint 来检查代码质量。"

    # 快速模式（正则匹配）
    candidates = memory_service.extract_from_conversation(user_msg, assistant_msg)
    print(f"  快速模式提取: {len(candidates)} 条候选")
    for c in candidates:
        print(f"    [{c.memory_type}] {c.content[:50]}")
        print(f"      置信度: {c.metadata.get('confidence', 'N/A')}")

    # 保存提取的记忆
    if candidates:
        saved = memory_service.save_extracted(candidates)
        print(f"  新保存: {saved} 条")
    print()


# ── 5. MEMORY.md 索引 ──────────────────────────────────────────


def demo_memory_index():
    """查看 MEMORY.md 索引内容。"""
    print("=== 5. MEMORY.md 索引 ===\n")

    index_content = memory_service.get_context_for_prompt()
    if index_content:
        print(f"  索引长度: {len(index_content)} 字符")
        preview = index_content[:300].replace("\n", "\n    ")
        print(f"  内容预览:\n    {preview}...")
    else:
        print("  (索引为空)")
    print()


# ── 6. 清理示例数据 ──────────────────────────────────────────


def demo_cleanup():
    """清理示例数据。"""
    print("=== 6. 清理示例数据 ===\n")

    entries = memory_service.list_entries()
    for entry in entries:
        if entry.name and entry.name.startswith("user-"):
            memory_service.delete(entry.name)
            print(f"  删除: {entry.name}")

    # 重建索引
    memory_service.rebuild_index()
    print("  索引已重建")

    stats = memory_service.get_stats()
    print(f"  清理后统计: {stats}")
    print()


# ── 主入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Memory 模块示例")
    print("=" * 60)
    print()

    demo_memory_crud()
    demo_memory_search()
    demo_context_build()
    demo_memory_extraction()
    demo_memory_index()
    demo_cleanup()

    print(">>> 示例结束 <<<")
