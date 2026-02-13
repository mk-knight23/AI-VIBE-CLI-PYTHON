"""Streaming response support for Friday AI.

Provides real-time token streaming, progress indicators,
and cancellation support for long-running operations.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Callable

from friday_ai.agent.events import AgentEvent

logger = logging.getLogger(__name__)


class StreamEventType(Enum):
    """Types of stream events."""
    TOKEN = "token"
    PROGRESS = "progress"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


@dataclass
class StreamEvent:
    """An event in the response stream."""

    type: StreamEventType
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class StreamProgress:
    """Progress tracking for streaming responses."""

    def __init__(self, total: int | None = None):
        """Initialize progress tracker.

        Args:
            total: Total units (tokens, steps, etc.) if known.
        """
        self.total = total
        self.current = 0
        self.percentage = 0.0
        self.eta_seconds: float | None = None
        self.started_at = datetime.now(timezone.utc)

    def update(self, increment: int = 1) -> None:
        """Update progress.

        Args:
            increment: Amount to increment by.
        """
        self.current += increment

        if self.total:
            self.percentage = (self.current / self.total) * 100

        # Calculate ETA
        if self.total and self.current > 0:
            elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
            rate = self.current / elapsed
            if rate > 0:
                self.eta_seconds = (self.total - self.current) / rate

    def is_complete(self) -> bool:
        """Check if progress is complete."""
        return self.total is not None and self.current >= self.total


class StreamingResponse:
    """Streaming response with progress tracking."""

    def __init__(
        self,
        request_id: str,
        on_event: Callable[[StreamEvent], None] | None = None,
    ):
        """Initialize streaming response.

        Args:
            request_id: Unique identifier for this response.
            on_event: Optional callback for stream events.
        """
        self.request_id = request_id
        self.on_event = on_event
        self._events: list[StreamEvent] = []
        self._is_complete = False
        self._is_cancelled = False
        self._progress = StreamProgress()

    async def stream_tokens(
        self,
        token_generator: AsyncGenerator[str, None],
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream tokens from a generator.

        Args:
            token_generator: Async generator yielding tokens.

        Yields:
            StreamEvent for each token.
        """
        try:
            async for token in token_generator:
                if self._is_cancelled:
                    yield StreamEvent(
                        type=StreamEventType.CANCELLED,
                        content="",
                        metadata={"reason": "User cancelled"},
                    )
                    break

                event = StreamEvent(
                    type=StreamEventType.TOKEN,
                    content=token,
                )

                self._events.append(event)
                self._progress.update(increment=len(token))

                if self.on_event:
                    self.on_event(event)

                yield event

        except Exception as e:
            logger.exception(f"Error streaming tokens: {e}")
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content=str(e),
            )

        finally:
            if not self._is_cancelled:
                yield StreamEvent(
                    type=StreamEventType.COMPLETE,
                    content="",
                    metadata={
                        "total_tokens": self._progress.current,
                        "duration": (datetime.now(timezone.utc) - self._progress.started_at).total_seconds(),
                    },
                )

    async def stream_with_progress(
        self,
        coro: Any,
        total_steps: int | None = None,
        step_description: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream a coroutine with progress updates.

        Args:
            coro: The coroutine to execute.
            total_steps: Total number of steps if known.
            step_description: Description of current step.

        Yields:
            StreamEvent for progress updates.
        """
        self._progress = StreamProgress(total=total_steps)

        yield StreamEvent(
            type=StreamEventType.PROGRESS,
            content="Starting",
            metadata={
                "progress": 0,
                "total": total_steps,
            },
        )

        try:
            result = await coro

            yield StreamEvent(
                type=StreamEventType.COMPLETE,
                content="",
                metadata={"result": str(result)},
            )

        except Exception as e:
            logger.exception(f"Error in streaming coroutine: {e}")
            yield StreamEvent(
                type=StreamEventType.ERROR,
                content=str(e),
            )

    def cancel(self) -> None:
        """Cancel the stream."""
        self._is_cancelled = True
        logger.info(f"Stream {self.request_id} cancelled")

    def is_complete(self) -> bool:
        """Check if stream is complete."""
        return self._is_complete

    def is_cancelled(self) -> bool:
        """Check if stream was cancelled."""
        return self._is_cancelled

    def get_events(self) -> list[StreamEvent]:
        """Get all stream events.

        Returns:
            List of events.
        """
        return self._events.copy()

    def get_progress(self) -> StreamProgress:
        """Get current progress.

        Returns:
            Progress tracker.
        """
        return self._progress


class StreamManager:
    """Manages multiple streaming responses."""

    def __init__(self):
        """Initialize the stream manager."""
        self._streams: dict[str, StreamingResponse] = {}

    def create_stream(
        self,
        request_id: str,
        on_event: Callable[[StreamEvent], None] | None = None,
    ) -> StreamingResponse:
        """Create a new streaming response.

        Args:
            request_id: Unique identifier for the stream.
            on_event: Optional callback for stream events.

        Returns:
            StreamingResponse instance.
        """
        stream = StreamingResponse(request_id, on_event)
        self._streams[request_id] = stream
        return stream

    def get_stream(self, request_id: str) -> StreamingResponse | None:
        """Get an existing stream.

        Args:
            request_id: Stream identifier.

        Returns:
            StreamingResponse or None if not found.
        """
        return self._streams.get(request_id)

    def cancel_stream(self, request_id: str) -> bool:
        """Cancel a stream.

        Args:
            request_id: Stream identifier.

        Returns:
            True if stream was cancelled, False if not found.
        """
        stream = self._streams.get(request_id)
        if stream:
            stream.cancel()
            return True
        return False

    def list_streams(self) -> list[str]:
        """List all active stream IDs.

        Returns:
            List of stream IDs.
        """
        return list(self._streams.keys())

    def remove_stream(self, request_id: str) -> None:
        """Remove a completed stream.

        Args:
            request_id: Stream identifier.
        """
        if request_id in self._streams:
            del self._streams[request_id]


async def stream_agent_response(
    agent,
    prompt: str,
    stream_manager: StreamManager,
    request_id: str,
) -> AsyncGenerator[StreamEvent, None]:
    """Stream an agent's response token by token.

    Args:
        agent: The Friday agent.
        prompt: The prompt to send.
        stream_manager: Stream manager for tracking.
        request_id: Unique request identifier.

    Yields:
        StreamEvent for each token and status update.
    """
    stream = stream_manager.create_stream(request_id)

    # Progress event
    yield StreamEvent(
        type=StreamEventType.PROGRESS,
        content="Generating response",
        metadata={"progress": 0},
    )

    try:
        # Get response from agent
        # Note: This is a simplified version
        # Full implementation would require token-level streaming from the LLM client
        response = await agent.run(prompt)

        # Simulate token streaming (in reality, tokens would stream from LLM)
        tokens = response.split()
        for i, token in enumerate(tokens):
            if stream.is_cancelled():
                break

            yield StreamEvent(
                type=StreamEventType.TOKEN,
                content=token + " ",  # Add space back
                metadata={"token_index": i},
            )

        yield StreamEvent(
            type=StreamEventType.COMPLETE,
            content="",
            metadata={"total_tokens": len(tokens)},
        )

    except Exception as e:
        logger.exception(f"Error streaming agent response: {e}")
        yield StreamEvent(
            type=StreamEventType.ERROR,
            content=str(e),
        )

    finally:
        stream_manager.remove_stream(request_id)
