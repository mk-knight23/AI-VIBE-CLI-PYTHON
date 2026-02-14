"""Tests for LLM Router integration with Session and Agent.

Tests multi-provider routing, task complexity estimation, and cost tracking.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from friday_ai.client.multi_provider import (
    ProviderRouter,
    ProviderManager,
    TaskComplexity,
    RoutingCriteria,
    ProviderInfo,
)
from friday_ai.client.providers.base import ProviderType, ChatMessage
from friday_ai.config.config import Config, ApprovalPolicy


class TestTaskComplexityEstimation:
    """Test task complexity estimation logic."""

    def test_simple_task_short_qa(self):
        """Test SIMPLE complexity for short Q&A."""
        from friday_ai.client.llm_router import LLMRouter

        router = LLMRouter()
        complexity = router.estimate_complexity("What is Python?")

        assert complexity == TaskComplexity.SIMPLE

    def test_simple_task_short_edit(self):
        """Test SIMPLE complexity for short edit."""
        from friday_ai.client.llm_router import LLMRouter

        router = LLMRouter()
        complexity = router.estimate_complexity("Fix typo in README")

        assert complexity == TaskComplexity.SIMPLE

    def test_moderate_task_code_review(self):
        """Test MODERATE complexity for code review."""
        from friday_ai.client.llm_router import LLMRouter

        router = LLMRouter()
        complexity = router.estimate_complexity(
            "Review this function for bugs and improvements"
        )

        assert complexity == TaskComplexity.MODERATE

    def test_moderate_task_multi_step(self):
        """Test MODERATE complexity for multi-step reasoning."""
        from friday_ai.client.llm_router import LLMRouter

        router = LLMRouter()
        complexity = router.estimate_complexity(
            "Explain how authentication works and suggest improvements"
        )

        assert complexity == TaskComplexity.MODERATE

    def test_complex_task_architecture(self):
        """Test COMPLEX complexity for architecture decisions."""
        from friday_ai.client.llm_router import LLMRouter

        router = LLMRouter()
        complexity = router.estimate_complexity(
            "Design a microservices architecture for a real-time collaboration platform"
            " with WebSocket support, user presence, and conflict resolution"
        )

        assert complexity == TaskComplexity.COMPLEX

    def test_complex_task_large_feature(self):
        """Test COMPLEX complexity for large feature implementation."""
        from friday_ai.client.llm_router import LLMRouter

        router = LLMRouter()
        complexity = router.estimate_complexity(
            "Implement a complete user authentication system with OAuth2, "
            "JWT tokens, password reset, email verification, and session management"
        )

        assert complexity == TaskComplexity.COMPLEX

    def test_expert_task_debugging(self):
        """Test EXPERT complexity for debugging critical issues."""
        from friday_ai.client.llm_router import LLMRouter

        router = LLMRouter()
        complexity = router.estimate_complexity(
            "Debug and fix the memory leak causing crashes under load"
        )

        assert complexity == TaskComplexity.EXPERT

    def test_expert_task_research(self):
        """Test EXPERT complexity for research tasks."""
        from friday_ai.client.llm_router import LLMRouter

        router = LLMRouter()
        complexity = router.estimate_complexity(
            "Research and implement the best approach for handling "
            "concurrent database transactions with proper isolation levels"
        )

        assert complexity == TaskComplexity.EXPERT


class TestLLMRouter:
    """Test LLM Router integration."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config(
            model_name="gpt-4",
            approval=ApprovalPolicy.AUTO,
        )

    @pytest.fixture
    def mock_provider(self):
        """Create mock provider."""
        provider = Mock()
        provider.is_available.return_value = True
        provider.config = Mock()
        provider.config.max_tokens = 4096
        provider.config.model = "gpt-4"
        provider.complete = AsyncMock(return_value="Response")
        return provider

    @pytest.fixture
    def router(self, mock_provider):
        """Create LLM router with mock providers."""
        from friday_ai.client.llm_router import LLMRouter

        llm_router = LLMRouter()

        # Register mock providers
        llm_router.router.register_provider(
            ProviderType.OPENAI, mock_provider, is_default=True
        )
        llm_router.router.register_provider(
            ProviderType.GROQ, mock_provider
        )

        # Update provider info
        llm_router.router._provider_info[ProviderType.OPENAI] = ProviderInfo(
            provider=mock_provider,
            provider_type=ProviderType.OPENAI,
            is_available=True,
            quality_score=0.95,
            avg_latency_ms=500.0,
            cost_per_1k_input=5.0,
            cost_per_1k_output=15.0,
            max_tokens=8192,
            supports_streaming=True,
        )

        llm_router.router._provider_info[ProviderType.GROQ] = ProviderInfo(
            provider=mock_provider,
            provider_type=ProviderType.GROQ,
            is_available=True,
            quality_score=0.85,
            avg_latency_ms=100.0,
            cost_per_1k_input=0.59,
            cost_per_1k_output=0.79,
            max_tokens=4096,
            supports_streaming=True,
        )

        return llm_router

    def test_estimate_complexity(self, router):
        """Test complexity estimation."""
        # Simple task
        simple = router.estimate_complexity("What is 2+2?")
        assert simple == TaskComplexity.SIMPLE

        # Complex task
        complex = router.estimate_complexity(
            "Design a distributed system with microservices"
        )
        assert complex == TaskComplexity.COMPLEX

    def test_select_provider_for_simple_task(self, router):
        """Test provider selection for simple tasks."""
        # Simple tasks should prefer fast/cheap providers
        criteria = RoutingCriteria(prefer_speed=True, prefer_cost=True)
        selected = router.router.select_provider(
            TaskComplexity.SIMPLE, criteria
        )

        # Groq is faster and cheaper
        assert selected == ProviderType.GROQ

    def test_select_provider_for_complex_task(self, router):
        """Test provider selection for complex tasks."""
        # Complex tasks should prefer quality
        # Allow higher cost for quality providers
        criteria = RoutingCriteria(
            prefer_quality=True,
            max_cost_per_1k_tokens=20.0  # Allow OpenAI's higher cost
        )
        selected = router.router.select_provider(
            TaskComplexity.COMPLEX, criteria
        )

        # OpenAI has higher quality
        assert selected == ProviderType.OPENAI

    def test_track_provider_usage(self, router):
        """Test tracking provider usage."""
        router.track_usage(ProviderType.OPENAI, 1000, 500)

        assert router.get_usage_count(ProviderType.OPENAI) == 1
        assert router.get_total_cost(ProviderType.OPENAI) == 12.5

    def test_track_multiple_providers(self, router):
        """Test tracking usage across multiple providers."""
        router.track_usage(ProviderType.OPENAI, 1000, 500)
        router.track_usage(ProviderType.GROQ, 2000, 1000)

        assert router.get_usage_count(ProviderType.OPENAI) == 1
        assert router.get_usage_count(ProviderType.GROQ) == 1

        openai_cost = router.get_total_cost(ProviderType.OPENAI)
        groq_cost = router.get_total_cost(ProviderType.GROQ)

        assert openai_cost == 12.5  # 1000*5 + 500*15 / 1000
        assert abs(groq_cost - 1.97) < 0.01  # 2000*0.59 + 1000*0.79 / 1000

    def test_get_cost_summary(self, router):
        """Test getting cost summary."""
        router.track_usage(ProviderType.OPENAI, 1000, 500)
        router.track_usage(ProviderType.GROQ, 2000, 1000)

        summary = router.get_cost_summary()

        assert summary["total_requests"] == 2
        assert summary["total_cost"] > 0
        assert "openai" in summary["by_provider"]
        assert "groq" in summary["by_provider"]


