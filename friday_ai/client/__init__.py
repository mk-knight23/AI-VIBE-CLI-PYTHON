"""Friday AI Client module."""

from friday_ai.client.llm_client import LLMClient
from friday_ai.client.response import StreamEvent, TokenUsage, TextDelta, ToolCall, ToolCallDelta
from friday_ai.client.providers import (
    BaseProvider,
    ProviderConfig,
    ProviderType,
    ChatMessage,
    StreamingChunk,
    ProviderRegistry,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    GroqProvider,
    OllamaProvider,
)
from friday_ai.client.multi_provider import (
    ProviderRouter,
    ProviderManager,
    TaskComplexity,
    RoutingCriteria,
    ProviderInfo,
)

__all__ = [
    "LLMClient",
    "StreamEvent",
    "TokenUsage",
    "TextDelta",
    "ToolCall",
    "ToolCallDelta",
    # Providers
    "BaseProvider",
    "ProviderConfig",
    "ProviderType",
    "ChatMessage",
    "StreamingChunk",
    "ProviderRegistry",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "GroqProvider",
    "OllamaProvider",
    # Router
    "ProviderRouter",
    "ProviderManager",
    "TaskComplexity",
    "RoutingCriteria",
    "ProviderInfo",
]
