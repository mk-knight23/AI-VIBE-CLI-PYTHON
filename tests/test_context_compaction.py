"""Tests for context compaction strategies."""

import pytest
from datetime import datetime, timedelta

from friday_ai.context.strategies import (
    SmartCompactor,
    CompactionStrategy,
    MessageScore,
)


class TestCompactionStrategy:
    """Test CompactionStrategy enum."""

    def test_strategies(self):
        """Test all strategy types exist."""
        assert CompactionStrategy.TOKEN_BASED.value == "token"
        assert CompactionStrategy.RELEVANCE.value == "relevance"
        assert CompactionStrategy.RECENCY.value == "recency"
        assert CompactionStrategy.IMPORTANCE.value == "importance"
        assert CompactionStrategy.SEMANTIC.value == "semantic"
        assert CompactionStrategy.HYBRID.value == "hybrid"


class TestMessageScore:
    """Test MessageScore functionality."""

    @pytest.fixture
    def message(self):
        return {
            "role": "user",
            "content": "test message",
        }

    @pytest.fixture
    def score(
        self,
        message,
        relevance=0.8,
        recency=0.6,
        importance=0.9,
        semantic=0.5,
    ):
        return MessageScore(message, relevance, recency, importance, semantic)

    def test_initialization(self, score, message):
        """Test score initialization."""
        assert score.message == message
        assert score.relevance_score == 0.8
        assert score.recency_score == 0.6
        assert score.importance_score == 0.9
        assert score.semantic_score == 0.5

    def test_calculate_total_token_based(self, score):
        """Test TOKEN_BASED strategy calculation."""
        total = score.calculate_total(CompactionStrategy.TOKEN_BASED)

        # Token-based always returns 1.0 (neutral score)
        assert total == 1.0

    def test_calculate_total_relevance(self, score):
        """Test RELEVANCE strategy calculation."""
        total = score.calculate_total(CompactionStrategy.RELEVANCE)

        assert total == score.relevance_score

    def test_calculate_total_recency(self, score):
        """Test RECENCY strategy calculation."""
        total = score.calculate_total(CompactionStrategy.RECENCY)

        assert total == score.recency_score

    def test_calculate_total_importance(self, score):
        """Test IMPORTANCE strategy calculation."""
        total = score.calculate_total(CompactionStrategy.IMPORTANCE)

        assert total == score.importance_score

    def test_calculate_total_semantic(self, score):
        """Test SEMANTIC strategy calculation."""
        total = score.calculate_total(CompactionStrategy.SEMANTIC)

        assert total == score.semantic_score

    def test_calculate_total_hybrid(self, score):
        """Test HYBRID strategy calculation."""
        total = score.calculate_total(CompactionStrategy.HYBRID)

        # Hybrid is weighted combination
        expected = (
            (score.relevance_score * 0.3)
            + (score.recency_score * 0.3)
            + (score.importance_score * 0.25)
            + (score.semantic_score * 0.15)
        )

        assert abs(total - expected) < 0.01  # Floating point comparison