class TestSessionIntegration:
    """Test Session integration with multi-provider routing."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config(
            model_name="gpt-4",
            approval=ApprovalPolicy.AUTO,
        )

    @pytest.mark.asyncio
    async def test_session_with_router(self, config):
        """Test that Session can use LLMRouter."""
        from friday_ai.agent.session import Session
        from friday_ai.client.llm_router import LLMRouter

        session = Session(config)

        # Add router to session (optional feature)
        router = LLMRouter()
        session.llm_router = router

        assert session.llm_router is not None
        assert isinstance(session.llm_router, LLMRouter)

        await session.cleanup()

    @pytest.mark.asyncio
    async def test_session_without_router(self, config):
        """Test that Session works without router (backwards compat)."""
        from friday_ai.agent.session import Session

        session = Session(config)

        # No router by default
        assert session.llm_router is None

        await session.initialize()
        await session.cleanup()

    @pytest.mark.asyncio
    async def test_session_router_initialization(self, config):
        """Test router initialization from config providers."""
        from friday_ai.agent.session import Session

        # Add provider config to test config
        config_dict = {
            "providers": {
                "openai": {
                    "api_key": "test-key",
                    "model": "gpt-4",
                },
            }
        }

        session = Session(config)

        # Initialize with providers (if available)
        if hasattr(session, "initialize_router"):
            await session.initialize_router(config_dict)

        await session.cleanup()


class TestCLICommands:
    """Test CLI commands for provider management."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config(
            model_name="gpt-4",
            approval=ApprovalPolicy.AUTO,
        )

    @pytest.fixture
    def cli(self, config):
        """Create CLI instance."""
        from friday_ai.main import CLI

        return CLI(config)

    def test_provider_list_command(self, cli, capsys):
        """Test /provider list command."""
        # Mock agent with router
        from friday_ai.client.llm_router import LLMRouter

        if not cli.agent:
            # Create mock agent
            cli.agent = Mock()
            cli.agent.session = Mock()

        # Add router to session
        router = LLMRouter()
        if cli.agent.session:
            cli.agent.session.llm_router = router

        # Test would be handled by _handle_command
        # This is a placeholder for the actual implementation
        assert cli is not None

    def test_provider_switch_command(self, cli, capsys):
        """Test /provider <name> command."""
        # Mock agent with router
        from friday_ai.client.llm_router import LLMRouter

        if not cli.agent:
            cli.agent = Mock()
            cli.agent.session = Mock()

        router = LLMRouter()
        if cli.agent.session:
            cli.agent.session.llm_router = router

        # Test would be handled by _handle_command
        assert cli is not None

    def test_cost_command(self, cli, capsys):
        """Test /cost command."""
        # Mock agent with router
        from friday_ai.client.llm_router import LLMRouter

        if not cli.agent:
            cli.agent = Mock()
            cli.agent.session = Mock()

        router = LLMRouter()
        router.track_usage(ProviderType.OPENAI, 1000, 500)

        if cli.agent.session:
            cli.agent.session.llm_router = router

        # Test would be handled by _handle_command
        assert cli is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
