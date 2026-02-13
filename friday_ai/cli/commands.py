"""Command handlers for Friday CLI.

Extracted from main.py to reduce file size and improve maintainability.
"""

import logging
from typing import Any

from rich.console import Console

from friday_ai.agent.persistence import PersistenceManager, SessionSnapshot
from friday_ai.agent.session import Session

logger = logging.getLogger(__name__)
console = Console()


async def handle_save(
    session: Session,
    args: dict[str, Any],
) -> None:
    """Save current session.

    Args:
        session: Active session
        args: Command arguments (not used)
    """
    try:
        persistence_manager = PersistenceManager()
        snapshot = SessionSnapshot(
            session_id=session.session_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
            turn_count=session.turn_count,
            messages=session.context_manager.get_messages(),
            total_usage=session.context_manager.total_usage,
        )
        await persistence_manager.save_session(snapshot)
        console.print(f"[success]Session saved: {session.session_id}[/success]")
    except Exception as e:
        console.print(f"[error]Failed to save session: {e}[/error]")


async def handle_sessions(session: Session, args: dict[str, Any]) -> None:
    """List saved sessions.

    Args:
        session: Active session
        args: Command arguments
    """
    try:
        persistence_manager = PersistenceManager()
        sessions = await persistence_manager.list_sessions()
        console.print("\n[bold]Saved Sessions[/bold]")
        if not sessions:
            console.print("  No saved sessions found")
        else:
            for i, s in enumerate(sessions, 1):
                console.print(f"  {i}. {s['session_id']} (turns: {s['turn_count']})")
    except Exception as e:
        console.print(f"[error]Failed to list sessions: {e}[/error]")


async def handle_resume(session: Session, args: dict[str, Any]) -> None:
    """Resume a saved session.

    Args:
        session: Active session
        args: Command arguments containing session_id
    """
    session_id = args.get("session_id")
    if not session_id:
        console.print("[error]Session ID required[/error]")
        return

    try:
        persistence_manager = PersistenceManager()
        snapshot = await persistence_manager.load_session(session_id)
        if not snapshot:
            console.print(f"[error]Session not found: {session_id}[/error]")
            return

        # Resume session state
        console.print(f"[success]Resuming session: {session_id}[/success]")

        config = session.config
        from friday_ai.agent.autonomous.circuit_breaker import CircuitBreakerControl

        # Initialize new session with resumed state
        session.agent.session_id = snapshot.session_id
        session.created_at = snapshot.created_at
        session.updated_at = snapshot.updated_at
        session.turn_count = snapshot.turn_count
        session.context_manager.total_usage = snapshot.total_usage
        session.context_manager.clear_messages()
        for msg in snapshot.messages:
            if msg.get("role") == "system":
                continue
            elif msg.get("role") == "user":
                session.context_manager.add_user_message(msg.get("content"))
            elif msg.get("role") == "assistant":
                session.context_manager.add_assistant_message(
                    msg.get("content"),
                    msg.get("tool_calls")
                )
            elif msg.get("role") == "tool":
                session.context_manager.add_tool_result(
                    msg.get("tool_call_id"),
                    msg.get("content"),
                )

        # Resume circuit breaker state
        circuit_breaker = CircuitBreakerControl(
            session.circuit_breaker
        )
        circuit_breaker.display_status(
            snapshot.consecutive_error_count,
            snapshot.consecutive_no_progress,
            snapshot.completion_indicators,
        )

        from friday_ai.agent.autonomous_loop import ResponseAnalyzer
        response_analyzer = ResponseAnalyzer(config)

        # Start the agent in resume mode
        async with session.agent as agent:
            while True:
                user_input = console.input("> ")
                if not user_input or user_input.lower() in ["exit", "quit", "/exit", "/quit", "/exit"]:
                    console.print("[bold]Session ended[/bold]")
                    break

                # Process command
                if user_input.startswith("/"):
                    # Handle slash commands
                    await session.cli.handle_command(user_input)
                else:
                    # Run as autonomous
                    await agent.run(user_input)
                    # Check for completion indicators
                    completion_indicators = response_analyzer.check_completion_indicators(
                        session.context_manager.get_all_messages()
                    )
                    circuit_breaker.display_status(
                        session.circuit_breaker.consecutive_error_count,
                        session.circuit_breaker.consecutive_no_progress,
                        completion_indicators,
                    )
    except Exception as e:
        console.print(f"[error]Failed to resume session: {e}[/error]")