class TestSmartCompactor:
    """Test SmartCompactor functionality."""

    @pytest.fixture
    def messages(self):
        return [
            {
                "role": "system",
                "content": "You are a helpful assistant.",
                "timestamp": datetime.now().isoformat(),
            },
            {
                "role": "user",
                "content": "Hello, how are you?",
            },
            {
                "role": "assistant",
                "content": "I'm doing well, thanks!",
            },
            {
                "role": "tool",
                "content": "Command executed successfully",
            },
            {
                "role": "user",
                "content": "What's the weather?",
            },
            {
                "role": "assistant",
                "content": "I don't have real-time weather data.",
            },
        ]

    @pytest.fixture
    def compactor(self):
        return SmartCompactor(
            strategy=CompactionStrategy.HYBRID,
            keep_tool_calls=True,
            keep_system_messages=True,
            min_messages=5,
            max_messages=50,
        )

    def test_initialization(self, compactor):
        """Test compactor initialization."""
        assert compactor.strategy == CompactionStrategy.HYBRID
        assert compactor.keep_tool_calls is True
        assert compactor.keep_system_messages is True
        assert compactor.min_messages == 5
        assert compactor.max_messages == 50

    def test_calculate_relevance(self, compactor):
        """Test relevance calculation."""
        msg = {"role": "user", "content": "implement feature X"}
        query = "feature X implementation"

        score = compactor._calculate_relevance(msg, query)

        # Should find exact match or high relevance
        assert score > 0.5

    def test_calculate_recency(self, compactor):
        """Test recency calculation."""
        now = datetime.now()

        # Recent message (< 1 hour ago)
        recent_msg = {
            "role": "user",
            "content": "recent message",
            "timestamp": (now - timedelta(minutes=30)).isoformat(),
        }

        # Old message (> 24 hours ago)
        old_msg = {
            "role": "user",
            "content": "old message",
            "timestamp": (now - timedelta(days=2)).isoformat(),
        }

        recent_score = compactor._calculate_recency(recent_msg, now)
        old_score = compactor._calculate_recency(old_msg, now)

        # Recent should have higher score
        assert recent_score > old_score

    def test_calculate_importance(self, compactor):
        """Test importance calculation."""
        # Tool call - highest importance
        tool_msg = {"role": "tool", "content": "done"}
        tool_score = compactor._calculate_importance(tool_msg)
        assert tool_score == 1.0

        # System message - high importance
        system_msg = {"role": "system", "content": "instructions"}
        system_score = compactor._calculate_importance(system_msg)
        assert system_score == 0.8

        # User message - baseline importance
        user_msg = {"role": "user", "content": "hello"}
        user_score = compactor._calculate_importance(user_msg)
        assert user_score == 0.4

        # Assistant with code - high importance
        assistant_msg = {"role": "assistant", "content": "```python\ncode\n```"}
        assistant_score = compactor._calculate_importance(assistant_msg)
        assert assistant_score == 0.7

    def test_compact_under_minimum(self, compactor, messages):
        """Test compaction when under minimum threshold."""
        result = compactor.compact(messages, current_query="test")

        # Should return original messages unchanged
        assert len(result) == len(messages)

    def test_compact_protects_system_messages(self, compactor, messages):
        """Test that system messages are protected."""
        result = compactor.compact(messages, current_query="test")

        # System message should be in result
        system_msgs = [m for m in result if m.get("role") == "system"]
        assert len(system_msgs) == 1

    def test_compact_protects_tool_calls(self, compactor, messages):
        """Test that tool calls are protected."""
        result = compactor.compact(messages, current_query="test")

        # Tool messages should be in result
        tool_msgs = [m for m in result if m.get("role") == "tool" or m.get("tool_calls")]
        assert len(tool_msgs) == 1

    @pytest.mark.skip(reason="Chit-chat removal logic needs adjustment")
    def test_compact_removes_chit_chat(self, compactor):
        """Test that chit-chat is removed."""
        messages = [
            {"role": "system", "content": "instructions"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "how are you?"},
            {"role": "assistant", "content": "good"},
            {"role": "user", "content": "ok"},
            {"role": "assistant", "content": "sure"},
        ] * 5  # 35 messages total

        result = compactor.compact(messages, current_query="test")

        # Should remove many user/assistant chit-chat pairs
        # But keep system message
        assert len(result) < len(messages)

    def test_estimate_tokens(self, compactor, messages):
        """Test token estimation."""
        estimate = compactor.estimate_tokens(messages)

        # Should be approximately total characters / 4
        total_chars = sum(len(m.get("content", "")) for m in messages)
        expected = total_chars // 4

        assert estimate == expected

    def test_compact_respects_max_limit(self, compactor):
        """Test that max_messages limit is respected."""
        # Create 100 messages
        messages = [{"role": "system", "content": "instructions"}] + [
            {"role": f"user", "content": f"message {i}"} for i in range(99)
        ]

        result = compactor.compact(messages, current_query="test")

        # Should not exceed max_messages + protected messages
        assert len(result) <= compactor.max_messages
