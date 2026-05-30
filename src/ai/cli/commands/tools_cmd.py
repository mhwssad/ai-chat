"""工具管理子命令 — list / enable / disable / test。"""

import asyncio

import typer

tools_app = typer.Typer(help="工具管理")


def _get_tool_registry():
    """延迟获取工具注册表。"""
    from src.ai.core.container import container

    return container.tool_container.tool_registry()


def _get_tool_manager():
    """延迟获取工具管理器。"""
    from src.ai.core.container import container

    return container.tool_container.tool_manager()


@tools_app.command("list")
def list_tools(
    all_tools: bool = typer.Option(False, "--all", "-a", help="显示所有工具（含禁用）"),
) -> None:
    """列出已注册的工具。"""
    registry = _get_tool_registry()
    tools = registry.list(enabled_only=not all_tools)

    if not tools:
        typer.echo("  没有已注册的工具")
        return

    typer.echo(f"\n  共 {len(tools)} 个工具:\n")
    for tool in tools:
        meta = registry.get_meta(tool.name)
        status = "●" if meta.enabled else "○"
        source = meta.source_type
        desc = getattr(tool, "description", "") or ""
        typer.echo(f"  {status} {tool.name:<24s} [{source}] {desc[:50]}")
    typer.echo()


@tools_app.command("enable")
def enable_tool(name: str = typer.Argument(..., help="工具名称")) -> None:
    """启用指定工具。"""
    registry = _get_tool_registry()
    try:
        meta = registry.get_meta(name)
        # ToolMeta 的 enabled 字段需要通过 registry 直接操作
        # 由于 ToolMeta 不是 frozen，可以直接修改
        meta.enabled = True
        typer.echo(f"  ✓ 已启用工具: {name}")
    except Exception as e:
        typer.echo(f"  ✗ 操作失败: {e}", err=True)


@tools_app.command("disable")
def disable_tool(name: str = typer.Argument(..., help="工具名称")) -> None:
    """禁用指定工具。"""
    registry = _get_tool_registry()
    try:
        tool = registry.get(name)
        meta = registry.get_meta(tool.name)
        if meta.essential:
            typer.echo(f"  ✗ 不能禁用核心工具: {name}", err=True)
            return
        meta.enabled = False
        typer.echo(f"  ✓ 已禁用工具: {name}")
    except Exception as e:
        typer.echo(f"  ✗ 操作失败: {e}", err=True)


@tools_app.command("test")
def test_tool(
    name: str = typer.Argument(..., help="工具名称"),
    args_json: str = typer.Option("{}", "--args", help="JSON 格式的参数"),
) -> None:
    """测试执行工具。"""
    import json

    manager = _get_tool_manager()

    try:
        arguments = json.loads(args_json)
    except json.JSONDecodeError:
        typer.echo(f"  ✗ 参数 JSON 格式错误: {args_json}", err=True)
        return

    typer.echo(f"  执行工具: {name}")
    typer.echo(f"  参数: {args_json}")

    async def _run():
        try:
            result = await manager.execute(name, arguments)
            result_str = str(result)
            if len(result_str) > 500:
                result_str = result_str[:500] + "\n...(已截断)"
            typer.echo(f"\n  结果:\n  {result_str}")
        except Exception as e:
            typer.echo(f"\n  ✗ 执行失败: {e}", err=True)

    asyncio.run(_run())
