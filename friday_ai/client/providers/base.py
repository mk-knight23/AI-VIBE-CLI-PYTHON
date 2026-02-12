"""Base provider class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Supported LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    OLLAMA = "ollama"
    LOCAL = "local"


@dataclass
class ProviderConfig:
    """Base configuration for all LLM providers."""

    provider_type: ProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    retry_attempts: int = 3
    system_prompt: Optional[str] = None


@dataclass
class ChatMessage:
    """A chat message."""

    role: str  # "user", "assistant", "system"
    content: str
    name: Optional[str] = None


@dataclass
class StreamingChunk:
    """A streaming response chunk."""

    content: str
    role: Optional[str] = None
    finish_reason: Optional[str] = None


class BaseProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, config: ProviderConfig):
        """Initialize the provider.

        Args:
            config: Provider configuration.
        """
        self.config = config
        self._is_initialized = False

    @property
    def provider_type(self) -> ProviderType:
        """Get the provider type."""
        return self.config.provider_type

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider (e.g., establish connection)."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the provider and release resources."""
        pass

    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
    ) -> AsyncGenerator[StreamingChunk, None] | str:
        """Generate a completion for the given messages.

        Args:
            messages: List of chat messages.
            stream: Whether to stream the response.

        Returns:
            Streaming generator or complete response string.
        """
        pass

    @abstractmethod
    async def get_models(self) -> list[str]:
        """Get available models for this provider.

        Returns:
            List of model identifiers.
        """
        pass

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Input text.

        Returns:
            Token count.
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration.

        Returns:
            True if configuration is valid.
        """
        pass

    def is_available(self) -> bool:
        """Check if the provider is available.

        Returns:
            True if provider can be used.
        """
        return self._is_initialized

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Get cost estimate for tokens.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        return 0.0  # Default implementation


class ProviderRegistry:
    """Registry for managing LLM providers."""

    _providers: dict[ProviderType, type[BaseProvider]] = {}

    @classmethod
    def register(cls, provider_type: ProviderType):
        """Decorator to register a provider class.

        Args:
            provider_type: Type to register the provider as.
        """
        def decorator(provider_class: type[BaseProvider]):
            cls._providers[provider_type] = provider_class
            return provider_class
        return decorator

    @classmethod
    def get_provider_class(cls, provider_type: ProviderType) -> type[BaseProvider]:
        """Get the provider class for a given type.

        Args:
            provider_type: Provider type.

        Returns:
            Provider class.

        Raises:
            ValueError: If provider type is not registered.
        """
        if provider_type not in cls._providers:
            raise ValueError(f"Provider type {provider_type} is not registered")
        return cls._providers[provider_type]

    @classmethod
    def create_provider(cls, config: ProviderConfig) -> BaseProvider:
        """Create a provider instance from configuration.

        Args:
            config: Provider configuration.

        Returns:
            Provider instance.
        """
        provider_class = cls.get_provider_class(config.provider_type)
        return provider_class(config)

    @classmethod
    def registered_types(cls) -> list[ProviderType]:
        """Get all registered provider types.

        Returns:
            List of registered types.
        """
        return list(cls._providers.keys())
