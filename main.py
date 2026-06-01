"""AI Chat 统一 CLI 入口。

子命令：
  serve         启动 FastAPI 服务
  chat          交互式对话（记忆 + 工具调用）
  agent         Agent 模式（自主任务执行）
  generate-key  生成 API Key 加密密钥
  dashboard     TUI 控制台仪表盘
  manage        管理子命令组（tools/memory/scheduler/chat）
"""

import asyncio
import json
import sys
from pathlib import Path

# 确保 src 在 sys.path（支持 uv run python main.py）
_src = str(Path(__file__).resolve().parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import typer  # noqa: E402

app = typer.Typer(help="AI Chat — 本地 AI 工作台", no_args_is_help=True)


# ── serve ─────────────────────────────────────────────────────


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="监听地址"),
    port: int = typer.Option(8000, "--port", help="监听端口"),
    reload: bool = typer.Option(False, "--reload", help="启用热重载"),
) -> None:
    """启动 FastAPI 服务。"""
    import uvicorn

    uvicorn.run("src.ai.api:app", host=host, port=port, reload=reload)


# ── chat ──────────────────────────────────────────────────────


@app.command()
def chat(
    session: str = typer.Option("cli-chat", "--session", help="会话 ID"),
) -> None:
    """交互式对话（记忆 + 工具调用）。"""
    asyncio.run(_chat_loop(session))


@app.command()
def agent(
    task: str = typer.Argument(..., help="任务描述"),
    session: str = typer.Option("agent-session", "--session", "-s", help="会话 ID"),
    max_iterations: int = typer.Option(10, "--max-iterations", "-m", help="最大迭代次数"),
) -> None:
    """Agent 模式 — 自主任务执行。"""
    asyncio.run(_agent_run(task, session, max_iterations))


async def _chat_loop(session_id: str) -> None:
    """异步交互式对话主循环。"""
    from src.ai.core.container import container

    # 从 DI 容器获取服务
    memory_svc = container.memory_container.memory_service()
    context_svc = container.context_container.context_service()
    chat_llm = container.chat_llm()
    chat_cfg = container.chat_model_config()
    tool_mgr = container.tool_container.tool_manager()
    skill_svc = container.skill_container.skill_service()

    typer.echo("=" * 50)
    typer.echo("AI Chat — 交互式对话")
    typer.echo("=" * 50)
    typer.echo("输入消息开始对话，/help 查看命令列表，/quit 退出\n")

    typer.echo(f"  模型: {chat_cfg.model_key} ({chat_cfg.backend})")

    # 加载工具和技能
    tools = tool_mgr.list_tools(enabled_only=True)
    skills = skill_svc.list_user_invocable()
    typer.echo(f"  工具: {len(tools)} 个可用")
    typer.echo(f"  技能: {len(skills)} 个可用\n")

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo("\n再见！")
            break

        if not user_input:
            continue

        # 斜杠命令分发
        if user_input.startswith("/"):
            try:
                skill_text = _dispatch_command(
                    user_input, session_id, memory_svc, skill_svc
                )
            except _QuitSignal:
                break
            if skill_text is None:
                continue
            user_input = skill_text

        # 对话（普通消息或技能渲染后的文本）
        try:
            reply = await _chat_once(
                chat_llm,
                user_input,
                tools,
                session_id,
                context_svc,
                chat_cfg,
                tool_mgr,
                memory_svc,
            )
            typer.echo(f"\n助手: {reply}\n")

            # 提取记忆
            candidates = await memory_svc.aextract_from_conversation(user_input, reply)
            if candidates:
                saved = memory_svc.save_extracted(candidates, session_id=session_id)
                if saved > 0:
                    typer.echo(f"  保存了 {saved} 条新记忆")
        except Exception as e:
            typer.echo(f"\n调用失败: {e}", err=True)


