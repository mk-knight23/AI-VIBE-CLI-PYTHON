"""Multi-provider LLM router for intelligent provider selection."""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from friday_ai.client.providers.base import (
    BaseProvider,
    ChatMessage,
    ProviderConfig,
    ProviderRegistry,
    ProviderType,
    StreamingChunk,
)

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels for routing decisions."""

    SIMPLE = "simple"  # Basic Q&A, simple code edits
    MODERATE = "moderate"  # Multi-step reasoning, code reviews
    COMPLEX = "complex"  # Architecture decisions, long code generation
    EXPERT = "expert"  # Complex problem solving, research


@dataclass
class RoutingCriteria:
    """Criteria for selecting the best provider."""

    prefer_speed: bool = False
    prefer_cost: bool = False
    prefer_quality: bool = True
    max_cost_per_1k_tokens: float = 1.0
    min_quality_score: float = 0.5
    allow_local: bool = True
    fallback_providers: list[ProviderType] = field(default_factory=list)


@dataclass
class ProviderInfo:
    """Information about a provider."""

    provider: BaseProvider
    provider_type: ProviderType
    is_available: bool
    avg_latency_ms: float
    cost_per_1k_input: float
    cost_per_1k_output: float
    quality_score: float
    supports_streaming: bool
    max_tokens: int


class ProviderRouter:
    """Router for intelligently selecting the best LLM provider."""

    def __init__(self):
        """Initialize the provider router."""
        self._providers: dict[ProviderType, BaseProvider] = {}
        self._provider_info: dict[ProviderType, ProviderInfo] = {}
        self._default_provider: Optional[ProviderType] = None
        self._lock = asyncio.Lock()

    def register_provider(
        self,
        provider_type: ProviderType,
        provider: BaseProvider,
        is_default: bool = False,
    ) -> None:
        """Register a provider with the router.

        Args:
            provider_type: Type of the provider.
            provider: Provider instance.
            is_default: Whether this is the default provider.
        """
        self._providers[provider_type] = provider
        if is_default or self._default_provider is None:
            self._default_provider = provider_type
        logger.info(f"Registered provider: {provider_type.value}")

    def get_provider(self, provider_type: ProviderType) -> Optional[BaseProvider]:
        """Get a specific provider.

        Args:
            provider_type: Type of provider.

        Returns:
            Provider instance or None.
        """
        return self._providers.get(provider_type)

    def get_all_providers(self) -> dict[ProviderType, BaseProvider]:
        """Get all registered providers.

        Returns:
            Dictionary of provider types to instances.
        """
        return self._providers.copy()

    async def initialize_all(self) -> None:
        """Initialize all registered providers."""
        async with self._lock:
            for provider_type, provider in self._providers.items():
                try:
                    if not provider.is_available():
                        await provider.initialize()
                    self._update_provider_info(provider_type, provider)
                except Exception as e:
                    logger.error(f"Failed to initialize {provider_type}: {e}")

    async def shutdown_all(self) -> None:
        """Shutdown all registered providers."""
        for provider in self._providers.values():
            try:
                if provider.is_available():
                    await provider.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down provider: {e}")

    def _update_provider_info(
        self,
        provider_type: ProviderType,
        provider: BaseProvider,
    ) -> None:
        """Update provider information for routing.

        Args:
            provider_type: Type of provider.
            provider: Provider instance.
        """
        # Default values (will be updated with actual metrics)
        info = ProviderInfo(
            provider=provider,
            provider_type=provider_type,
            is_available=provider.is_available(),
            avg_latency_ms=500.0,  # Will be measured
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
            quality_score=0.8,
            supports_streaming=True,
            max_tokens=provider.config.max_tokens,
        )

        # Update from provider pricing
        if provider_type == ProviderType.OPENAI:
            # Import here to avoid circular dependency
            from friday_ai.client.providers.openai import OPENAI_PRICING
            pricing = OPENAI_PRICING.get(provider.config.model, OPENAI_PRICING["default"])
            info.cost_per_1k_input = pricing["input"]
            info.cost_per_1k_output = pricing["output"]
            info.quality_score = 0.95

        elif provider_type == ProviderType.ANTHROPIC:
            from friday_ai.client.providers.anthropic import ANTHROPIC_PRICING
            pricing = ANTHROPIC_PRICING.get(provider.config.model, ANTHROPIC_PRICING["default"])
            info.cost_per_1k_input = pricing["input"]
            info.cost_per_1k_output = pricing["output"]
            info.quality_score = 0.95

        elif provider_type == ProviderType.GOOGLE:
            from friday_ai.client.providers.google import GOOGLE_PRICING
            pricing = GOOGLE_PRICING.get(provider.config.model, GOOGLE_PRICING["default"])
            info.cost_per_1k_input = pricing["input"]
            info.cost_per_1k_output = pricing["output"]
            info.quality_score = 0.90

        elif provider_type == ProviderType.GROQ:
            from friday_ai.client.providers.groq import GROQ_PRICING
            pricing = GROQ_PRICING.get(provider.config.model, GROQ_PRICING["default"])
            info.cost_per_1k_input = pricing["input"]
            info.cost_per_1k_output = pricing["output"]
            info.quality_score = 0.85
            info.avg_latency_ms = 100.0  # Groq is fast

        elif provider_type == ProviderType.OLLAMA:
            info.cost_per_1k_input = 0.0
            info.cost_per_1k_output = 0.0
            info.quality_score = 0.75
            info.avg_latency_ms = 2000.0  # Local models can be slower

        self._provider_info[provider_type] = info

    def select_provider(
        self,
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        criteria: Optional[RoutingCriteria] = None,
    ) -> ProviderType:
        """Select the best provider based on criteria.

        Args:
            complexity: Task complexity level.
            criteria: Routing criteria.

        Returns:
            Selected provider type.
        """
        if criteria is None:
            criteria = RoutingCriteria()

        available_providers = [
            (pt, info)
            for pt, info in self._provider_info.items()
            if info.is_available
        ]

        if not available_providers:
            return self._default_provider or ProviderType.OPENAI

        # Filter by criteria
        filtered_providers = []
        for pt, info in available_providers:
            # Skip local if not allowed
            if pt == ProviderType.OLLAMA and not criteria.allow_local:
                continue

            # Skip if cost too high
            avg_cost = (info.cost_per_1k_input + info.cost_per_1k_output) / 2
            if avg_cost > criteria.max_cost_per_1k_tokens:
                continue

            # Skip if quality too low
            if info.quality_score < criteria.min_quality_score:
                continue

            filtered_providers.append((pt, info))

        if not filtered_providers:
            # Return cheapest available if none meet criteria
            filtered_providers = available_providers

        # Score and rank providers
        def score_provider(pt_info: tuple[ProviderType, ProviderInfo]) -> float:
            pt, info = pt_info
            score = 0.0

            # Adjust based on task complexity
            if complexity == TaskComplexity.SIMPLE:
                # Prefer fast, cheap providers
                if criteria.prefer_speed:
                    score += (1000 - info.avg_latency_ms) / 1000 * 0.4
                if criteria.prefer_cost:
                    score += (1.0 - info.cost_per_1k_output) * 0.4
                score += info.quality_score * 0.2

            elif complexity == TaskComplexity.MODERATE:
                # Balance of speed, cost, quality
                if criteria.prefer_speed:
                    score += (1000 - info.avg_latency_ms) / 1000 * 0.3
                if criteria.prefer_cost:
                    score += (1.0 - info.cost_per_1k_output) * 0.3
                score += info.quality_score * 0.4

            else:  # COMPLEX or EXPERT
                # Prefer quality
                score += info.quality_score * 0.6
                if criteria.prefer_speed:
                    score += (1000 - info.avg_latency_ms) / 1000 * 0.2
                if criteria.prefer_cost:
                    score += (1.0 - info.cost_per_1k_output) * 0.2

            # Boost for streaming support
            if info.supports_streaming:
                score += 0.05

            # Boost for higher max tokens on complex tasks
            if complexity in (TaskComplexity.COMPLEX, TaskComplexity.EXPERT):
                if info.max_tokens >= 16384:
                    score += 0.1
                elif info.max_tokens >= 8192:
                    score += 0.05

            return score

        # Sort by score and return best
        filtered_providers.sort(key=score_provider, reverse=True)

        # Apply fallback if primary fails
        if filtered_providers:
            return filtered_providers[0][0]

        return self._default_provider or ProviderType.OPENAI

    async def complete(
        self,
        messages: list[ChatMessage],
        complexity: TaskComplexity = TaskComplexity.MODERATE,
        criteria: Optional[RoutingCriteria] = None,
        provider_type: Optional[ProviderType] = None,
        stream: bool = False,
    ) -> Any:
        """Generate a completion using the best (or specified) provider.

        Args:
            messages: List of chat messages.
            complexity: Task complexity level.
            criteria: Routing criteria.
            provider_type: Specific provider to use (overrides routing).
            stream: Whether to stream the response.

        Returns:
            Response from provider.
        """
        if provider_type is None:
            provider_type = self.select_provider(complexity, criteria)
        else:
            provider_type = provider_type

        provider = self._providers.get(provider_type)
        if provider is None:
            raise ValueError(f"Provider {provider_type} is not registered")

        if not provider.is_available():
            raise RuntimeError(f"Provider {provider_type} is not available")

        return await provider.complete(messages, stream=stream)

    def estimate_cost(
        self,
        provider_type: ProviderType,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for a provider.

        Args:
            provider_type: Provider type.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        info = self._provider_info.get(provider_type)
        if info is None:
            return 0.0

        return (
            (input_tokens / 1000) * info.cost_per_1k_input +
            (output_tokens / 1000) * info.cost_per_1k_output
        )

    def get_provider_status(self) -> dict[str, Any]:
        """Get status of all providers.

        Returns:
            Dictionary with provider status information.
        """
        status = {
            "default": self._default_provider.value if self._default_provider else None,
            "providers": {},
        }

        for pt, info in self._provider_info.items():
            status["providers"][pt.value] = {
                "available": info.is_available,
                "latency_ms": info.avg_latency_ms,
                "cost_per_1k_input": info.cost_per_1k_input,
                "cost_per_1k_output": info.cost_per_1k_output,
                "quality_score": info.quality_score,
                "streaming": info.supports_streaming,
                "max_tokens": info.max_tokens,
                "model": info.provider.config.model,
            }

        return status


class ProviderManager:
    """Manager for creating and configuring providers from config."""

    def __init__(self):
        """Initialize the provider manager."""
        self.router = ProviderRouter()

    def create_provider(
        self,
        provider_type: ProviderType,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        is_default: bool = False,
    ) -> BaseProvider:
        """Create and register a provider.

        Args:
            provider_type: Type of provider.
            api_key: API key (optional for Ollama).
            base_url: Base URL (optional).
            model: Model name.
            temperature: Temperature setting.
            max_tokens: Max tokens.
            is_default: Whether this is the default provider.

        Returns:
            Created provider instance.
        """
        config = ProviderConfig(
            provider_type=provider_type,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        provider = ProviderRegistry.create_provider(config)
        self.router.register_provider(provider_type, provider, is_default=is_default)

        return provider

    def from_config(self, config_dict: dict[str, Any]) -> None:
        """Create providers from configuration dictionary.

        Args:
            config_dict: Configuration with providers settings.
        """
        # Set default provider
        default = config_dict.get("default", "openai")

        for name, settings in config_dict.get("providers", {}).items():
            try:
                provider_type = ProviderType(name)
                api_key = settings.get("api_key")
                base_url = settings.get("base_url")
                model = settings.get("model", "default")
                temperature = settings.get("temperature", 0.7)
                max_tokens = settings.get("max_tokens", 4096)
                is_default = name == default

                self.create_provider(
                    provider_type=provider_type,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    is_default=is_default,
                )
            except ValueError as e:
                logger.warning(f"Unknown provider type: {name}, {e}")

    async def initialize(self) -> None:
        """Initialize all registered providers."""
        await self.router.initialize_all()

    async def shutdown(self) -> None:
        """Shutdown all providers."""
        await self.router.shutdown_all()

    @property
    def router(self) -> ProviderRouter:
        """Get the provider router."""
        return self._router

    @router.setter
    def router(self, value: ProviderRouter) -> None:
        """Set the provider router."""
        self._router = value
