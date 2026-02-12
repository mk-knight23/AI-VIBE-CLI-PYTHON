"""Google provider implementation."""

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
GOOGLE_PRICING = {
    "gemini-1.5-pro": {"input": 0.35, "output": 1.05},
    "gemini-1.5-flash": {"input": 0.035, "output": 0.105},
    "gemini-1.0-pro": {"input": 0.5, "output": 1.5},
    "default": {"input": 0.35, "output": 1.05},
}

GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


@ProviderRegistry.register(ProviderType.GOOGLE)
class GoogleProvider(BaseProvider):
    """Google provider implementation using Gemini API."""

    def __init__(self, config: ProviderConfig):
        """Initialize the Google provider.

        Args:
            config: Provider configuration.
        """
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None
        self._base_url = config.base_url or GOOGLE_BASE_URL
        self._pricing = GOOGLE_PRICING

    async def initialize(self) -> None:
        """Initialize the Google client."""
        if not self.config.api_key:
            raise ValueError("Google API key is required")

        timeout = httpx.Timeout(self.config.timeout)

        self.client = httpx.AsyncClient(
            timeout=timeout,
        )

        self._is_initialized = True
        logger.info(f"Google provider initialized with model: {self.config.model}")

    async def shutdown(self) -> None:
        """Shutdown the Google client."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self._is_initialized = False
        logger.info("Google provider shutdown")

    async def complete(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
    ) -> AsyncGenerator[StreamingChunk, None] | str:
        """Generate a completion using Google Gemini API.

        Args:
            messages: List of chat messages.
            stream: Whether to stream the response.

        Returns:
            Streaming generator or complete response string.
        """
        if not self.client:
            raise RuntimeError("Google provider not initialized")

        # Convert messages to Gemini format
        contents = self._build_contents(messages)

        url = f"{self._base_url}/models/{self.config.model}:generateContent"
        params = {"key": self.config.api_key}

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_tokens,
            },
        }

        if stream:
            return self._stream_response(url, params, payload)
        else:
            return await _non_stream_response(self.client, url, params, payload)

    def _build_contents(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        """Build contents list from chat messages for Gemini.

        Args:
            messages: List of chat messages.

        Returns:
            List of content dicts.
        """
        contents = []
        for message in messages:
            role = "user" if message.role == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": message.content}]
            })
        return contents

    async def _stream_response(
        self,
        url: str,
        params: dict[str, Any],
        payload: dict[str, Any],
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Stream response from Google.

        Args:
            url: API URL.
            params: Query parameters.
            payload: Request payload.

        Yields:
            Streaming chunks.
        """
        stream_url = f"{url}:streamGenerateContent"
        async with self.client.stream(
            "POST",
            stream_url,
            params=params,
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("candidates", [{}])[0].get("content", {})
                        parts = content.get("parts", [{}])
                        text = parts[0].get("text", "") if parts else ""
                        if text:
                            yield StreamingChunk(content=text)
                    except (json.JSONDecodeError, IndexError):
                        continue

    async def get_models(self) -> list[str]:
        """Get available Google models.

        Returns:
            List of model identifiers.
        """
        try:
            url = f"{self._base_url}/models?key={self.config.api_key}"
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return [m["name"].split("/")[-1] for m in data.get("models", [])]
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch models: {e}")
            return list(self._pricing.keys())

    async def count_tokens(self, text: str) -> int:
        """Count tokens for Google.

        Args:
            text: Input text.

        Returns:
            Estimated token count.
        """
        # Rough estimate: 4 characters per token
        return len(text) // 4

    def validate_config(self) -> bool:
        """Validate Google configuration.

        Returns:
            True if configuration is valid.
        """
        if not self.config.api_key:
            return False
        return True

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Get cost estimate for Google tokens.

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
    url: str,
    params: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    """Get non-streamed response from Google.

    Args:
        client: HTTP client.
        url: API URL.
        params: Query parameters.
        payload: Request payload.

    Returns:
        Response content.
    """
    response = await client.post(url, params=params, json=payload)
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates", [{}])
    content = candidates[0].get("content", {})
    parts = content.get("parts", [{}])
    return parts[0].get("text", "") if parts else ""
