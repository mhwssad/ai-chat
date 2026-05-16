"""Prompts 模块管理入口 — 提供交互式 CLI 菜单管理提示词。"""

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.prompts.manager import PromptManager

logger = get_logger(__name__)


def _choose(prompt: str, options: list[str]) -> int:
    """显示选项列表并等待用户输入，返回选择的序号（从 1 开始）。"""
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = input(prompt).strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw)


def _print_prompt(p) -> None:
    """格式化打印单个提示词摘要行。"""
    tag = "[内置]" if p.is_builtin else "[自定义]"
    stype = "文件" if p.source_type == "file" else "内联"
    vars_str = f" 变量: {p.input_variables}" if p.input_variables else ""
    tags_str = f" [{p.tags}]" if p.tags else ""
    print(f"  {tag} {p.name} ({stype}) | {p.description}{tags_str}{vars_str}")


def menu_prompts():
    """提示词管理 — 交互式 CLI 菜单。

    功能:
    1. 列出所有提示词
    2. 搜索提示词
    3. 查看提示词详情（内容、变量、标签）
    4. 创建简单提示词（inline）
    5. 创建模板文件提示词（file → .jinja2）
    6. 编辑提示词
    7. 删除提示词（内置不可删）
    8. 查看版本历史
    9. 回滚到指定版本
    10. 返回上级
    """
    logger.info("进入提示词管理菜单")
    mgr = PromptManager()

    while True:
        print("\n── 提示词管理 ──")
        idx = _choose("操作: ", [
            "列出所有提示词",
            "搜索提示词",
            "查看提示词详情",
            "创建简单提示词（内联）",
            "创建模板文件提示词（文件）",
            "编辑提示词",
            "删除提示词",
            "查看版本历史",
            "回滚到指定版本",
            "返回上级",
        ])
        if idx == 10:
            logger.debug("退出提示词管理菜单")
            return

        if idx == 1:
            total = mgr.count_prompts()
            prompts = mgr.list_prompts()
            if not prompts:
                print("  （无提示词）\n")
                continue
            print(f"\n  共 {total} 个提示词:\n")
            for p in prompts:
                _print_prompt(p)
            print()

        elif idx == 2:
            keyword = input("  关键词: ").strip()
            if not keyword:
                continue
            results = mgr.search_prompts(keyword)
            if not results:
                print(f"  未找到匹配 \"{keyword}\" 的提示词\n")
                continue
            print(f"\n  找到 {len(results)} 个:\n")
            for p in results:
                _print_prompt(p)
            print()

        elif idx == 3:
            name = input("  提示词名称: ").strip()
            try:
                p = mgr.get_prompt(name)
            except KeyError as e:
                print(f"  错误: {e}\n")
                continue
            print(f"\n  名称:     {p.name}")
            print(f"  类型:     {'文件' if p.source_type == 'file' else '内联'}")
            print(f"  描述:     {p.description}")
            print(f"  标签:     {p.tags or '（无）'}")
            print(f"  内置:     {'是' if p.is_builtin else '否'}")
            if p.input_variables:
                print(f"  变量:     {', '.join(p.input_variables)}")
            if p.file_path:
                print(f"  文件路径: data/prompts/{p.file_path}")
            print(f"\n  内容:\n  {'-' * 40}")
            for line in p.content.split("\n"):
                print(f"  {line}")
            print(f"  {'-' * 40}\n")

        elif idx == 4:
            name = input("  名称: ").strip()
            if not name:
                continue
            desc = input("  描述: ").strip()
            tags = input("  标签（逗号分隔）: ").strip()
            print("  输入模板内容（jinja2 格式，空行结束）:")
            lines = []
            while True:
                line = input("  > ")
                if not line:
                    break
                lines.append(line)
            content = "\n".join(lines)
            if not content:
                continue
            try:
                mgr.create_prompt(name, content=content, description=desc,
                                  tags=tags, source_type="inline")
                print(f"  已创建提示词: {name}\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 5:
            name = input("  名称: ").strip()
            if not name:
                continue
            desc = input("  描述: ").strip()
            tags = input("  标签（逗号分隔）: ").strip()
            print("  输入模板内容（jinja2 格式，空行结束）:")
            lines = []
            while True:
                line = input("  > ")
                if not line:
                    break
                lines.append(line)
            content = "\n".join(lines)
            if not content:
                continue
            file_name = f"{name.replace('.', '_')}.jinja2"
            try:
                mgr.create_prompt(name, content=content, file_path=file_name,
                                  source_type="file", description=desc, tags=tags)
                print(f"  已创建提示词: {name} (文件: data/prompts/{file_name})\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 6:
            name = input("  提示词名称: ").strip()
            try:
                p = mgr.get_prompt(name)
            except KeyError as e:
                print(f"  错误: {e}\n")
                continue
            if p.is_builtin:
                print("  内置提示词不可编辑\n")
                continue

            print(f"  当前描述: {p.description}")
            new_desc = input("  新描述（留空不变）: ").strip()
            new_tags = input(f"  新标签（当前: {p.tags}，留空不变）: ").strip()
            print("  输入新内容（jinja2 格式，空行结束，留空不变）:")
            lines = []
            while True:
                line = input("  > ")
                if not line:
                    break
                lines.append(line)
            new_content = "\n".join(lines)

            updates = {}
            if new_desc:
                updates["description"] = new_desc
            if new_tags:
                updates["tags"] = new_tags
            if new_content:
                updates["content"] = new_content
            if not updates:
                print("  无变更\n")
                continue

            try:
                mgr.update_prompt(name, **updates)
                print(f"  已更新: {name}\n")
            except Exception as e:
                print(f"  错误: {e}\n")

        elif idx == 7:
            name = input("  提示词名称: ").strip()
            try:
                p = mgr.get_prompt(name)
            except KeyError as e:
                print(f"  错误: {e}\n")
                continue
            if p.is_builtin:
                print("  内置提示词不可删除\n")
                continue
            confirm = input(f"  确认删除 '{name}'？(y/N): ").strip().lower()
            if confirm != "y":
                print("  已取消\n")
                continue
            mgr.delete_prompt(name)
            print(f"  已删除: {name}\n")

        elif idx == 8:
            name = input("  提示词名称: ").strip()
            try:
                versions = mgr.list_versions(name)
            except KeyError as e:
                print(f"  错误: {e}\n")
                continue
            if not versions:
                print(f"  '{name}' 无版本历史\n")
                continue
            print(f"\n  '{name}' 的版本历史（共 {len(versions)} 条）:\n")
            for v in versions:
                preview = v.content[:50].replace("\n", " ") if v.content else "（空）"
                print(f"  #{v.id} | {v.created_at.strftime('%Y-%m-%d %H:%M') if v.created_at else '?'} | {preview}...")
            print()

        elif idx == 9:
            name = input("  提示词名称: ").strip()
            try:
                versions = mgr.list_versions(name)
            except KeyError as e:
                print(f"  错误: {e}\n")
                continue
            if not versions:
                print(f"  '{name}' 无版本历史\n")
                continue
            print(f"\n  '{name}' 的版本历史:\n")
            for v in versions:
                preview = v.content[:50].replace("\n", " ") if v.content else "（空）"
                print(f"  #{v.id} | {v.created_at.strftime('%Y-%m-%d %H:%M') if v.created_at else '?'} | {preview}...")
            vid = input("\n  输入要回滚的版本 ID: ").strip()
            if not vid.isdigit():
                print("  无效的版本 ID\n")
                continue
            confirm = input(f"  确认回滚 '{name}' 到版本 #{vid}？(y/N): ").strip().lower()
            if confirm != "y":
                print("  已取消\n")
                continue
            try:
                mgr.restore_version(name, int(vid))
                print(f"  已回滚: {name} -> 版本 #{vid}\n")
            except Exception as e:
                print(f"  错误: {e}\n")
