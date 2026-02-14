"""Context Compaction - Intelligent message pruning using multiple strategies."""

import logging
from typing import Any, Optional

from friday_ai.client.llm_client import LLMClient
from friday_ai.client.response import StreamEventType, TokenUsage
from friday_ai.context.manager import ContextManager
from friday_ai.prompts.system import get_compression_prompt
from friday_ai.context.strategies import (
    SmartCompactor,
    CompactionStrategy,
    MessageScore,
)

logger = logging.getLogger(__name__)


class ChatCompactor:
    """Compacts chat history using configurable strategies.

    Supports multiple compaction strategies:
    - TOKEN_BASED: Simple token count threshold
    - RELEVANCE: Score messages by relevance to current query
    - RECENCY: Prioritize recent messages
    - IMPORTANCE: Keep tool calls and important messages
    - SEMANTIC: Embedding-based similarity (future)
    - HYBRID: Combine multiple scoring methods (default)
    """

    def __init__(
        self,
        client: LLMClient,
        strategy: CompactionStrategy = CompactionStrategy.HYBRID,
        keep_tool_calls: bool = True,
        keep_system_messages: bool = True,
        min_messages: int = 5,
        max_messages: int = 50,
        embedding_service: Optional[Any] = None,
    ):
        """Initialize chat compactor.

        Args:
            client: LLM client for token estimation
            strategy: Compaction strategy to use (default: HYBRID)
            keep_tool_calls: Always keep tool call messages
            keep_system_messages: Always keep system messages
            min_messages: Minimum messages before compaction
            max_messages: Maximum messages to keep after compaction
            embedding_service: EmbeddingService for semantic scoring (optional)
        """
        self.client = client
        self.strategy = strategy

        # Initialize embedding service if needed for SEMANTIC or HYBRID strategies
        if embedding_service is None and strategy in [
            CompactionStrategy.SEMANTIC,
            CompactionStrategy.HYBRID,
        ]:
            try:
                from friday_ai.intelligence.embeddings import EmbeddingService

                embedding_service = EmbeddingService()
                logger.info("Initialized EmbeddingService for semantic compression")
            except Exception as e:
                logger.warning(f"Failed to initialize EmbeddingService: {e}")
                logger.info("Semantic compression will use fallback scores")
                embedding_service = None

        # Create smart compactor with strategy and embedding service
        self.smart_compactor = SmartCompactor(
            strategy=strategy,
            keep_tool_calls=keep_tool_calls,
            keep_system_messages=keep_system_messages,
            min_messages=min_messages,
            max_messages=max_messages,
            embedding_service=embedding_service,
        )

        logger.info(f"ChatCompactor initialized with strategy: {strategy.value}")

    def _format_history_for_compaction(self, messages: list[dict[str, Any]]) -> str:
        """Format conversation history for compression prompt.

        Args:
            messages: List of messages to format

        Returns:
            Formatted conversation string
        """
        output = ["Here is the conversation that needs to be continue: \n"]

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                continue

            if role == "tool":
                tool_id = msg.get("tool_call_id", "unknown")
                truncated = content[:2000] if len(content) > 2000 else content
                if len(content) > 2000:
                    truncated += "\n... [tool output truncated]"
                output.append(f"[Tool Result ({tool_id})]:\n{truncated}")
            elif role == "assistant":
                tool_details = []
                if content:
                    truncated = content[:3000] if len(content) > 3000 else content
                    if len(content) > 3000:
                        truncated += "\n... [response truncated]"
                    output.append(f"Assistant:\n{truncated}")
                if msg.get("tool_calls"):
                    for tc in msg["tool_calls"]:
                        func = tc.get("function", {})
                        name = func.get("name", "unknown")
                        args = func.get("arguments", "{}")
                        if len(args) > 500:
                            args = args[:500]
                        tool_details.append(f"  - {name}({args})")
                    output.append("Assistant called tools:\n" + "\n".join(tool_details))
            else:
                truncated = content[:1500] if len(content) > 1500 else content
                if len(content) > 1500:
                    truncated += "\n... [message truncated]"
                output.append(f"User:\n{truncated}")

        return "\n\n---\n\n".join(output)

    async def compress_legacy(self, context_manager: ContextManager) -> tuple[str | None, TokenUsage | None]:
        """Legacy compression method (backward compatibility).

        Uses simple token-based compression without strategy.

        Args:
            context_manager: Context manager with messages

        Returns:
            Tuple of (summary, usage) or (None, None)
        """
        messages = context_manager.get_messages()

        if len(messages) < 3:
            return None, None

        compression_messages = [
            {
                "role": "system",
                "content": get_compression_prompt(),
            },
            {
                "role": "user",
                "content": self._format_history_for_compaction(messages),
            },
        ]

        try:
            summary = ""
            usage = None

            async for event in self.client.chat_completion(
                compression_messages,
                stream=False,
            ):
                if event.type == StreamEventType.MESSAGE_COMPLETE:
                    usage = event.usage
                    summary += event.text_delta.content

            if not summary or not usage:
                return None, None

            return summary, usage

        except Exception:
            logger.exception("Legacy compression failed")
            return None, None

    async def compress_smart(
        self,
        context_manager: ContextManager,
        current_query: str = "",
    ) -> tuple[str | None, TokenUsage | None]:
        """Smart compression using configured strategy.

        Args:
            context_manager: Context manager with messages
            current_query: Current user query for relevance scoring

        Returns:
            Tuple of (summary, usage) or (None, None)
        """
        messages = context_manager.get_messages()

        if len(messages) < self.smart_compactor.min_messages:
            logger.debug(
                f"Only {len(messages)} messages, below minimum "
                f"({self.smart_compactor.min_messages}), not compacting"
            )
            return None, None

        # Use smart compactor with strategy
        compacted_messages = self.smart_compactor.compact(messages, current_query)

        if len(compacted_messages) == len(messages):
            logger.debug("No messages removed by compaction")
            return None, None

        # Format for compression
        compression_messages = [
            {
                "role": "system",
                "content": get_compression_prompt(),
            },
            {
                "role": "user",
                "content": self._format_history_for_compaction(compacted_messages),
            },
        ]

        try:
            summary = ""
            usage = None

            async for event in self.client.chat_completion(
                compression_messages,
                stream=False,
            ):
                if event.type == StreamEventType.MESSAGE_COMPLETE:
                    usage = event.usage
                    summary += event.text_delta.content

            if not summary or not usage:
                return None, None

            removed_count = len(messages) - len(compacted_messages)
            logger.info(
                f"Smart compression removed {removed_count} messages using "
                f"{self.strategy.value} strategy, {len(compacted_messages)} remaining"
            )

            return summary, usage

        except Exception:
            logger.exception("Smart compression failed")
            return None, None

    async def compress(
        self,
        context_manager: ContextManager,
        current_query: str = "",
        use_smart: bool = True,
    ) -> tuple[str | None, TokenUsage | None]:
        """Compress context using configured strategy.

        Args:
            context_manager: Context manager with messages
            current_query: Current query for relevance scoring
            use_smart: Use smart compression (True) or legacy (False)

        Returns:
            Tuple of (summary, usage) or (None, None)
        """
        # Choose compression method based on strategy
        if use_smart and self.strategy != CompactionStrategy.TOKEN_BASED:
            return await self.compress_smart(context_manager, current_query)
        else:
            return await self.compress_legacy(context_manager)

    def estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate token count for messages.

        Uses smart compactor's estimation for better accuracy.

        Args:
            messages: List of messages

        Returns:
            Estimated token count
        """
        return self.smart_compactor.estimate_tokens(messages)
