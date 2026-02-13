from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from friday_ai.resilience.retry import with_retry
from friday_ai.tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from friday_ai.tools.builtin.http_client import get_http_client


class WebFetchParams(BaseModel):
    url: str = Field(..., description="URL to fetch (must be http:// or https://)")
    timeout: int = Field(
        30,
        ge=5,
        le=120,
        description="Request timeout in seconds (default: 120)",
    )


class WebFetchTool(Tool):
    name = "web_fetch"
    description = "Fetch content from a URL. Returns the response body as text"
    kind = ToolKind.NETWORK
    schema = WebFetchParams

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = WebFetchParams(**invocation.params)

        parsed = urlparse(params.url)
        if not parsed.scheme or parsed.scheme not in ("http", "https"):
            return ToolResult.error_result("Url must be http:// or https://")

        return await self._fetch_with_retry(params)

    @with_retry(
        max_retries=3,
        base_delay=1.0,
        retryable_exceptions=(httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError),
    )
    async def _fetch_with_retry(self, params: WebFetchParams) -> ToolResult:
        """Fetch URL with retry logic for transient failures."""
        return await self._fetch_once(params)

    async def _fetch_once(self, params: WebFetchParams) -> ToolResult:
        """Execute a single fetch request."""
        try:
            # Use shared HTTP client with connection pooling
            client = await get_http_client()

            # Create request with timeout included
            timeout = httpx.Timeout(params.timeout)
            request = client.build_request("GET", params.url, timeout=timeout)

            response = await client.send(request, follow_redirects=True)
            response.raise_for_status()
            text = response.text
        except httpx.HTTPStatusError as e:
            return ToolResult.error_result(
                f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
            )
        except Exception as e:
            return ToolResult.error_result(f"Request failed: {e}")

        if len(text) > 100 * 1024:
            text = text[: 100 * 1024] + "\n... [content truncated]"

        return ToolResult.success_result(
            text,
            metadata={
                "status_code": response.status_code,
                "content_length": len(response.content),
            },
        )
