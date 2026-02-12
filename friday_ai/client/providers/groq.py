"""Groq provider implementation."""

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
GROQ_PRICING = {
    "llama-3.1-70b-versatile": {"input": 0.59, "output": 0.79},
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama3-70b-8192": {"input": 0.59, "output": 0.79},
    "llama3-8b-8192": {"input": 0.05, "output": 0.08},
    "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
    "gemma-7b-it": {"input": 0.10, "output": 0.10},
    "default": {"input": 0.59, "output": 0.79},
}

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


@ProviderRegistry.register(ProviderType.GROQ)
class GroqProvider(BaseProvider):
    """Groq provider implementation using their OpenAI-compatible API."""

    def __init__(self, config: ProviderConfig):
        """Initialize the Groq provider.

        Args:
            config: Provider configuration.
        """
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None
        self._base_url = config.base_url or GROQ_BASE_URL
        self._pricing = GROQ_PRICING

    async def initialize(self) -> None:
        """Initialize the Groq client."""
        if not self.config.api_key:
            raise ValueError("Groq API key is required")

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(self.config.timeout)

        self.client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=timeout,
        )

        self._is_initialized = True
        logger.info(f"Groq provider initialized with model: {self.config.model}")

    async def shutdown(self) -> None:
        """Shutdown the Groq client."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self._is_initialized = False
        logger.info("Groq provider shutdown")

    async def complete(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
    ) -> AsyncGenerator[StreamingChunk, None] | str:
        """Generate a completion using Groq API.

        Args:
            messages: List of chat messages.
            stream: Whether to stream the response.

        Returns:
            Streaming generator or complete response string.
        """
        if not self.client:
            raise RuntimeError("Groq provider not initialized")

        payload = {
            "model": self.config.model,
            "messages": [self._format_message(m) for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": stream,
        }

        if stream:
            return self._stream_response(payload)
        else:
            return await _non_stream_response(self.client, payload)

    def _format_message(self, message: ChatMessage) -> dict[str, Any]:
        """Format a chat message for the API.

        Args:
            message: Chat message.

        Returns:
            Formatted message dict.
        """
        result = {"role": message.role, "content": message.content}
        if message.name:
            result["name"] = message.name
        return result

    async def _stream_response(
        self,
        payload: dict[str, Any],
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Stream response from Groq.

        Args:
            payload: Request payload.

        Yields:
            Streaming chunks.
        """
        async with self.client.stream(
            "POST",
            "/chat/completions",
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        finish_reason = chunk["choices"][0].get("finish_reason")
                        if content:
                            yield StreamingChunk(content=content, finish_reason=finish_reason)
                    except json.JSONDecodeError:
                        continue

    async def get_models(self) -> list[str]:
        """Get available Groq models.

        Returns:
            List of model identifiers.
        """
        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch models: {e}")
            return list(self._pricing.keys())

    async def count_tokens(self, text: str) -> int:
        """Count tokens for Groq.

        Args:
            text: Input text.

        Returns:
            Estimated token count.
        """
        return len(text) // 4

    def validate_config(self) -> bool:
        """Validate Groq configuration.

        Returns:
            True if configuration is valid.
        """
        if not self.config.api_key:
            return False
        return True

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Get cost estimate for Groq tokens.

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
    """Get non-streamed response from Groq.

    Args:
        client: HTTP client.
        payload: Request payload.

    Returns:
        Response content.
    """
    response = await client.post("/chat/completions", json=payload)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