async def _agent_run(task: str, session_id: str, max_iterations: int) -> None:
    """Agent 模式执行。"""
    from src.ai.core.container import container

    # 从 DI 容器获取 Agent 编排器
    agent_orchestrator = container.agent_container.agent_orchestrator()

    typer.echo("=" * 50)
    typer.echo("AI Agent — 自主任务执行")
    typer.echo("=" * 50)
    typer.echo(f"任务: {task}")
    typer.echo(f"会话: {session_id}")
    typer.echo(f"最大迭代: {max_iterations}")
    typer.echo("=" * 50)
    typer.echo()

    try:
        result = await agent_orchestrator.run(
            session_id=session_id,
            user_message=task,
            max_iterations=max_iterations,
        )

        typer.echo(f"\n{'=' * 50}")
        typer.echo(f"执行完成: {result.status.value}")
        typer.echo(f"迭代次数: {result.iterations}")
        typer.echo(f"工具调用: {len(result.tool_calls)} 次")
        typer.echo(f"{'=' * 50}")
        typer.echo(f"\n结果:\n{result.content}")

        if result.tool_calls:
            typer.echo("\n工具调用记录:")
            for tc in result.tool_calls:
                status = "[OK]" if tc.error is None else "[X]"
                typer.echo(f"  {status} {tc.name} ({tc.duration_ms}ms)")
                if tc.error:
                    typer.echo(f"    错误: {tc.error}")

    except Exception as e:
        typer.echo(f"\n执行失败: {e}", err=True)


# ── 斜杠命令分发 ────────────────────────────────────────────


class _QuitSignal(Exception):
    """用于 /quit 命令跳出对话循环的信号异常。"""


def _dispatch_command(
    user_input: str,
    session_id: str,
    memory_svc,
    skill_svc,
) -> str | None:
    """分发斜杠命令。

    三级优先级：内置命令 → 技能命令 → 未知命令提示。

    Args:
        user_input: 用户原始输入（以 / 开头）。
        session_id: 当前会话 ID。
        memory_svc: 记忆服务实例。
        skill_svc: 技能服务实例。

    Returns:
        - None: 内置命令已处理，调用方应 continue。
        - str: 技能激活后的模板文本，调用方应将其作为 user_input 传给 _chat_once。

    Raises:
        _QuitSignal: 用户输入 /quit，调用方应 break。
    """
    cmd = user_input.lower().strip()
    parts = cmd.split(None, 1)
    name = parts[0]  # 如 /help、/memory、/translate
    args = parts[1] if len(parts) > 1 else ""

    # 内置命令
    if name == "/quit":
        typer.echo("\n再见！")
        raise _QuitSignal

    if name == "/help":
        _cmd_help(skill_svc)
        return None

    if name == "/skills":
        _cmd_skills(skill_svc)
        return None

    if name == "/memory":
        _cmd_memory(args, memory_svc)
        return None

    if name == "/stats":
        _cmd_stats(session_id, memory_svc)
        return None

    if name == "/clear":
        _cmd_clear(session_id, memory_svc)
        return None

    # 技能斜杠命令匹配
    matched = skill_svc.match_slash_command(user_input)
    if matched is not None:
        # 提取参数（/translate hello world → arguments="hello world"）
        raw_parts = user_input.strip().split(None, 1)
        arguments = raw_parts[1] if len(raw_parts) > 1 else ""
        rendered = skill_svc.activate(matched.name, arguments=arguments)
        typer.echo(f"  > 技能: {matched.name}")
        return rendered

    # 未匹配任何命令
    typer.echo(f"  未知命令: {name}")
    typer.echo("  输入 /help 查看可用命令")
    return None


def _cmd_help(skill_svc) -> None:
    """显示帮助信息（内置命令 + 技能命令）。"""
    typer.echo("\n内置命令:")
    typer.echo("  /help              显示此帮助")
    typer.echo("  /quit              退出对话")
    typer.echo("  /memory            查看记忆列表")
    typer.echo("  /memory search Q   搜索记忆")
    typer.echo("  /memory rebuild    重建记忆索引")
    typer.echo("  /skills            列出可用技能")
    typer.echo("  /stats             显示统计")
    typer.echo("  /clear             清空当前会话")

    slash_cmds = skill_svc.get_slash_commands()
    if slash_cmds:
        typer.echo("\n技能命令:")
        for cmd in slash_cmds:
            typer.echo(f"  {cmd['command']:<20s} {cmd['description']}")
    typer.echo()


def _cmd_skills(skill_svc) -> None:
    """列出所有用户可调用的技能。"""
    skills = skill_svc.list_user_invocable()
    if not skills:
        typer.echo("  没有可用技能")
        return
    for s in skills:
        hint = f"  {s.argument_hint}" if s.argument_hint else ""
        typer.echo(f"  /{s.name}{hint}")
        typer.echo(f"    {s.description}")
    typer.echo()


