"""API response models using Pydantic."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field with error (if applicable)")


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = Field(False, description="Always false for errors")
    error: ErrorDetail = Field(..., description="Error details")
    trace_id: Optional[str] = Field(None, description="Trace ID for debugging")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(..., description="Current server time")
    components: Dict[str, str] = Field(
        default_factory=dict, description="Component health statuses"
    )


class SessionResponse(BaseModel):
    """Session information response."""

    id: str = Field(..., description="Session ID")
    name: Optional[str] = Field(None, description="Session name")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")


class RunResponse(BaseModel):
    """Agent run response."""

    run_id: str = Field(..., description="Unique run ID")
    status: str = Field(..., description="Run status (started, running, completed, failed)")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    created_at: datetime = Field(..., description="Run creation time")


class ToolResponse(BaseModel):
    """Tool execution response."""

    success: bool = Field(..., description="Whether tool executed successfully")
    output: str = Field(..., description="Tool output")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
