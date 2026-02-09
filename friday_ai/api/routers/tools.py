"""Tool execution endpoints."""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status

from friday_ai.api.dependencies import (
    check_rate_limit,
    get_current_user,
)
from friday_ai.api.models.requests import ToolExecuteRequest
from friday_ai.api.models.responses import ErrorResponse, ToolResponse
from friday_ai.config.config import Config
from friday_ai.tools.base import ToolInvocation
from friday_ai.tools.registry import ToolRegistry

router = APIRouter()


def get_tool_registry() -> ToolRegistry:
    """Get or create tool registry singleton."""
    if not hasattr(get_tool_registry, "_registry"):
        config = Config()
        get_tool_registry._registry = ToolRegistry(config)
    return get_tool_registry._registry


@router.get("/", response_model=list[str])
async def list_tools(
    user=Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """List all available tools."""
    registry = get_tool_registry()
    return list(registry._tools.keys())


@router.post(
    "/{tool_name}",
    response_model=ToolResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Tool not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def execute_tool(
    tool_name: str,
    request: ToolExecuteRequest,
    user=Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """Execute a tool with the provided parameters."""
    registry = get_tool_registry()

    # Check if tool exists
    if tool_name not in registry._tools:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}",
        )

    # Execute tool
    start_time = datetime.utcnow()
    try:
        invocation = ToolInvocation(
            params=request.params,
            cwd="/tmp",  # TODO: Get from session or config
        )

        result = await registry.execute(tool_name, invocation)

        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return ToolResponse(
            success=result.success,
            output=result.output,
            error=result.error,
            execution_time_ms=execution_time,
        )

    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        return ToolResponse(
            success=False,
            output="",
            error=str(e),
            execution_time_ms=execution_time,
        )


@router.get("/{tool_name}/schema", response_model=Dict[str, Any])
async def get_tool_schema(
    tool_name: str,
    user=Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """Get the JSON schema for a tool's parameters."""
    registry = get_tool_registry()

    tool = registry._tools.get(tool_name)
    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool not found: {tool_name}",
        )

    return tool.schema if hasattr(tool, "schema") else {}
