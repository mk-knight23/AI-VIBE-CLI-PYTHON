"""Context Compaction Strategies - Multiple strategies for intelligent context pruning."""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CompactionStrategy(Enum):
    """Compaction strategy types."""

    TOKEN_BASED = "token"  # Current approach - simple token count
    RELEVANCE = "relevance"  # Score by relevance to current query
    RECENCY = "recency"  # Keep recent messages
    IMPORTANCE = "importance"  # Tool calls > chit-chat
    SEMANTIC = "semantic"  # Embedding-based similarity
    HYBRID = "hybrid"  # Combine multiple strategies


class MessageScore:
    """Score for a message in context."""

    def __init__(
        self,
        message: dict[str, Any],
        relevance_score: float = 0.0,
        recency_score: float = 0.0,
        importance_score: float = 0.0,
        semantic_score: float = 0.0,
    ):
        """Initialize message score.

        Args:
            message: The message to score
            relevance_score: Relevance to current context (0-1)
            recency_score: How recent the message is (0-1)
            importance_score: Importance of message content (0-1)
            semantic_score: Semantic similarity score (0-1)
        """
        self.message = message
        self.relevance_score = relevance_score
        self.recency_score = recency_score
        self.importance_score = importance_score
        self.semantic_score = semantic_score

    def calculate_total(self, strategy: CompactionStrategy) -> float:
        """Calculate total score based on strategy.

        Args:
            strategy: Which compaction strategy to use

        Returns:
            Total score (higher = more important to keep)
        """
        if strategy == CompactionStrategy.TOKEN_BASED:
            # Token-based doesn't use scoring
            return 1.0

        elif strategy == CompactionStrategy.RELEVANCE:
            return self.relevance_score

        elif strategy == CompactionStrategy.RECENCY:
            return self.recency_score

        elif strategy == CompactionStrategy.IMPORTANCE:
            return self.importance_score

        elif strategy == CompactionStrategy.SEMANTIC:
            return self.semantic_score

        elif strategy == CompactionStrategy.HYBRID:
            # Weighted combination of all scores
            return (
                (self.relevance_score * 0.3) +
                (self.recency_score * 0.3) +
                (self.importance_score * 0.25) +
                (self.semantic_score * 0.15)
            )

        else:
            logger.warning(f"Unknown strategy: {strategy}, using default")
            return self.recency_score


