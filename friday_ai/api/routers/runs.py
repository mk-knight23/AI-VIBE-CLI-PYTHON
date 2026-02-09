"""Agent run endpoints."""

import asyncio
import uuid
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from friday_ai.api.dependencies import (
    check_rate_limit,
    get_current_user,
    get_redis_backend,
)
from friday_ai.api.models.requests import RunRequest
from friday_ai.api.models.responses import ErrorResponse, RunResponse
from friday_ai.database.redis_backend import RedisSessionBackend

router = APIRouter()

# In-memory store for active runs (will be Redis in production)
_active_runs: dict[str, dict] = {}


@router.post(
    "/",
    response_model=RunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def create_run(
    request: RunRequest,
    user=Depends(get_current_user),
    _: None = Depends(check_rate_limit),
    redis: RedisSessionBackend = Depends(get_redis_backend),
):
    """Start a new agent run.

    Returns immediately with a run_id. Use the stream endpoint
    to receive real-time updates.
    """
    run_id = str(uuid.uuid4())

    # Validate session if provided
    if request.session_id:
        session = await redis.load(request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

    # Create run record
    _active_runs[run_id] = {
        "id": run_id,
        "user_id": user.id,
        "prompt": request.prompt,
        "session_id": request.session_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat(),
        "events": [],
    }

    # Start run in background (simplified for Phase 1)
    asyncio.create_task(_execute_run(run_id, request.prompt))

    return RunResponse(
        run_id=run_id,
        status="queued",
        session_id=request.session_id,
        created_at=datetime.utcnow(),
    )


async def _execute_run(run_id: str, prompt: str):
    """Background task to execute agent run."""
    run = _active_runs.get(run_id)
    if not run:
        return

    run["status"] = "running"

    # Simulate agent execution with events
    events = [
        {"type": "start", "message": "Starting agent execution"},
        {"type": "thinking", "message": f"Processing: {prompt[:100]}..."},
        {"type": "progress", "message": "Analyzing context...", "progress": 25},
        {"type": "progress", "message": "Generating response...", "progress": 50},
        {"type": "progress", "message": "Finalizing...", "progress": 75},
        {"type": "complete", "message": "Run completed", "progress": 100},
    ]

    for event in events:
        await asyncio.sleep(0.5)  # Simulate work
        run["events"].append(event)

    run["status"] = "completed"


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: str,
    request: Request,
    user=Depends(get_current_user),
):
    """Stream run events via Server-Sent Events (SSE).

    Connect to this endpoint to receive real-time updates
    about the agent run progress.
    """
    run = _active_runs.get(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    if run["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events."""
        last_index = 0

        while True:
            run = _active_runs.get(run_id)
            if not run:
                yield f"event: error\ndata: Run not found\n\n"
                break

            # Send new events
            while last_index < len(run["events"]):
                event = run["events"][last_index]
                yield f"event: {event.get('type', 'message')}\n"
                yield f"data: {str(event)}\n\n"
                last_index += 1

            # Check if run is complete
            if run["status"] in ("completed", "failed"):
                yield f"event: done\ndata: {run['status']}\n\n"
                break

            # Wait for new events
            await asyncio.sleep(0.1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/{run_id}",
    response_model=dict,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Run not found"},
    },
)
async def get_run_status(
    run_id: str,
    user=Depends(get_current_user),
):
    """Get current status and events for a run."""
    run = _active_runs.get(run_id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    if run["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return {
        "run_id": run_id,
        "status": run["status"],
        "events": run["events"],
        "created_at": run["created_at"],
    }
