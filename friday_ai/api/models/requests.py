"""API request models using Pydantic."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class SessionCreateRequest(BaseModel):
    """Request to create a new session."""

    name: Optional[str] = Field(None, description="Optional session name")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata"
    )


class RunRequest(BaseModel):
    """Request to start an agent run."""

    prompt: str = Field(..., min_length=1, max_length=100000, description="User prompt")
    session_id: Optional[str] = Field(None, description="Session ID (optional)")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Run configuration"
    )

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Prompt cannot be empty or whitespace only")
        return v


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool."""

    tool_name: str = Field(..., description="Name of the tool to execute")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Tool parameters"
    )
    session_id: Optional[str] = Field(None, description="Associated session ID")