def _cmd_memory(args: str, memory_svc) -> None:
    """处理 /memory 命令及其子命令。"""
    if not args:
        # /memory — 列出记忆
        entries = memory_svc.list_entries()
        if not entries:
            typer.echo("  暂无记忆")
            return
        for entry in entries:
            typer.echo(f"  [{entry.memory_type}] {entry.name}")
            typer.echo(f"    {entry.description[:60]}")
        return

    # 子命令分发
    sub_parts = args.strip().split(None, 1)
    sub_cmd = sub_parts[0].lower()

    if sub_cmd == "search" and len(sub_parts) > 1:
        query = sub_parts[1]
        results = memory_svc.search(query)
        if not results:
            typer.echo(f"  未找到与 \"{query}\" 相关的记忆")
            return
        for r in results:
            typer.echo(
                f"  [{r.entry.memory_type}] {r.entry.name} (相关度: {r.score:.2f})"
            )
            typer.echo(f"    {r.entry.description[:60]}")
        return

    if sub_cmd == "rebuild":
        memory_svc.rebuild_index()
        typer.echo("  记忆索引已重建")
        return

    # 未知子命令
    typer.echo(f"  未知子命令: /memory {sub_cmd}")
    typer.echo("  可用: /memory, /memory search Q, /memory rebuild")


def _cmd_stats(session_id: str, memory_svc) -> None:
    """显示会话统计信息。"""
    from src.ai.utils.token_utils import token_counter

    stats = memory_svc.get_stats()
    from src.ai.core.container import container as _c

    history_mgr = _c.context_container.chat_history_manager()
    messages = history_mgr.get_messages(session_id)
    token_usage = token_counter.estimate_messages_tokens(messages)
    typer.echo(f"  记忆: {stats.get('total', 0)} 条")
    typer.echo(f"  消息: {len(messages)} 条")
    typer.echo(f"  Token: ~{token_usage}")


def _cmd_clear(session_id: str, memory_svc) -> None:
    """清空当前会话的对话历史。"""
    from src.ai.core.container import container as _c

    history_mgr = _c.context_container.chat_history_manager()
    history_mgr.clear_history(session_id)
    typer.echo(f"  会话 {session_id} 的历史已清空")


async def _chat_once(
    llm,
    user_input: str,
    tools: list,
    session_id: str,
    context_svc,
    chat_cfg,
    tool_mgr,
    memory_svc,
) -> str:
    """单轮对话：上下文构建 → LLM → 工具循环 → 保存历史。"""
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    from src.ai.core.context import ContextBuildRequest

    # 构建上下文
    request = ContextBuildRequest(
        messages=[HumanMessage(content=user_input)],
        model_config=chat_cfg,
        session_id=session_id,
        enable_memory=True,
        enable_tools=True,
        enable_rag=False,
    )
    result = await context_svc.abuild(request)

    # 绑定工具并调用 LLM
    llm_with_tools = llm.bind_tools(tools)
    response: AIMessage = await llm_with_tools.ainvoke(result.messages)

    # 工具调用循环（累积消息，保留所有轮次的 AI + Tool 消息）
    messages = list(result.messages)
    max_rounds = 10
    round_count = 0
    while response.tool_calls and round_count < max_rounds:
        round_count += 1
        messages.append(response)

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]
            typer.echo(f"  调用工具: {tool_name}")

            try:
                tool_result = await tool_mgr.execute(tool_name, tool_args)
                result_str = (
                    tool_result
                    if isinstance(tool_result, str)
                    else json.dumps(tool_result, ensure_ascii=False, default=str)
                )
                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "\n...(已截断)"
            except Exception as e:
                result_str = f"工具执行失败: {e}"

            messages.append(ToolMessage(content=result_str, tool_call_id=tool_id))

        response = await llm_with_tools.ainvoke(messages)

    # 保存历史
    from src.ai.core.container import container as _c

    history_mgr = _c.context_container.chat_history_manager()
    history_mgr.add_message(session_id, HumanMessage(content=user_input))
    history_mgr.add_message(session_id, response)

    return response.content


# ── dashboard ─────────────────────────────────────────────────


@app.command()
def dashboard() -> None:
    """启动 TUI 控制台仪表盘。"""
    from src.ai.cli.dashboard import Dashboard
    from src.ai.cli.sessions import SessionManager
    from src.ai.core.container import container

    history_mgr = container.context_container.chat_history_manager()
    session_mgr = SessionManager(history_mgr)

    dash = Dashboard(session_mgr)
    dash.run()


# ── manage 子命令组 ───────────────────────────────────────────

from src.ai.cli.commands import manage_app  # noqa: E402

app.add_typer(manage_app, name="manage")


# ── generate-key ──────────────────────────────────────────────

from src.ai.cli import app as _cli_app  # noqa: E402

app.registered_commands.extend(_cli_app.registered_commands)

# ── 入口 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
