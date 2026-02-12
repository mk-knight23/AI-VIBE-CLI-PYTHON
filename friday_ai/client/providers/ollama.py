"""Ollama provider implementation for local LLM models."""

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

OLLAMA_BASE_URL = "http://localhost:11434"


@ProviderRegistry.register(ProviderType.OLLAMA)
class OllamaProvider(BaseProvider):
    """Ollama provider for running local LLMs."""

    def __init__(self, config: ProviderConfig):
        """Initialize the Ollama provider.

        Args:
            config: Provider configuration.
        """
        super().__init__(config)
        self.client: Optional[httpx.AsyncClient] = None
        self._base_url = config.base_url or OLLAMA_BASE_URL
        self._available_models: list[str] = []

    async def initialize(self) -> None:
        """Initialize the Ollama client."""
        timeout = httpx.Timeout(self.config.timeout)

        self.client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
        )

        # Check if Ollama is running
        try:
            await self._check_connection()
            await self._fetch_models()
            self._is_initialized = True
            logger.info(f"Ollama provider initialized with model: {self.config.model}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise

    async def _check_connection(self) -> None:
        """Check if Ollama is running."""
        response = await self.client.get("/api/version")
        response.raise_for_status()

    async def _fetch_models(self) -> None:
        """Fetch available models from Ollama."""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            self._available_models = [m["name"] for m in data.get("models", [])]
        except httpx.HTTPError:
            self._available_models = []

    async def shutdown(self) -> None:
        """Shutdown the Ollama client."""
        if self.client:
            await self.client.aclose()
            self.client = None
        self._is_initialized = False
        logger.info("Ollama provider shutdown")

    async def complete(
        self,
        messages: list[ChatMessage],
        stream: bool = False,
    ) -> AsyncGenerator[StreamingChunk, None] | str:
        """Generate a completion using Ollama.

        Args:
            messages: List of chat messages.
            stream: Whether to stream the response.

        Returns:
            Streaming generator or complete response string.
        """
        if not self.client:
            raise RuntimeError("Ollama provider not initialized")

        # Convert messages to Ollama format
        prompt = self._build_prompt(messages)

        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        if stream:
            return self._stream_response(payload)
        else:
            return await _non_stream_response(self.client, payload)

    def _build_prompt(self, messages: list[ChatMessage]) -> str:
        """Build prompt from chat messages for Ollama.

        Args:
            messages: List of chat messages.

        Returns:
            Formatted prompt string.
        """
        prompt_parts = []
        for message in messages:
            if message.role == "system":
                prompt_parts.append(f"System: {message.content}\n")
            elif message.role == "user":
                prompt_parts.append(f"User: {message.content}\n")
            else:
                prompt_parts.append(f"Assistant: {message.content}\n")
        prompt_parts.append("Assistant: ")
        return "".join(prompt_parts)

    async def _stream_response(
        self,
        payload: dict[str, Any],
    ) -> AsyncGenerator[StreamingChunk, None]:
        """Stream response from Ollama.

        Args:
            payload: Request payload.

        Yields:
            Streaming chunks.
        """
        async with self.client.stream(
            "POST",
            "/api/generate",
            json=payload,
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("response", "")
                        if content:
                            yield StreamingChunk(
                                content=content,
                                finish_reason="stop" if chunk.get("done") else None,
                            )
                    except json.JSONDecodeError:
                        continue

    async def get_models(self) -> list[str]:
        """Get available Ollama models.

        Returns:
            List of model identifiers.
        """
        if not self._available_models:
            await self._fetch_models()
        return self._available_models

    async def count_tokens(self, text: str) -> int:
        """Count tokens for Ollama.

        Args:
            text: Input text.

        Returns:
            Estimated token count.
        """
        # Rough estimate: 4 characters per token
        return len(text) // 4

    def validate_config(self) -> bool:
        """Validate Ollama configuration.

        Returns:
            True if configuration is valid.
        """
        # No API key needed for local Ollama
        return True

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Get cost estimate for Ollama.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.

        Returns:
            Cost is always 0 for local models.
        """
        return 0.0

    async def pull_model(self, model_name: str) -> None:
        """Pull a model from Ollama registry.

        Args:
            model_name: Name of the model to pull.
        """
        async with self.client.stream(
            "POST",
            "/api/pull",
            json={"name": model_name, "stream": True},
        ) as response:
            async for line in response.aiter_lines():
                # Optionally log progress
                pass

    async def delete_model(self, model_name: str) -> bool:
        """Delete a model from Ollama.

        Args:
            model_name: Name of the model to delete.

        Returns:
            True if deletion was successful.
        """
        try:
            response = await self.client.delete(
                "/api/delete",
                params={"name": model_name}
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False


async def _non_stream_response(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> str:
    """Get non-streamed response from Ollama.

    Args:
        client: HTTP client.
        payload: Request payload.

    Returns:
        Response content.
    """
    response = await client.post("/api/generate", json=payload)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")
