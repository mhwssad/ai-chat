"""Workflows 模块管理入口 — 提供交互式 CLI 菜单管理工作流。"""

from __future__ import annotations

import json

from src.ai_chat.workflows import workflow_manager
from src.ai_chat.workflows.models import EdgeConfig, NodeConfig
from src.ai_chat.workflows.nodes import NodeExecutorFactory


def _choose(prompt: str, options: list[str]) -> int:
    """显示选项列表并等待用户输入，返回选择的序号（从 1 开始）。"""
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def _print_workflow(record) -> None:
    """格式化打印工作流摘要行。"""
    node_count = len(record.nodes)
    edge_count = len(record.edges)
    status = "启用" if record.is_active else "停用"
    print(f"  {record.name} | 节点: {node_count} | 边: {edge_count} | [{status}]")


def _print_nodes(nodes: list[NodeConfig]) -> None:
    """格式化打印节点列表。"""
    for n in nodes:
        ref = f" → {n.ref}" if n.ref else ""
        print(f"    {n.name} ({n.type}){ref}")


def _print_edges(edges: list[EdgeConfig]) -> None:
    """格式化打印边列表。"""
    for e in edges:
        if e.type == "direct":
            print(f"    {e.source} → {e.target}")
        else:
            conds = ", ".join(f"{k}:{v}" for k, v in e.conditions.items())
            print(f"    {e.source} → [{conds}]")


def _input_nodes() -> list[NodeConfig]:
    """交互式输入节点配置。"""
    node_types = NodeExecutorFactory().list_types()
    print(f"  可用节点类型: {', '.join(node_types)}")
    print("  输入节点配置（JSON 数组格式，空行结束）:")
    lines = []
    while True:
        line = input("  > ").strip()
        if not line:
            break
        lines.append(line)
    text = "\n".join(lines)
    if not text.strip():
        return []
    try:
        return [NodeConfig(**n) for n in json.loads(text)]
    except Exception as e:
        print(f"  解析节点失败: {e}")
        return []


def _input_edges() -> list[EdgeConfig]:
    """交互式输入边配置。"""
    print("  输入边配置（JSON 数组格式，空行结束）:")
    lines = []
    while True:
        line = input("  > ").strip()
        if not line:
            break
        lines.append(line)
    text = "\n".join(lines)
    if not text.strip():
        return []
    try:
        return [EdgeConfig(**e) for e in json.loads(text)]
    except Exception as e:
        print(f"  解析边失败: {e}")
        return []


def menu_workflows():
    """工作流管理 — CRUD + 执行 + 校验。

    功能:
    1. 列出已保存工作流
    2. 查看工作流详情
    3. 创建工作流
    4. 编辑工作流
    5. 删除工作流
    6. 执行工作流
    7. 校验工作流配置
    8. 返回上级
    """
    while True:
        print("\n── 工作流管理 ──")
        idx = _choose("操作: ", [
            "列出已保存工作流",
            "查看工作流详情",
            "创建工作流",
            "编辑工作流",
            "删除工作流",
            "执行工作流",
            "校验工作流配置",
            "返回上级",
        ])
        if idx == 8:
            return

        if idx == 1:
            workflows = workflow_manager.list_workflows()
            if not workflows:
                print("  （无已保存工作流）\n")
                continue
            total = workflow_manager.count_workflows()
            print(f"\n  共 {total} 个工作流:\n")
            for w in workflows:
                _print_workflow(w)
            print()

        elif idx == 2:
            name = input("  工作流名称: ").strip()
            if not name:
                continue
            try:
                w = workflow_manager.get_workflow(name)
            except KeyError as e:
                print(f"  错误: {e}\n")
                continue
            print(f"\n  名称:       {w.name}")
            print(f"  ID:         {w.id}")
            print(f"  描述:       {w.description or '（无）'}")
            print(f"  模型:       {w.model_name or '（默认）'}")
            print(f"  标签:       {w.tags or '（无）'}")
            print(f"  状态:       {'启用' if w.is_active else '停用'}")
            print(f"  节点 ({len(w.nodes)}):")
            _print_nodes(w.nodes)
            print(f"  边 ({len(w.edges)}):")
            _print_edges(w.edges)
            print(f"  创建时间:   {w.created_at}")
            print(f"  更新时间:   {w.updated_at}")
            print()

        elif idx == 3:
            name = input("  工作流名称: ").strip()
            if not name:
                continue
            if workflow_manager.workflow_exists(name):
                print(f"  工作流 '{name}' 已存在\n")
                continue
            desc = input("  描述: ").strip()
            model = input("  默认模型（留空使用默认）: ").strip()
            tags = input("  标签（逗号分隔）: ").strip()

            nodes = _input_nodes()
            edges = _input_edges()

            try:
                workflow_manager.create_workflow(
                    name=name,
                    description=desc,
                    model_name=model,
                    nodes=nodes,
                    edges=edges,
                    tags=tags,
                )
                print(f"  已创建工作流: {name} ({len(nodes)} 节点, {len(edges)} 边)\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 4:
            name = input("  工作流名称: ").strip()
            if not name:
                continue
            try:
                w = workflow_manager.get_workflow(name)
            except KeyError as e:
                print(f"  错误: {e}\n")
                continue

            print(f"  当前描述: {w.description}")
            new_desc = input("  新描述（留空不变）: ").strip()
            new_model = input(f"  新模型（当前: {w.model_name}，留空不变）: ").strip()
            new_tags = input(f"  新标签（当前: {w.tags}，留空不变）: ").strip()

            updates = {}
            if new_desc:
                updates["description"] = new_desc
            if new_model:
                updates["model_name"] = new_model
            if new_tags:
                updates["tags"] = new_tags

            edit_nodes = input("  编辑节点配置？(y/N): ").strip().lower()
            if edit_nodes == "y":
                nodes = _input_nodes()
                if nodes:
                    updates["nodes"] = nodes

            edit_edges = input("  编辑边配置？(y/N): ").strip().lower()
            if edit_edges == "y":
                edges = _input_edges()
                if edges:
                    updates["edges"] = edges

            if not updates:
                print("  无变更\n")
                continue

            try:
                workflow_manager.update_workflow(name, **updates)
                print(f"  已更新: {name}\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 5:
            name = input("  工作流名称: ").strip()
            if not name:
                continue
            if not workflow_manager.workflow_exists(name):
                print(f"  工作流 '{name}' 不存在\n")
                continue
            confirm = input(f"  确认删除 '{name}'？(y/N): ").strip().lower()
            if confirm != "y":
                print("  已取消\n")
                continue
            try:
                workflow_manager.delete_workflow(name)
                print(f"  已删除: {name}\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 6:
            name = input("  工作流名称: ").strip()
            if not name:
                continue
            user_input = input("  输入内容: ").strip()
            if not user_input:
                continue
            try:
                result = workflow_manager.invoke(name, user_input)
                print(f"\n  结果:\n  {result}\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 7:
            name = input("  工作流名称: ").strip()
            if not name:
                continue
            try:
                w = workflow_manager.get_workflow(name)
            except KeyError as e:
                print(f"  错误: {e}\n")
                continue
            from src.ai_chat.workflows.engine import validate_workflow
            errors = validate_workflow(w)
            if errors:
                print(f"\n  校验失败 ({len(errors)} 个错误):\n")
                for err in errors:
                    print(f"    - {err}")
                print()
            else:
                print("  校验通过\n")
