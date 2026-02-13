"""Session - Orchestrates agent interaction with LLM and tools."""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from friday_ai.agent.safety_manager import SafetyManager
from friday_ai.agent.session_metrics import SessionMetrics

# New refactored components
from friday_ai.agent.tool_orchestrator import ToolOrchestrator
from friday_ai.client.llm_client import LLMClient
from friday_ai.config.config import Config
from friday_ai.config.loader import get_data_dir
from friday_ai.context.compaction import ChatCompactor
from friday_ai.context.loop_detector import LoopDetector
from friday_ai.context.manager import ContextManager
from friday_ai.hooks.hook_system import HookSystem
from friday_ai.tools.registry import create_default_registry

logger = logging.getLogger(__name__)


class Session:
    """Orchestrates agent interaction with LLM and tools.

    Simplified session class using composition to delegate specialized concerns.
    Reduced from 92 lines to ~50 lines by extracting:
    - ToolOrchestrator: Tool registry, MCP, discovery
    - SafetyManager: Approval, validation, sanitization
    - SessionMetrics: Stats tracking

    Remaining responsibilities:
    - High-level orchestration
    - Context management
    - LLM client coordination
    - Event emission
    - Loop detection
    - Hook execution
    """

    def __init__(self, config: Config):
        """Initialize session with composition over inheritance.

        Args:
            config: Application configuration
        """
        self.config = config

        # Core client
        self.client = LLMClient(config=config)

        # Composed components
        self.tool_orchestrator = ToolOrchestrator(
            config,
            create_default_registry(config),
        )
        self.safety_manager = SafetyManager(
            config.approval,
            str(config.cwd),
        )
        self.metrics = SessionMetrics(str(uuid.uuid4()))
        self.chat_compactor = ChatCompactor(self.client)
        self.loop_detector = LoopDetector()
        self.hook_system = HookSystem(config)

        # Context manager (initialized separately)
        self.context_manager: ContextManager | None = None

        # Timestamps
        self.created_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)

        logger.info("Session initialized with refactored architecture")

    async def initialize(self) -> None:
        """Initialize session components.

        Establishes MCP connections, tool discovery, and context.
        """
        logger.info("Initializing session")

        # Initialize tool orchestrator (MCP, discovery)
        mcp_tools = await self.tool_orchestrator.initialize()

        # Initialize context manager
        self.context_manager = ContextManager(
            config=self.config,
            user_memory=self._load_memory(),
            tools=self.tool_orchestrator.tool_registry.get_tools(),
        )

        logger.info(f"Session initialized with {mcp_tools} MCP tools")

    def _load_memory(self) -> str | None:
        """Load user memory from disk.

        Returns:
            User memory content or None if not found
        """
        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        path = data_dir / "user_memory.json"

        if not path.exists():
            return None

        try:
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            entries = data.get("entries")
            if not entries:
                return None

            lines = ["User preferences and notes:"]
            for key, value in entries.items():
                lines.append(f"- {key}: {value}")

            return "\n".join(lines)
        except Exception:
            logger.warning(f"Failed to load user memory: {path}")
            return None

    def increment_turn(self) -> int:
        """Increment turn counter and update metrics.

        Returns:
            New turn count
        """
        self.metrics.increment_turn()
        self.updated_at = datetime.now(UTC)
        return self.metrics.turn_count

    def get_stats(self) -> dict[str, Any]:
        """Get session statistics.

        Returns:
            Dictionary with session metrics
        """
        # Update metrics with current context info
        if self.context_manager:
            self.metrics.message_count = self.context_manager.message_count
            self.metrics.total_tokens_used = self.context_manager.total_usage.total_tokens
            self.metrics.total_tokens_cached = self.context_manager.total_usage.cached_tokens

        return self.metrics.get_stats()

    async def save(self) -> None:
        """Save session state to disk.

        Persists context, metrics, and metadata.
        """
        logger.info("Saving session state")

        data_dir = get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)

        # Save session metadata
        session_file = data_dir / f"session_{self.metrics.session_id}.json"
        session_data = {
            "session_id": self.metrics.session_id,
            "created_at": self.metrics.created_at.isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "stats": self.get_stats(),
        }

        session_file.write_text(
            json.dumps(session_data, indent=2),
            encoding="utf-8",
        )

        logger.info(f"Session saved to: {session_file}")

    async def cleanup(self) -> None:
        """Cleanup session resources.

        Properly closes connections and releases resources.
        """
        logger.info("Cleaning up session resources")

        # Shutdown tool orchestrator (MCP connections)
        await self.tool_orchestrator.shutdown()

        # Shutdown HTTP client (connection pooling)
        from friday_ai.tools.builtin.http_client import shutdown_http_client

        await shutdown_http_client()

        logger.info("Session cleanup complete")
