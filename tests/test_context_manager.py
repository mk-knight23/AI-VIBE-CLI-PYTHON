"""Comprehensive tests for context manager module."""

from unittest.mock import MagicMock, patch

import pytest

from friday_ai.context.manager import ContextManager
from friday_ai.client.response import TokenUsage


class TestContextManager:
    """Test ContextManager class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = MagicMock()
        config.max_tokens = 8000
        config.context_window = 128000
        config.compression_threshold = 0.8
        return config

    @pytest.fixture
    def context_manager(self, mock_config):
        """Create a ContextManager for testing."""
        return ContextManager(mock_config)

    def test_context_manager_initialization(self, context_manager, mock_config):
        """Test ContextManager initialization."""
        assert context_manager.config == mock_config
        assert context_manager.messages == []
        assert context_manager.total_usage.prompt_tokens == 0
        assert context_manager.total_usage.completion_tokens == 0

    def test_add_user_message(self, context_manager):
        """Test adding a user message."""
        context_manager.add_user_message("Hello, world!")
        assert len(context_manager.messages) == 1
        assert context_manager.messages[0]["role"] == "user"
        assert context_manager.messages[0]["content"] == "Hello, world!"

    def test_add_assistant_message_basic(self, context_manager):
        """Test adding a basic assistant message."""
        context_manager.add_assistant_message("Hi there!")
        assert len(context_manager.messages) == 1
        assert context_manager.messages[0]["role"] == "assistant"
        assert context_manager.messages[0]["content"] == "Hi there!"
        assert context_manager.messages[0].get("tool_calls") is None

    def test_add_assistant_message_with_tool_calls(self, context_manager):
        """Test adding assistant message with tool calls."""
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": '{"path": "/tmp/file.txt"}'
                }
            }
        ]
        context_manager.add_assistant_message("I'll read that file.", tool_calls)
        assert len(context_manager.messages) == 1
        assert context_manager.messages[0]["tool_calls"] == tool_calls

    def test_add_tool_result(self, context_manager):
        """Test adding a tool result message."""
        context_manager.add_tool_result("call_1", "File content: hello")
        assert len(context_manager.messages) == 1
        assert context_manager.messages[0]["role"] == "tool"
        assert context_manager.messages[0]["tool_call_id"] == "call_1"
        assert context_manager.messages[0]["content"] == "File content: hello"

    def test_get_messages(self, context_manager):
        """Test getting all messages."""
        context_manager.add_user_message("Hello")
        context_manager.add_assistant_message("Hi!")

        messages = context_manager.get_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_get_messages_returns_copy(self, context_manager):
        """Test that get_messages returns a copy, not reference."""
        context_manager.add_user_message("Hello")
        messages = context_manager.get_messages()
        messages.append({"role": "user", "content": "Modified"})

        # Original should be unchanged
        assert len(context_manager.messages) == 1

    def test_get_last_n_messages(self, context_manager):
        """Test getting last N messages."""
        for i in range(5):
            context_manager.add_user_message(f"Message {i}")

        last_3 = context_manager.get_last_n_messages(3)
        assert len(last_3) == 3
        assert last_3[0]["content"] == "Message 2"
        assert last_3[2]["content"] == "Message 4"

    def test_get_last_n_messages_exceeds_count(self, context_manager):
        """Test getting more messages than available."""
        context_manager.add_user_message("Only message")

        result = context_manager.get_last_n_messages(10)
        assert len(result) == 1

    def test_clear_messages(self, context_manager):
        """Test clearing all messages."""
        context_manager.add_user_message("Message 1")
        context_manager.add_user_message("Message 2")
        context_manager.clear_messages()

        assert len(context_manager.messages) == 0

    def test_get_token_count(self, context_manager):
        """Test getting total token count."""
        usage1 = TokenUsage(prompt_tokens=100, completion_tokens=50)
        usage2 = TokenUsage(prompt_tokens=200, completion_tokens=75)

        context_manager.add_usage(usage1)
        context_manager.add_usage(usage2)

        total = context_manager.get_token_count()
        assert total == 425  # 100+50+200+75

    def test_add_usage(self, context_manager):
        """Test adding usage information."""
        usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
        context_manager.add_usage(usage)

        assert context_manager.total_usage.prompt_tokens == 100
        assert context_manager.total_usage.completion_tokens == 50

    def test_set_latest_usage(self, context_manager):
        """Test setting latest usage."""
        usage = TokenUsage(prompt_tokens=150, completion_tokens=75)
        context_manager.set_latest_usage(usage)

        assert context_manager.latest_usage.prompt_tokens == 150
        assert context_manager.latest_usage.completion_tokens == 75

    def test_get_messages_with_system_prompt(self, context_manager):
        """Test getting messages including system prompt."""
        context_manager.system_prompt = "You are a helpful assistant."
        context_manager.add_user_message("Hello")

        messages = context_manager.get_messages()
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."

    def test_set_system_prompt(self, context_manager):
        """Test setting system prompt."""
        context_manager.set_system_prompt("New system prompt")
        assert context_manager.system_prompt == "New system prompt"

    def test_prune_tool_outputs(self, context_manager):
        """Test pruning tool output messages."""
        context_manager.add_user_message("Read file")
        context_manager.add_assistant_message("I'll read it.", [{"id": "call_1", "type": "function"}])
        context_manager.add_tool_result("call_1", "File content")
        context_manager.add_user_message("What does it say?")

        context_manager.prune_tool_outputs()

        # Tool results should be pruned (empty content)
        tool_msg = [m for m in context_manager.messages if m.get("role") == "tool"]
        assert len(tool_msg) == 1
        # After pruning, tool outputs should have empty content
        assert tool_msg[0]["content"] == ""

    def test_needs_compression_false(self, context_manager, mock_config):
        """Test needs_compression returns False when under threshold."""
        mock_config.max_tokens = 8000
        mock_config.compression_threshold = 0.8

        usage = TokenUsage(prompt_tokens=100, completion_tokens=50)
        context_manager.add_usage(usage)

        assert not context_manager.needs_compression()

    def test_needs_compression_true(self, context_manager, mock_config):
        """Test needs_compression returns True when over threshold."""
        mock_config.max_tokens = 100
        mock_config.compression_threshold = 0.8

        usage = TokenUsage(prompt_tokens=90, completion_tokens=0)
        context_manager.add_usage(usage)

        assert context_manager.needs_compression()

    def test_get_context_summary(self, context_manager):
        """Test getting context summary."""
        context_manager.add_user_message("Message 1")
        context_manager.add_assistant_message("Response 1")
        context_manager.add_user_message("Message 2")

        summary = context_manager.get_context_summary()
        assert "total_messages" in summary
        assert summary["total_messages"] == 3
        assert "total_tokens" in summary

    def test_replace_with_summary(self, context_manager):
        """Test replacing messages with summary."""
        context_manager.add_user_message("Message 1")
        context_manager.add_assistant_message("Response 1")
        context_manager.add_user_message("Message 2")

        summary = "Previous conversation discussed topic X"
        context_manager.replace_with_summary(summary)

        messages = context_manager.get_messages()
        # Should have system prompt, summary, and last message
        assert any(m.get("content") == summary for m in messages)

    def test_count_tokens_by_message_role(self, context_manager):
        """Test counting tokens by role."""
        context_manager.add_user_message("User message")
        context_manager.add_assistant_message("Assistant message")

        counts = context_manager.count_tokens_by_message_role()
        # Should return counts for different roles
        assert isinstance(counts, dict)

    def test_get_message_count(self, context_manager):
        """Test getting total message count."""
        context_manager.add_user_message("Msg 1")
        context_manager.add_assistant_message("Msg 2")
        context_manager.add_tool_result("call_1", "result")

        assert context_manager.get_message_count() == 3

    def test_has_messages_false(self, context_manager):
        """Test has_messages returns False when empty."""
        assert not context_manager.has_messages()

    def test_has_messages_true(self, context_manager):
        """Test has_messages returns True when has messages."""
        context_manager.add_user_message("Hello")
        assert context_manager.has_messages()

    def test_get_last_user_message(self, context_manager):
        """Test getting last user message."""
        context_manager.add_user_message("First")
        context_manager.add_assistant_message("Response")
        context_manager.add_user_message("Second")

        last_user = context_manager.get_last_user_message()
        assert last_user["content"] == "Second"

    def test_get_last_user_message_none(self, context_manager):
        """Test getting last user message when none exists."""
        assert context_manager.get_last_user_message() is None

    def test_get_last_assistant_message(self, context_manager):
        """Test getting last assistant message."""
        context_manager.add_user_message("Hello")
        context_manager.add_assistant_message("Response 1")
        context_manager.add_assistant_message("Response 2")

        last_assistant = context_manager.get_last_assistant_message()
        assert last_assistant["content"] == "Response 2"

    def test_get_last_assistant_message_none(self, context_manager):
        """Test getting last assistant message when none exists."""
        assert context_manager.get_last_assistant_message() is None

    def test_remove_last_message(self, context_manager):
        """Test removing last message."""
        context_manager.add_user_message("First")
        context_manager.add_user_message("Second")

        context_manager.remove_last_message()
        assert len(context_manager.messages) == 1
        assert context_manager.messages[-1]["content"] == "First"

    def test_remove_last_message_empty(self, context_manager):
        """Test removing last message when empty."""
        context_manager.remove_last_message()
        assert len(context_manager.messages) == 0

    def test_clone_context_manager(self, context_manager):
        """Test cloning a context manager."""
        context_manager.add_user_message("Hello")
        context_manager.add_usage(TokenUsage(prompt_tokens=100, completion_tokens=50))

        cloned = context_manager.clone()

        assert len(cloned.messages) == len(context_manager.messages)
        assert cloned.get_token_count() == context_manager.get_token_count()
        # Should be different objects
        assert cloned is not context_manager
        assert cloned.messages is not context_manager.messages

    def test_estimate_tokens_text(self, context_manager):
        """Test estimating tokens for text."""
        text = "Hello, world!"
        estimate = context_manager.estimate_tokens(text)
        assert estimate > 0
        assert isinstance(estimate, int)

    def test_estimate_tokens_messages(self, context_manager):
        """Test estimating tokens for messages."""
        context_manager.add_user_message("This is a test message with some content")
        estimate = context_manager.estimate_tokens()
        assert estimate > 0

    @patch('friday_ai.context.manager tiktoken')
    def test_token_encoding_with_tiktoken(self, mock_tiktoken, context_manager):
        """Test token encoding when tiktoken is available."""
        mock_encoding = MagicMock()
        mock_encoding.encode.return_value = [1, 2, 3, 4, 5]
        mock_tiktoken.encoding_for_model.return_value = mock_encoding

        count = context_manager._count_tokens_with_tiktoken("Hello")
        assert count == 5

    def test_add_message_with_metadata(self, context_manager):
        """Test adding message with custom metadata."""
        context_manager.add_user_message("Hello", metadata={"timestamp": "2024-01-01"})
        assert context_manager.messages[0].get("metadata") == {"timestamp": "2024-01-01"}

    def test_get_messages_by_role(self, context_manager):
        """Test filtering messages by role."""
        context_manager.add_user_message("User 1")
        context_manager.add_assistant_message("Assistant 1")
        context_manager.add_user_message("User 2")

        user_msgs = context_manager.get_messages_by_role("user")
        assert len(user_msgs) == 2
        assert all(m["role"] == "user" for m in user_msgs)

    def test_trim_to_token_limit(self, context_manager, mock_config):
        """Test trimming messages to stay within token limit."""
        mock_config.max_tokens = 100

        # Add messages that would exceed limit
        for i in range(10):
            context_manager.add_user_message(f"Message {i} " * 50)

        context_manager.trim_to_token_limit()
        # Should trim to stay under limit
        assert context_manager.estimate_tokens() <= mock_config.max_tokens

    def test_reset_with_system_prompt(self, context_manager):
        """Test resetting while keeping system prompt."""
        context_manager.set_system_prompt("System prompt")
        context_manager.add_user_message("User message")

        context_manager.reset_with_system_prompt()

        assert context_manager.system_prompt == "System prompt"
        assert len(context_manager.messages) == 1  # Only system prompt


class TestContextManagerEdgeCases:
    """Test edge cases for ContextManager."""

    @pytest.fixture
    def context_manager(self):
        """Create a basic context manager."""
        config = MagicMock()
        config.max_tokens = 8000
        config.context_window = 128000
        return ContextManager(config)

    def test_empty_content_message(self, context_manager):
        """Test adding message with empty content."""
        context_manager.add_user_message("")
        assert len(context_manager.messages) == 1
        assert context_manager.messages[0]["content"] == ""

    def test_very_long_message(self, context_manager):
        """Test adding very long message."""
        long_content = "A" * 10000
        context_manager.add_user_message(long_content)
        assert len(context_manager.messages) == 1

    def test_unicode_content(self, context_manager):
        """Test messages with unicode content."""
        context_manager.add_user_message("Hello 世界 🌍")
        assert context_manager.messages[0]["content"] == "Hello 世界 🌍"

    def test_special_characters_in_content(self, context_manager):
        """Test messages with special characters."""
        special = "Test\n\t\r with \x00 null"
        context_manager.add_user_message(special)
        assert context_manager.messages[0]["content"] == special

    def test_none_tool_calls(self, context_manager):
        """Test adding assistant message with None tool_calls."""
        context_manager.add_assistant_message("Hello", tool_calls=None)
        assert context_manager.messages[0].get("tool_calls") is None

    def test_empty_tool_calls(self, context_manager):
        """Test adding assistant message with empty tool_calls."""
        context_manager.add_assistant_message("Hello", tool_calls=[])
        assert context_manager.messages[0]["tool_calls"] == []

    def test_multiple_tool_results(self, context_manager):
        """Test adding multiple tool results."""
        context_manager.add_tool_result("call_1", "Result 1")
        context_manager.add_tool_result("call_2", "Result 2")
        context_manager.add_tool_result("call_3", "Result 3")

        tool_msgs = [m for m in context_manager.messages if m.get("role") == "tool"]
        assert len(tool_msgs) == 3

    def test_get_token_count_with_no_usage(self, context_manager):
        """Test getting token count when no usage recorded."""
        count = context_manager.get_token_count()
        assert count == 0

    def test_prune_with_no_tool_messages(self, context_manager):
        """Test pruning when there are no tool messages."""
        context_manager.add_user_message("Hello")
        context_manager.add_assistant_message("Hi")

        # Should not raise error
        context_manager.prune_tool_outputs()
        assert len(context_manager.messages) == 2
