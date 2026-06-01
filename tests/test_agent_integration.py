"""Agent 集成测试 — 使用 Mock 测试完整 LangGraph 流程。"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 确保 src 在 sys.path
_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from langchain_core.tools import BaseTool

from src.ai.core.agent.orchestrator import AgentOrchestrator
from src.ai.core.agent.types import AgentResult, AgentStatus


def _create_mock_tool(name: str, return_value: str = "ok") -> BaseTool:
    """创建可被 ToolNode 调用的 mock BaseTool。"""
    from pydantic import BaseModel, Field
    from langchain_core.tools import StructuredTool

    # 通用参数 schema
    class _Args(BaseModel):
        command: str = Field(default="", description="命令")

    async def _run(command: str = "", **kwargs) -> str:
        return return_value

    return StructuredTool.from_function(
        coroutine=_run,
        name=name,
        description=f"Mock tool: {name}",
        args_schema=_Args,
    )


def create_mock_orchestrator(tool_results: dict[str, str] | None = None):
    """创建 Mock 的 AgentOrchestrator。

    Args:
        tool_results: 工具名称 → 返回值映射，默认所有工具返回 "ok"。
    """
    model_service = MagicMock()
    tool_manager = MagicMock()
    context_service = MagicMock()
    tool_registry = MagicMock()

    # Mock ModelService
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.ainvoke = AsyncMock()
    model_service.get_chat_llm.return_value = mock_llm

    # Mock ToolRegistry — 返回 BaseTool 列表
    if tool_results is None:
        tool_results = {"bash": "ok"}
    mock_tools = [
        _create_mock_tool(name, result) for name, result in tool_results.items()
    ]
    tool_registry.list.return_value = mock_tools

    # Mock ToolManager（不再直接执行，但保留兼容）
    tool_manager.list_schemas.return_value = []

    # Mock ContextService
    context_service.abuild = AsyncMock()
    context_service.strategy = MagicMock()
    context_service.strategy.aadd_message = AsyncMock()

    return AgentOrchestrator(
        model_service=model_service,
        tool_manager=tool_manager,
        context_service=context_service,
        tool_registry=tool_registry,
    )


def _mock_context():
    """创建 mock 上下文结果。"""
    from src.ai.core.context.types import ContextBuildResult

    return ContextBuildResult(
        messages=[],
        system_message="系统提示",
        sections=[],
        budget_report={},
        total_input_tokens=100,
        budget_enabled=False,
        strategy_used="compression",
    )


@pytest.mark.asyncio
async def test_agent_simple_response():
    """测试 Agent 简单响应（无工具调用）。"""
    from langchain_core.messages import AIMessage

    orchestrator = create_mock_orchestrator()

    # Mock LLM 响应（无工具调用）
    mock_response = AIMessage(content="你好！有什么可以帮助你的吗？")
    orchestrator._model.get_chat_llm().ainvoke = AsyncMock(
        return_value=mock_response
    )
    orchestrator._model.get_chat_llm().bind_tools.return_value = (
        orchestrator._model.get_chat_llm()
    )

    # Mock 上下文构建
    orchestrator._context.abuild = AsyncMock(return_value=_mock_context())

    # 执行
    result = await orchestrator.run(
        session_id="test-session",
        user_message="你好",
        max_iterations=5,
    )

    # 验证
    assert result.status == AgentStatus.SUCCESS
    assert result.content == "你好！有什么可以帮助你的吗？"
    assert result.iterations == 1

    print("✓ test_agent_simple_response passed")


@pytest.mark.asyncio
async def test_agent_with_tool_call():
    """测试 Agent 工具调用流程。"""
    from langchain_core.messages import AIMessage

    # 创建 mock 工具，bash 工具返回 "file1.txt\nfile2.txt"
    orchestrator = create_mock_orchestrator(tool_results={"bash": "file1.txt\nfile2.txt"})

    # 第一次 LLM 响应：调用工具
    first_response = AIMessage(
        content="",
        tool_calls=[
            {"id": "call-1", "name": "bash", "args": {"command": "ls"}}
        ],
    )

    # 第二次 LLM 响应：返回结果
    second_response = AIMessage(content="当前目录有 2 个文件：file1.txt 和 file2.txt")

    # Mock LLM 调用顺序
    mock_llm = orchestrator._model.get_chat_llm()
    mock_llm.ainvoke = AsyncMock(
        side_effect=[first_response, second_response]
    )
    mock_llm.bind_tools.return_value = mock_llm

    # Mock 上下文构建
    orchestrator._context.abuild = AsyncMock(return_value=_mock_context())

    # 执行
    result = await orchestrator.run(
        session_id="test-session",
        user_message="列出当前目录的文件",
        max_iterations=5,
    )

    # 验证
    assert result.status == AgentStatus.SUCCESS
    assert "file1.txt" in result.content
    assert result.iterations == 2
    assert len(result.tool_calls) >= 1
    assert result.tool_calls[0].name == "bash"

    print("✓ test_agent_with_tool_call passed")


@pytest.mark.asyncio
async def test_agent_max_iterations():
    """测试 Agent 达到最大迭代次数。"""
    from langchain_core.messages import AIMessage

    orchestrator = create_mock_orchestrator()

    # LLM 总是返回工具调用
    def always_tool_call(*args, **kwargs):
        return AIMessage(
            content="",
            tool_calls=[
                {"id": "call-1", "name": "bash", "args": {"command": "ls"}}
            ],
        )

    mock_llm = orchestrator._model.get_chat_llm()
    mock_llm.ainvoke = AsyncMock(side_effect=always_tool_call)
    mock_llm.bind_tools.return_value = mock_llm

    # Mock 上下文构建
    orchestrator._context.abuild = AsyncMock(return_value=_mock_context())

    # 执行（最大迭代 3 次）
    result = await orchestrator.run(
        session_id="test-session",
        user_message="执行任务",
        max_iterations=3,
    )

    # 验证
    assert result.status == AgentStatus.MAX_ITERATIONS
    assert result.iterations == 3

    print("✓ test_agent_max_iterations passed")


@pytest.mark.asyncio
async def test_agent_tool_error():
    """测试 Agent 工具执行错误。"""
    from langchain_core.messages import AIMessage

    # 创建会抛出异常的 mock 工具
    from pydantic import BaseModel, Field
    from langchain_core.tools import StructuredTool

    class _Args(BaseModel):
        command: str = Field(default="", description="命令")

    async def _fail(command: str = "", **kwargs) -> str:
        raise Exception("命令无效")

    error_tool = StructuredTool.from_function(
        coroutine=_fail,
        name="bash",
        description="Mock tool: bash",
        args_schema=_Args,
    )

    # 创建 orchestrator，覆盖 tool_registry 返回
    orchestrator = create_mock_orchestrator()
    orchestrator._registry.list.return_value = [error_tool]

    # 第一次 LLM 响应：调用工具
    first_response = AIMessage(
        content="",
        tool_calls=[
            {"id": "call-1", "name": "bash", "args": {"command": "invalid"}}
        ],
    )

    # 第二次 LLM 响应：处理错误
    second_response = AIMessage(content="工具执行失败，命令无效。")

    mock_llm = orchestrator._model.get_chat_llm()
    mock_llm.ainvoke = AsyncMock(
        side_effect=[first_response, second_response]
    )
    mock_llm.bind_tools.return_value = mock_llm

    # Mock 上下文构建
    orchestrator._context.abuild = AsyncMock(return_value=_mock_context())

    # 执行
    result = await orchestrator.run(
        session_id="test-session",
        user_message="执行无效命令",
        max_iterations=5,
    )

    # 验证 — 工具错误被捕获并传递给 LLM
    assert result.status == AgentStatus.SUCCESS
    assert len(result.tool_calls) >= 1
    assert result.tool_calls[0].error is not None

    print("✓ test_agent_tool_error passed")


async def run_all_tests():
    """运行所有集成测试。"""
    print("Running Agent integration tests...")
    print()

    await test_agent_simple_response()
    await test_agent_with_tool_call()
    await test_agent_max_iterations()
    await test_agent_tool_error()

    print()
    print("All integration tests passed! ✓")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
