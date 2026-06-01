"""Agent 路由。"""

from fastapi import APIRouter

from src.ai.api.deps import AgentOrchestratorDep
from src.ai.api.schemas.agent import (
    AgentRunRequest,
    AgentRunResponse,
    ToolCallResponse,
)
from src.ai.api.services.agent_service import AgentService

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    request: AgentRunRequest,
    orchestrator: AgentOrchestratorDep,
):
    """执行 Agent 任务。

    运行 ReAct 循环，自动推理和执行工具直到任务完成。

    Args:
        request: 执行请求。
    """
    service = AgentService(orchestrator=orchestrator)

    result = await service.run(
        session_id=request.session_id,
        user_message=request.user_message,
        system_prompt=request.system_prompt,
        max_iterations=request.max_iterations,
        tools=request.tools,
    )

    return AgentRunResponse(
        status=result["status"],
        content=result["content"],
        tool_calls=[
            ToolCallResponse(
                id=tc["id"],
                name=tc["name"],
                arguments=tc["arguments"],
                result=tc.get("result"),
                error=tc.get("error"),
                duration_ms=tc.get("duration_ms", 0),
            )
            for tc in result.get("tool_calls", [])
        ],
        iterations=result["iterations"],
        total_tokens=result["total_tokens"],
        plan=result.get("plan"),
    )
