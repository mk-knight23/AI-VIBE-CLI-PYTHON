"""Session management endpoints."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, status

from friday_ai.api.dependencies import (
    check_rate_limit,
    get_current_user,
    get_redis_backend,
)
from friday_ai.api.exceptions import APIError
from friday_ai.api.models.requests import SessionCreateRequest
from friday_ai.api.models.responses import ErrorResponse, SessionResponse
from friday_ai.api.services.session_service import SessionService
from friday_ai.database.redis_backend import RedisSessionBackend
from friday_ai.utils.errors import AuthenticationError, AuthorizationError, SessionNotFoundError

router = APIRouter()


def get_session_service(
    redis: RedisSessionBackend = Depends(get_redis_backend),
) -> SessionService:
    return SessionService(redis)


@router.post(
    "/",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
async def create_session(
    request: SessionCreateRequest,
    user=Depends(get_current_user),
    _: None = Depends(check_rate_limit),
    service: SessionService = Depends(get_session_service),
):
    """Create a new session.

    Sessions persist conversation context across multiple requests.
    Sessions expire after 24 hours of inactivity by default.
    """
    session = await service.create_session(
        user_id=user.id,
        name=request.name,
        metadata=request.metadata,
    )

    return SessionResponse(
        id=session.id,
        name=session.name,
        created_at=session.created_at,
        updated_at=session.updated_at,
        metadata=session.metadata,
    )


@router.get(
    "/",
    response_model=List[SessionResponse],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
)
async def list_sessions(
    user=Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
):
    """List all active sessions for the current user."""
    sessions = await service.list_user_sessions(user.id)

    return [
        SessionResponse(
            id=s.id,
            name=s.name,
            created_at=s.created_at,
            updated_at=s.updated_at,
            metadata=s.metadata,
        )
        for s in sessions
    ]


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
async def get_session(
    session_id: str,
    user=Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
):
    """Get a specific session by ID."""
    session = await service.get_session(session_id)

    if not session:
        raise SessionNotFoundError(session_id=session_id)

    # Verify ownership
    if session.user_id != user.id:
        raise AuthorizationError(
            message="Access denied to session",
            resource="session",
            action="read",
        )

    return SessionResponse(
        id=session.id,
        name=session.name,
        created_at=session.created_at,
        updated_at=session.updated_at,
        metadata=session.metadata,
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
async def delete_session(
    session_id: str,
    user=Depends(get_current_user),
    service: SessionService = Depends(get_session_service),
):
    """Delete a session and all associated data."""
    session = await service.get_session(session_id)

    if not session:
        raise SessionNotFoundError(session_id=session_id)

    if session.user_id != user.id:
        raise AuthorizationError(
            message="Access denied to session",
            resource="session",
            action="delete",
        )

    await service.delete_session(session_id)
    return None
