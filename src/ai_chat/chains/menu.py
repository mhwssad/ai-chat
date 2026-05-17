"""Chains 模块管理入口 — 提供交互式 CLI 菜单管理持久化链配置。"""

from __future__ import annotations

import json

from src.ai_chat.chains import chain_manager
from src.ai_chat.chains.factory import chain_factory
from src.ai_chat.chains.observability import metrics_collector


def _choose(prompt: str, options: list[str]) -> int:
    """显示选项列表并等待用户输入，返回选择的序号（从 1 开始）。"""
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def _print_chain(record) -> None:
    """格式化打印链摘要行。"""
    status = "启用" if record.is_active else "停用"
    model = record.model_name or "默认"
    print(f"  {record.name} | 类型: {record.chain_type} | 模型: {model} | [{status}]")


def _choose_chain_type() -> str:
    """从工厂注册类型中选择，返回 chain_type 名称。"""
    info = chain_factory.get_registry_info()
    if not info:
        print("  （无可用链类型）")
        return ""
    for i, item in enumerate(info, 1):
        print(f"    {i}. {item['name']} ({item['class']})")
    while True:
        raw = input("  选择类型: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(info):
            return info[int(raw) - 1]["name"]


_CHAIN_TYPE_LABELS = {
    "chat": "对话",
    "summarize": "文本摘要",
    "translate": "翻译",
    "extraction": "结构化抽取",
    "refine": "文本优化",
    "rag": "检索增强生成",
    "code_review": "代码审查",
}


def menu_chains():
    """链管理 — 持久化链的 CRUD + 执行 + 度量。

    功能:
    1. 列出已保存链
    2. 搜索链
    3. 查看链详情
    4. 创建链
    5. 编辑链
    6. 删除链
    7. 执行链
    8. 列出工厂注册类型
    9. 查看度量
    10. 返回上级
    """
    while True:
        print("\n── 链管理 ──")
        idx = _choose("操作: ", [
            "列出已保存链",
            "搜索链",
            "查看链详情",
            "创建链",
            "编辑链",
            "删除链",
            "执行链",
            "列出工厂注册类型",
            "查看度量",
            "返回上级",
        ])
        if idx == 10:
            return

        if idx == 1:
            chains = chain_manager.list_chains()
            if not chains:
                print("  （无已保存链）\n")
                continue
            total = chain_manager.count_chains()
            print(f"\n  共 {total} 条链配置:\n")
            for c in chains:
                _print_chain(c)
            print()

        elif idx == 2:
            keyword = input("  关键词: ").strip()
            if not keyword:
                continue
            results = chain_manager.search_chains(keyword)
            if not results:
                print(f"  未找到匹配 \"{keyword}\" 的链\n")
                continue
            print(f"\n  找到 {len(results)} 条:\n")
            for c in results:
                _print_chain(c)
            print()

        elif idx == 3:
            name = input("  链名称: ").strip()
            if not name:
                continue
            try:
                c = chain_manager.get_chain(name)
            except KeyError as e:
                print(f"  错误: {e}\n")
                continue
            print(f"\n  名称:       {c.name}")
            print(f"  ID:         {c.id}")
            print(f"  类型:       {c.chain_type}")
            print(f"  模型:       {c.model_name or '（默认）'}")
            print(f"  描述:       {c.description or '（无）'}")
            print(f"  标签:       {c.tags or '（无）'}")
            print(f"  状态:       {'启用' if c.is_active else '停用'}")
            if c.config:
                print(f"  配置:       {json.dumps(c.config, ensure_ascii=False)}")
            if c.prompt_context:
                print(f"  Prompt 上下文: {json.dumps(c.prompt_context, ensure_ascii=False)}")
            print(f"  创建时间:   {c.created_at}")
            print(f"  更新时间:   {c.updated_at}")
            print()

        elif idx == 4:
            name = input("  链名称: ").strip()
            if not name:
                continue
            if chain_manager.chain_exists(name):
                print(f"  链 '{name}' 已存在\n")
                continue
            chain_type = _choose_chain_type()
            if not chain_type:
                continue
            model_name = input("  模型名称（留空使用默认）: ").strip()
            description = input("  描述: ").strip()
            tags = input("  标签（逗号分隔）: ").strip()
            try:
                chain_manager.create_chain(
                    name=name,
                    chain_type=chain_type,
                    model_name=model_name,
                    description=description,
                    tags=tags,
                )
                print(f"  已创建链: {name} ({chain_type})\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 5:
            name = input("  链名称: ").strip()
            if not name:
                continue
            try:
                c = chain_manager.get_chain(name)
            except KeyError as e:
                print(f"  错误: {e}\n")
                continue

            print(f"  当前描述: {c.description}")
            new_desc = input("  新描述（留空不变）: ").strip()
            new_tags = input(f"  新标签（当前: {c.tags}，留空不变）: ").strip()
            new_model = input(f"  新模型（当前: {c.model_name}，留空不变）: ").strip()

            updates = {}
            if new_desc:
                updates["description"] = new_desc
            if new_tags:
                updates["tags"] = new_tags
            if new_model:
                updates["model_name"] = new_model
            if not updates:
                print("  无变更\n")
                continue

            try:
                chain_manager.update_chain(name, **updates)
                print(f"  已更新: {name}\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 6:
            name = input("  链名称: ").strip()
            if not name:
                continue
            if not chain_manager.chain_exists(name):
                print(f"  链 '{name}' 不存在\n")
                continue
            confirm = input(f"  确认删除 '{name}'？(y/N): ").strip().lower()
            if confirm != "y":
                print("  已取消\n")
                continue
            try:
                chain_manager.delete_chain(name)
                print(f"  已删除: {name}\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 7:
            name = input("  链名称: ").strip()
            if not name:
                continue
            user_input = input("  输入内容: ").strip()
            if not user_input:
                continue
            try:
                result = chain_manager.invoke(name, input=user_input)
                print(f"\n  结果:\n  {result}\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 8:
            info = chain_factory.get_registry_info()
            registered = chain_factory.list_chains()
            if not registered:
                print("  （无注册类型）\n")
                continue
            print()
            for item in info:
                label = _CHAIN_TYPE_LABELS.get(item["name"], "")
                print(f"  {item['name']}: {item['class']} {label}")
            print()

        elif idx == 9:
            summary = metrics_collector.summary()
            print(f"  总调用: {summary.total_calls}")
            print(f"  成功: {summary.success_calls}  失败: {summary.failed_calls}")
            print(f"  平均延迟: {summary.avg_latency_ms:.0f}ms")
            print(f"  Token: 输入 {summary.total_input_tokens} + 输出 {summary.total_output_tokens}")
            print()