class SmartCompactor:
    """Intelligent context compaction with multiple strategies."""

    def __init__(
        self,
        strategy: CompactionStrategy = CompactionStrategy.HYBRID,
        keep_tool_calls: bool = True,
        keep_system_messages: bool = True,
        min_messages: int = 5,
        max_messages: int = 50,
        embedding_service: Optional[Any] = None,
    ):
        """Initialize smart compactor.

        Args:
            strategy: Compaction strategy to use
            keep_tool_calls: Always keep tool call messages
            keep_system_messages: Always keep system messages
            min_messages: Minimum messages to keep after compaction
            max_messages: Maximum messages to keep (soft limit)
            embedding_service: EmbeddingService for semantic scoring (optional)
        """
        self.strategy = strategy
        self.keep_tool_calls = keep_tool_calls
        self.keep_system_messages = keep_system_messages
        self.min_messages = min_messages
        self.max_messages = max_messages
        self.embedding_service = embedding_service

        logger.info(f"Smart compactor initialized with strategy: {strategy.value}")

    def score_messages(
        self,
        messages: list[dict[str, Any]],
        current_query: str = "",
    ) -> list[MessageScore]:
        """Score messages based on strategy.

        Args:
            messages: List of messages to score
            current_query: Current user query for relevance scoring

        Returns:
            List of MessageScore objects
        """
        scored_messages = []
        now = datetime.now(timezone.utc)

        for msg in messages:
            role = msg.get("role", "")

            # Default scores
            relevance = 0.0
            recency = 0.0
            importance = 0.0
            semantic = 0.0

            # Relevance scoring (if current query provided)
            if current_query and self.strategy in [
                CompactionStrategy.RELEVANCE,
                CompactionStrategy.HYBRID,
            ]:
                relevance = self._calculate_relevance(msg, current_query)

            # Recency scoring (for strategies that need it)
            if self.strategy in [
                CompactionStrategy.RECENCY,
                CompactionStrategy.HYBRID,
            ]:
                recency = self._calculate_recency(msg, now)

            # Importance scoring (for strategies that need it)
            if self.strategy in [
                CompactionStrategy.IMPORTANCE,
                CompactionStrategy.HYBRID,
            ]:
                importance = self._calculate_importance(msg)

            # Semantic scoring (for strategies that need it)
            if self.strategy in [
                CompactionStrategy.SEMANTIC,
                CompactionStrategy.HYBRID,
            ]:
                # Use embedding service for semantic similarity
                semantic = self._calculate_semantic(msg, current_query)

            scored_messages.append(
                MessageScore(msg, relevance, recency, importance, semantic)
            )

        return scored_messages

    def _calculate_relevance(self, message: dict[str, Any], query: str) -> float:
        """Calculate relevance score for message.

        Simple keyword matching approach.
        """
        content = message.get("content", "").lower()
        query_lower = query.lower()

        # Exact match gets highest score
        if query_lower in content:
            return 1.0

        # Partial match gets moderate score
        query_words = set(query_lower.split())
        content_words = set(content.split())

        overlap = query_words & content_words
        if overlap:
            return len(overlap) / max(len(query_words), 1) * 0.8

        return 0.0

    def _calculate_recency(self, message: dict[str, Any], now: datetime) -> float:
        """Calculate recency score (newer = higher).

        Uses exponential decay based on message age.
        """
        # Check for timestamp in message
        timestamp_str = message.get("timestamp")
        if not timestamp_str:
            return 0.5  # Default mid-range score

        try:
            # Parse ISO format timestamp
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            age = now - timestamp

            # Exponential decay: score = e^(-age_in_hours)
            age_hours = max(age.total_seconds() / 3600, 0)
            score = 2.718 ** (-age_hours / 24)  # e^(-days)

            return min(max(score, 0.0), 1.0)

        except (ValueError, TypeError):
            logger.warning(f"Failed to parse timestamp: {timestamp_str}")
            return 0.5

    def _calculate_importance(self, message: dict[str, Any]) -> float:
        """Calculate importance score for message.

        Tool calls and errors are most important.
        """
        role = message.get("role", "")
        content = message.get("content", "")

        # Tool calls are very important
        if role == "tool" or message.get("tool_calls"):
            return 1.0

        # System messages are important
        if role == "system":
            return 0.8

        # Assistant messages with code/results are important
        if role == "assistant":
            if "```" in content:  # Contains code
                return 0.7
            if message.get("tool_calls"):  # Called tools
                return 0.9

        # User messages are baseline importance
        return 0.4

    def _calculate_semantic(self, message: dict[str, Any], query: str) -> float:
        """Calculate semantic similarity score for message.

        Uses embedding service for real semantic similarity.
        Falls back to 0.5 if embedding service unavailable.

        Args:
            message: Message to score
            query: Current query for comparison

        Returns:
            Semantic similarity score (0-1)
        """
        # Fallback if no embedding service
        if self.embedding_service is None:
            return 0.5

        # Fallback if no query
        if not query:
            return 0.5

        try:
            # Get message content
            content = message.get("content", "")
            if not content:
                return 0.5

            # Generate embeddings
            query_embedding = self.embedding_service.embed(query)
            content_embedding = self.embedding_service.embed(content)

            # Calculate similarity
            similarity = self.embedding_service.similarity(
                query_embedding,
                content_embedding
            )

            return similarity

        except Exception as e:
            logger.warning(f"Failed to calculate semantic similarity: {e}")
            # Fallback to default score
            return 0.5

    def compact(
        self,
        messages: list[dict[str, Any]],
        current_query: str = "",
    ) -> list[dict[str, Any]]:
        """Compact messages using configured strategy.

        Args:
            messages: List of all messages
            current_query: Current user query for relevance scoring

        Returns:
            Compacted list of messages
        """
        if not messages:
            return messages

        # Score messages
        scored_messages = self.score_messages(messages, current_query)

        # Always keep certain messages
        protected_messages = []
        messages_to_compact = []

        for scored_msg in scored_messages:
            msg = scored_msg.message
            role = msg.get("role", "")

            # Always keep system messages if configured
            if self.keep_system_messages and role == "system":
                protected_messages.append(msg)
                continue

            # Always keep tool calls if configured
            if self.keep_tool_calls and (role == "tool" or msg.get("tool_calls")):
                protected_messages.append(msg)
                continue

            messages_to_compact.append(scored_msg)

        # If we have few messages, don't compact
        if len(messages) <= self.min_messages:
            logger.debug(f"Only {len(messages)} messages, not compacting")
            return messages

        # Sort by score (descending)
        messages_to_compact.sort(
            key=lambda m: m.calculate_total(self.strategy),
            reverse=True,
        )

        # Keep top messages up to max_messages
        keep_count = min(self.max_messages - len(protected_messages), len(messages_to_compact))
        compacted = messages_to_compact[:keep_count]

        # Combine protected and compacted messages
        result = protected_messages + [m.message for m in compacted]

        logger.info(
            f"Compacted {len(messages)} -> {len(result)} messages "
            f"using strategy: {self.strategy.value}"
        )

        return result

    def estimate_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate token count for messages.

        Simple heuristic: ~4 characters per token.
        """
        total_chars = sum(len(str(msg.get("content", ""))) for msg in messages)
        return total_chars // 4
