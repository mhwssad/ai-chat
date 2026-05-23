"""工具路由。"""

from __future__ import annotations

from fastapi import APIRouter

from src.ai.api.schemas.tools import ToolCallRequestIn, ToolCallResponse, ToolResponse
from src.ai.api.services.tool_service import ToolService
from src.ai.core.tools import ToolCallRequest

router = APIRouter()


@router.get("", response_model=list[ToolResponse])
async def list_tools(enabled_only: bool = False):
    tools = ToolService().list_tools(enabled_only=enabled_only)
    return [
        ToolResponse(
            name=tool.name,
            description=tool.description,
            source_type=tool.source_type,
            source_id=tool.source_id,
            enabled=tool.enabled,
            status=tool.status,
            permissions=tool.permissions,
            input_schema=tool.input_schema,
        )
        for tool in tools
    ]


@router.post("/call", response_model=ToolCallResponse)
async def call_tool(payload: ToolCallRequestIn):
    result = await ToolService().call_tool(
        ToolCallRequest(
            tool_name=payload.tool_name,
            arguments=payload.arguments,
            session_id=payload.session_id,
            message_id=payload.message_id,
            metadata=payload.metadata,
        )
    )
    return ToolCallResponse(
        tool_name=result.tool_name,
        content=result.content,
        structured_content=result.structured_content,
        is_error=result.is_error,
        raw=result.raw,
    )

