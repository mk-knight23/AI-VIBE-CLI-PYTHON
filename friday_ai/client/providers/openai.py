"""OpenAI provider implementation."""

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
OPENAI_PRICING = {
    "gpt-4o": {"input": 5.0, "output": 15.0},
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "default": {"input": 5.0, "output": 15.0},
}


@ProviderRegistry.register(ProviderType.OPENAI)
class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation using the Chat Completions API."""

    def __init__(self, config: ProviderConfig):
        """Initialize the OpenAI provider.

        Args:
            config: Provider configuration.
        """
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None
        self._base_url = config.base_url or "https://api.openai.com/v1"
        self._pricing = OPENAI_PRICING

    async def initialize(self) -> None:
        """Initialize the OpenAI client."""
        if not self.config.api_key:
            raise ValueError("OpenAI API key is required")

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
        logger.info(f"OpenAI provider initialized with model: {self.config.model}")

    async def shutdown(self) -> None:
        """Shutdown the OpenAI client."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self._is_initialized = False
        logger.info("OpenAI provider shutdown")

    async def complete(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
    ) -> AsyncGenerator[StreamingChunk, None] | str:
        """Generate a completion using OpenAI API.

        Args:
            messages: List of chat messages.
            stream: Whether to stream the response.

        Returns:
            Streaming generator or complete response string.
        """
        if not self.client:
            raise RuntimeError("OpenAI provider not initialized")

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

    async def _stream_response(
        self,
        payload: dict[str, Any],
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Stream response from OpenAI.

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
                        role = chunk["choices"][0]["delta"].get("role")
                        finish_reason = chunk["choices"][0].get("finish_reason")
                        if content:
                            yield StreamingChunk(
                                content=content,
                                role=role,
                                finish_reason=finish_reason,
                            )
                    except json.JSONDecodeError:
                        continue

    async def get_models(self) -> list[str]:
        """Get available OpenAI models.

        Returns:
            List of model identifiers.
        """
        if not self.client:
            raise RuntimeError("OpenAI provider not initialized")

        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [m["id"] for m in data.get("data", []) if "gpt" in m["id"].lower()]
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch models: {e}")
            # Return known models as fallback
            return list(self._pricing.keys())

    async def count_tokens(self, text: str) -> int:
        """Count tokens using OpenAI's tiktoken.

        For simplicity, we use a rough estimate (4 chars per token).

        Args:
            text: Input text.

        Returns:
            Estimated token count.
        """
        # For better accuracy, we would use tiktoken
        # import tiktoken
        # enc = tiktoken.encoding_for_model(self.config.model)
        # return len(enc.encode(text))
        return len(text) // 4

    def validate_config(self) -> bool:
        """Validate OpenAI configuration.

        Returns:
            True if configuration is valid.
        """
        if not self.config.api_key:
            return False
        if self.config.model and not isinstance(self.config.model, str):
            return False
        return True

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Get cost estimate for OpenAI tokens.

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


async def _non_stream_response(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> str:
    """Get non-streamed response from OpenAI.

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
