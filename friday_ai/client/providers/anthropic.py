"""Anthropic provider implementation."""

import json
from typing import Any, AsyncGenerator, Optional
import httpx
import logging

from friday_ai.client.providers.base import (
    BaseProvider,
    ChatMessage,
    ProviderConfig,
    ProviderRegistry,
    ProviderType,
    StreamingChunk,
)

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (as of 2024)
ANTHROPIC_PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-3-20250514": {"input": 0.25, "output": 1.25},
    "claude-opus-4-20250514": {"input": 30.0, "output": 75.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "default": {"input": 3.0, "output": 15.0},
}

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"


@ProviderRegistry.register(ProviderType.ANTHROPIC)
class AnthropicProvider(BaseProvider):
    """Anthropic provider implementation using Claude API."""

    def __init__(self, config: ProviderConfig):
        """Initialize the Anthropic provider.

        Args:
            config: Provider configuration.
        """
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None
        self._base_url = config.base_url or ANTHROPIC_BASE_URL
        self._pricing = ANTHROPIC_PRICING
        self._anthropic_version = "2023-06-01"

    async def initialize(self) -> None:
        """Initialize the Anthropic client."""
        if not self.config.api_key:
            raise ValueError("Anthropic API key is required")

        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": self._anthropic_version,
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(self.config.timeout)

        self.client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=timeout,
        )

        self._is_initialized = True
        logger.info(f"Anthropic provider initialized with model: {self.config.model}")

    async def shutdown(self) -> None:
        """Shutdown the Anthropic client."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self._is_initialized = False
        logger.info("Anthropic provider shutdown")

    async def complete(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
    ) -> AsyncGenerator[StreamingChunk, None] | str:
        """Generate a completion using Anthropic API.

        Args:
            messages: List of chat messages.
            stream: Whether to stream the response.

        Returns:
            Streaming generator or complete response string.
        """
        if not self.client:
            raise RuntimeError("Anthropic provider not initialized")

        # Convert messages to Anthropic format
        prompt = self._build_prompt(messages)

        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": stream,
        }

        if stream:
            return self._stream_response(payload)
        else:
            return await _non_stream_response(self.client, payload)

    def _build_prompt(self, messages: list[ChatMessage]) -> str:
        """Build prompt from chat messages for Anthropic.

        Args:
            messages: List of chat messages.

        Returns:
            Formatted prompt string.
        """
        prompt_parts = []
        for message in messages:
            if message.role == "system":
                prompt_parts.append(f"\n\nHuman: {message.content}\n\nAssistant: ")
            else:
                role = "Human" if message.role == "user" else "Assistant"
                prompt_parts.append(f"\n\n{role}: {message.content}")

        prompt_parts.append("\n\nAssistant:")
        return "".join(prompt_parts)

    async def _stream_response(
        self,
        payload: dict[str, Any],
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Stream response from Anthropic.

        Args:
            payload: Request payload.

        Yields:
            Streaming chunks.
        """
        async with self.client.stream(
            "POST",
            "/messages",
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    try:
                        chunk = json.loads(data)
                        if chunk.get("type") == "content_block_delta":
                            content = chunk.get("delta", {}).get("text", "")
                            if content:
                                yield StreamingChunk(content=content)
                        elif chunk.get("type") == "message_delta":
                            yield StreamingChunk(
                                content="",
                                finish_reason=chunk.get("delta", {}).get("stop_reason"),
                            )
                    except json.JSONDecodeError:
                        continue

    async def get_models(self) -> list[str]:
        """Get available Anthropic models.

        Returns:
            List of model identifiers.
        """
        # Anthropic doesn't have a models endpoint, return known models
        return list(self._pricing.keys())

    async def count_tokens(self, text: str) -> int:
        """Count tokens for Anthropic.

        Args:
            text: Input text.

        Returns:
            Estimated token count.
        """
        # Rough estimate: 4 characters per token
        return len(text) // 4

    def validate_config(self) -> bool:
        """Validate Anthropic configuration.

        Returns:
            True if configuration is valid.
        """
        if not self.config.api_key:
            return False
        return True

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Get cost estimate for Anthropic tokens.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Estimated cost in USD.
        """
        model = self.config.model or "default"
        pricing = self._pricing.get(model, self._pricing["default"])
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


async def _non_stream_response(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> str:
    """Get non-streamed response from Anthropic.

    Args:
        client: HTTP client.
        payload: Request payload.

    Returns:
        Response content.
    """
    response = await client.post("/messages", json=payload)
    response.raise_for_status()
    data = response.json()
    # Extract text from the first content block
    content_blocks = data.get("content", [])
    for block in content_blocks:
        if block.get("type") == "text":
            return block.get("text", "")
    return ""
