"""Tests for multi-provider LLM support."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from friday_ai.client.providers.base import (
    ProviderConfig,
    ProviderType,
    ChatMessage,
    ProviderRegistry,
)
from friday_ai.client.providers.openai import OpenAIProvider
from friday_ai.client.providers.anthropic import AnthropicProvider
from friday_ai.client.providers.groq import GroqProvider
from friday_ai.client.multi_provider import (
    ProviderRouter,
    ProviderManager,
    TaskComplexity,
    RoutingCriteria,
)


class TestProviderConfig:
    """Test provider configuration."""

    def test_provider_config_creation(self):
        """Test creating a provider config."""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2000,
        )

        assert config.provider_type == ProviderType.OPENAI
        assert config.api_key == "test-key"
        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000


class TestProviderRegistry:
    """Test provider registry."""

    def test_get_provider_class(self):
        """Test getting provider class from registry."""
        provider_class = ProviderRegistry.get_provider_class(ProviderType.OPENAI)
        assert provider_class == OpenAIProvider

    def test_create_provider(self):
        """Test creating provider from config."""
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            model="gpt-4",
        )

        provider = ProviderRegistry.create_provider(config)
        assert isinstance(provider, OpenAIProvider)
        assert provider.config == config


class TestProviderRouter:
    """Test provider router."""

    @pytest.fixture
    def router(self):
        return ProviderRouter()

    @pytest.fixture
    def mock_provider(self):
        provider = Mock()
        provider.is_available.return_value = True
        provider.config = Mock()
        provider.config.max_tokens = 4096
        provider.config.model = "gpt-4"
        return provider

    def test_register_provider(self, router, mock_provider):
        """Test registering a provider."""
        router.register_provider(ProviderType.OPENAI, mock_provider)

        assert ProviderType.OPENAI in router._providers
        assert router._providers[ProviderType.OPENAI] == mock_provider

    def test_select_provider_simple_task(self, router, mock_provider):
        """Test provider selection for simple tasks."""
        # Register providers
        router.register_provider(ProviderType.OPENAI, mock_provider)
        router.register_provider(ProviderType.GROQ, mock_provider)

        # Update provider info manually for testing
        from friday_ai.client.multi_provider import ProviderInfo

        router._provider_info[ProviderType.OPENAI] = ProviderInfo(
            provider=mock_provider,
            provider_type=ProviderType.OPENAI,
            is_available=True,
            quality_score=0.95,
            avg_latency_ms=500.0,
            cost_per_1k_input=5.0,
            cost_per_1k_output=15.0,
            max_tokens=4096,
            supports_streaming=True,
        )

        router._provider_info[ProviderType.GROQ] = ProviderInfo(
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

        # Simple tasks should prefer fast/cheap providers
        criteria = RoutingCriteria(prefer_speed=True, prefer_cost=True)
        selected = router.select_provider(TaskComplexity.SIMPLE, criteria)

        # Groq is faster and cheaper
        assert selected == ProviderType.GROQ

    def test_estimate_cost(self, router, mock_provider):
        """Test cost estimation."""
        router.register_provider(ProviderType.OPENAI, mock_provider)

        # Setup provider info
        router._provider_info[ProviderType.OPENAI] = Mock()
        router._provider_info[ProviderType.OPENAI].cost_per_1k_input = 5.0
        router._provider_info[ProviderType.OPENAI].cost_per_1k_output = 15.0

        cost = router.estimate_cost(ProviderType.OPENAI, 1000, 500)

        # (1000/1000)*5 + (500/1000)*15 = 5 + 7.5 = 12.5
        assert cost == 12.5


class TestProviderManager:
    """Test provider manager."""

    @pytest.fixture
    def manager(self):
        return ProviderManager()

    def test_create_provider(self, manager):
        """Test creating a provider."""
        provider = manager.create_provider(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            model="gpt-4",
            is_default=True,
        )

        assert provider is not None
        assert manager.router._default_provider == ProviderType.OPENAI

    def test_from_config(self, manager):
        """Test loading providers from config dict."""
        config = {
            "default": "openai",
            "providers": {
                "openai": {
                    "api_key": "test-key",
                    "model": "gpt-4",
                },
                "anthropic": {
                    "api_key": "test-key",
                    "model": "claude-3",
                },
            },
        }

        manager.from_config(config)

        assert ProviderType.OPENAI in manager.router._providers
        assert ProviderType.ANTHROPIC in manager.router._providers
        assert manager.router._default_provider == ProviderType.OPENAI


class TestOpenAIProvider:
    """Test OpenAI provider."""

    @pytest.fixture
    def provider(self):
        config = ProviderConfig(
            provider_type=ProviderType.OPENAI,
            api_key="test-key",
            model="gpt-4",
        )
        return OpenAIProvider(config)

    def test_validate_config(self, provider):
        """Test config validation."""
        assert provider.validate_config() is True

        # Test without API key
        provider.config.api_key = None
        assert provider.validate_config() is False

    def test_get_cost_estimate(self, provider):
        """Test cost estimation."""
        # gpt-4 pricing: input=$30/M, output=$60/M
        provider.config.model = "gpt-4"
        cost = provider.get_cost_estimate(1_000_000, 500_000)

        # (1M/1M)*30 + (0.5M/1M)*60 = 30 + 30 = 60
        assert cost == 60.0

    def test_format_message(self, provider):
        """Test message formatting."""
        from friday_ai.client.providers.base import ChatMessage

        message = ChatMessage(role="user", content="Hello", name="test")
        result = provider._format_message(message)

        assert result == {"role": "user", "content": "Hello", "name": "test"}


class TestGroqProvider:
    """Test Groq provider."""

    @pytest.fixture
    def provider(self):
        config = ProviderConfig(
            provider_type=ProviderType.GROQ,
            api_key="test-key",
            model="llama-3.1-70b",
        )
        return GroqProvider(config)

    def test_validate_config(self, provider):
        """Test config validation."""
        assert provider.validate_config() is True

    def test_get_cost_estimate(self, provider):
        """Test cost estimation."""
        # llama-3.1-70b pricing: input=$0.59/M, output=$0.79/M
        provider.config.model = "llama-3.1-70b-versatile"
        cost = provider.get_cost_estimate(1_000_000, 500_000)

        # (1M/1M)*0.59 + (0.5M/1M)*0.79 = 0.59 + 0.395 = 0.985
        assert abs(cost - 0.985) < 0.001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
