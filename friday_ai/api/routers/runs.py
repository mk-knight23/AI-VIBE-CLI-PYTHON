"""Agent run endpoints."""

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from friday_ai.api.dependencies import (
    check_rate_limit,
    get_current_user,
    get_redis_backend,
)
from friday_ai.api.models.requests import RunRequest
from friday_ai.api.models.responses import ErrorResponse, RunResponse
from friday_ai.database.redis_backend import RedisSessionBackend
from friday_ai.utils.errors import SessionNotFoundError, AuthorizationError, ValidationError

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory store for active runs (will be Redis in production)
_active_runs: dict[str, dict] = {}
# Lock to protect concurrent access to _active_runs
_active_runs_lock = asyncio.Lock()

# Configuration for run cleanup
_RUN_TTL_SECONDS = 3600  # Keep completed runs for 1 hour
_CLEANUP_INTERVAL_SECONDS = 300  # Check every 5 minutes

# Task registry for background tasks with proper error handling (FIX-016)
_background_tasks: dict[str, asyncio.Task] = {}
_task_lock = asyncio.Lock()


async def _cleanup_old_runs():
    """Background task to clean up completed/failed runs older than TTL."""
    while True:
        try:
            await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)

            cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=_RUN_TTL_SECONDS)
            runs_to_remove = []

            async with _active_runs_lock:
                for run_id, run in _active_runs.items():
                    # Only cleanup completed or failed runs
                    if run["status"] in ("completed", "failed"):
                        created_at = datetime.fromisoformat(run["created_at"])
                        if created_at < cutoff_time:
                            runs_to_remove.append(run_id)

                for run_id in runs_to_remove:
                    del _active_runs[run_id]

            if runs_to_remove:
                logger.info(f"Cleaned up {len(runs_to_remove)} old runs")
        except Exception as e:
            logger.error(f"Error in run cleanup: {e}")


async def _remove_run(run_id: str):
    """Remove a run from active runs (thread-safe)."""
    async with _active_runs_lock:
        if run_id in _active_runs:
            del _active_runs[run_id]


def _handle_task_done(run_id: str, task: asyncio.Task) -> None:
    """Callback when background task completes (FIX-016).

    Logs any exceptions that occurred during task execution.
    This is called from the event loop when the task finishes.
    """
    try:
        # Check if task raised an exception
        exception = task.exception()
        if exception:
            logger.error(
                f"Background task {run_id} failed with exception: {exception}",
                exc_info=exception,
            )
    except asyncio.CancelledError:
        logger.info(f"Background task {run_id} was cancelled")
    except Exception as e:
        logger.error(f"Error in task done callback for {run_id}: {e}")


# Start cleanup task on module load
# _cleanup_task = asyncio.create_task(_cleanup_old_runs())
_cleanup_task = None  # TODO: Start this in app lifespan


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
            raise SessionNotFoundError(session_id=request.session_id)

    # Create run record (protected by lock for thread safety)
    async with _active_runs_lock:
        _active_runs[run_id] = {
            "id": run_id,
            "user_id": user.id,
            "prompt": request.prompt,
            "session_id": request.session_id,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "events": [],
        }

    # Start run in background with task registry and error handling (FIX-016)
    task = asyncio.create_task(_execute_run(run_id, request.prompt))

    # Add done callback to catch any unhandled exceptions
    task.add_done_callback(lambda t: _handle_task_done(run_id, task))

    # Register task in the global registry
    async with _task_lock:
        _background_tasks[run_id] = task

    logger.info(f"Created run {run_id} for user {user.id}")

    return RunResponse(
        run_id=run_id,
        status="queued",
        session_id=request.session_id,
        created_at=datetime.now(timezone.utc),
    )


async def _execute_run(run_id: str, prompt: str):
    """Background task to execute agent run."""
    try:
        async with _active_runs_lock:
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
            async with _active_runs_lock:
                run = _active_runs.get(run_id)
                if run:
                    run["events"].append(event)

        async with _active_runs_lock:
            run = _active_runs.get(run_id)
            if run:
                run["status"] = "completed"
    except Exception as e:
        # Handle errors and mark run as failed
        logger.error(f"Error executing run {run_id}: {e}")
        async with _active_runs_lock:
            run = _active_runs.get(run_id)
            if run:
                run["status"] = "failed"
                run["events"].append({"type": "error", "message": f"Run failed: {str(e)}"})
    finally:
        # Schedule cleanup after TTL to allow clients to fetch final status
        await asyncio.sleep(_RUN_TTL_SECONDS)
        await _remove_run(run_id)


@router.get(
    "/{run_id}/stream",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def stream_run(
    run_id: str,
    request: Request,
    user=Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """Stream run events via Server-Sent Events (SSE).

    Connect to this endpoint to receive real-time updates
    about the agent run progress.
    """
    async with _active_runs_lock:
        run = _active_runs.get(run_id)

    if not run:
        raise ValidationError(
            message="Run not found or has expired",
            field="run_id",
            value=run_id,
        )

    if run["user_id"] != user.id:
        raise AuthorizationError(
            message="Access denied to run",
            resource="run",
            action="read",
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events."""
        last_index = 0

        while True:
            async with _active_runs_lock:
                run = _active_runs.get(run_id)
                if not run:
                    yield "event: error\ndata: Run not found\n\n"
                    break

                # Copy data to avoid holding lock during yield
                run_status = run["status"]
                run_events = run["events"].copy()

            # Send new events (outside lock to avoid blocking other coroutines)
            while last_index < len(run_events):
                event = run_events[last_index]
                yield f"event: {event.get('type', 'message')}\n"
                yield f"data: {str(event)}\n\n"
                last_index += 1

            # Check if run is complete
            if run_status in ("completed", "failed"):
                yield f"event: done\ndata: {run_status}\n\n"
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
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def get_run_status(
    run_id: str,
    user=Depends(get_current_user),
    _: None = Depends(check_rate_limit),
):
    """Get current status and events for a run."""
    async with _active_runs_lock:
        run = _active_runs.get(run_id)

    if not run:
        raise ValidationError(
            message="Run not found or has expired",
            field="run_id",
            value=run_id,
        )

    if run["user_id"] != user.id:
        raise AuthorizationError(
            message="Access denied to run",
            resource="run",
            action="read",
        )

    return {
        "run_id": run_id,
        "status": run["status"],
        "events": run["events"],
        "created_at": run["created_at"],
    }
