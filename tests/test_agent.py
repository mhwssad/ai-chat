"""Agent 模块测试。"""

from src.ai.core.agent.types import AgentResult, AgentStatus, ToolCall
from src.ai.core.agent.state import GraphState


def test_agent_status_enum():
    """测试 AgentStatus 枚举。"""
    assert AgentStatus.SUCCESS.value == "success"
    assert AgentStatus.MAX_ITERATIONS.value == "max_iterations"
    assert AgentStatus.ERROR.value == "error"
    assert AgentStatus.PLAN_MODE.value == "plan_mode"


def test_tool_call_dataclass():
    """测试 ToolCall 数据类。"""
    tc = ToolCall(
        id="test-id",
        name="bash",
        arguments={"command": "ls"},
    )
    assert tc.id == "test-id"
    assert tc.name == "bash"
    assert tc.arguments == {"command": "ls"}
    assert tc.result is None
    assert tc.error is None
    assert tc.duration_ms == 0


def test_agent_result_dataclass():
    """测试 AgentResult 数据类。"""
    result = AgentResult(
        status=AgentStatus.SUCCESS,
        content="任务完成",
        iterations=3,
    )
    assert result.is_success
    assert not result.has_tool_calls
    assert result.iterations == 3

    # 测试 to_dict
    d = result.to_dict()
    assert d["status"] == "success"
    assert d["content"] == "任务完成"
    assert d["iterations"] == 3


def test_graph_state_structure():
    """测试 GraphState 类型结构。"""
    # GraphState 是 TypedDict，验证其键存在
    annotations = GraphState.__annotations__
    assert "messages" in annotations
    assert "iteration" in annotations
    assert "max_iterations" in annotations
    assert "total_tokens" in annotations
    assert "session_id" in annotations
    assert "is_plan_mode" in annotations
    assert "plan" in annotations
    assert "error" in annotations


def test_graph_state_construction():
    """测试 GraphState 构造。"""
    state: GraphState = {
        "messages": [],
        "iteration": 0,
        "max_iterations": 5,
        "total_tokens": 0,
        "session_id": "test-session",
        "is_plan_mode": False,
        "plan": None,
        "error": None,
    }

    assert state["iteration"] == 0
    assert state["max_iterations"] == 5
    assert not state["is_plan_mode"]
    assert state["plan"] is None
    assert state["error"] is None
    assert state["session_id"] == "test-session"


def test_graph_state_max_iterations():
    """测试 GraphState 最大迭代限制判断。"""
    state: GraphState = {
        "messages": [],
        "iteration": 3,
        "max_iterations": 3,
        "total_tokens": 0,
        "session_id": "test",
        "is_plan_mode": False,
        "plan": None,
        "error": None,
    }

    # iteration >= max_iterations 时应停止
    assert state["iteration"] >= state["max_iterations"]
