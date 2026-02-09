import asyncio
import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal, Any
from urllib.parse import urljoin

import httpx

from friday_ai.tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult


class HttpRequestParams(BaseModel):
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"] = Field(
        "GET", description="HTTP method"
    )
    url: str = Field(..., description="URL to request")
    headers: dict[str, str] | None = Field(None, description="HTTP headers")
    params: dict[str, str] | None = Field(None, description="Query parameters")
    body: str | None = Field(None, description="Request body (JSON or raw)")
    json_data: dict[str, Any] | None = Field(None, description="JSON body (alternative to body)")
    timeout: int = Field(30, ge=1, le=300, description="Timeout in seconds")
    follow_redirects: bool = Field(True, description="Follow redirects")
    max_response_size: int = Field(1024 * 1024, description="Max response size in bytes (default 1MB)")


class HttpTool(Tool):
    name = "http_request"
    kind = ToolKind.NETWORK
    description = """Make HTTP requests for API testing and web interaction.

Supports: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS

Examples:
- GET request: http_request method="GET" url="https://api.example.com/users"
- POST JSON: http_request method="POST" url="..." json_data={"name": "John"}
- With headers: http_request url="..." headers={"Authorization": "Bearer token"}
- Query params: http_request url="..." params={"page": "1", "limit": "10"}
"""

    schema = HttpRequestParams

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        params = HttpRequestParams(**invocation.params)

        # Mutating methods need confirmation
        if params.method in ["POST", "PUT", "DELETE", "PATCH"]:
            return ToolConfirmation(
                tool_name=self.name,
                params=invocation.params,
                description=f"HTTP {params.method} to {params.url}",
                is_dangerous=params.method in ["DELETE", "PUT"],
            )
        return None

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = HttpRequestParams(**invocation.params)

        # Prepare headers
        headers = params.headers or {}

        # Prepare body
        content = None
        if params.json_data is not None:
            content = json.dumps(params.json_data).encode('utf-8')
            if 'content-type' not in {k.lower(): v for k, v in headers.items()}:
                headers['Content-Type'] = 'application/json'
        elif params.body is not None:
            content = params.body.encode('utf-8')

        try:
            async with httpx.AsyncClient(
                timeout=params.timeout,
                follow_redirects=params.follow_redirects
            ) as client:
                response = await client.request(
                    method=params.method,
                    url=params.url,
                    headers=headers,
                    params=params.params,
                    content=content,
                )

                # Format response
                output_lines = [
                    f"Status: {response.status_code} {response.reason_phrase}",
                    f"URL: {response.url}",
                    f"Time: {response.elapsed.total_seconds():.3f}s",
                    "",
                    "Headers:",
                ]

                for name, value in response.headers.items():
                    output_lines.append(f"  {name}: {value}")

                output_lines.append("")
                output_lines.append("Body:")

                # Format body based on content type
                body = response.text
                content_type = response.headers.get('content-type', '')

                # Truncate if too large
                if len(body) > params.max_response_size:
                    body = body[:params.max_response_size] + "\n... [response truncated]"

                if 'application/json' in content_type:
                    try:
                        parsed = response.json()
                        formatted = json.dumps(parsed, indent=2)
                        output_lines.append(formatted)
                    except:
                        output_lines.append(body)
                else:
                    output_lines.append(body)

                output = "\n".join(output_lines)

                return ToolResult(
                    success=200 <= response.status_code < 300,
                    output=output,
                    error=None if response.status_code < 400 else f"HTTP {response.status_code}",
                    metadata={
                        "status_code": response.status_code,
                        "content_type": content_type,
                        "size": len(response.content),
                    }
                )

        except httpx.TimeoutException:
            return ToolResult.error_result(f"Request timed out after {params.timeout}s")
        except httpx.ConnectError as e:
            return ToolResult.error_result(f"Connection error: {e}")
        except Exception as e:
            return ToolResult.error_result(f"Request failed: {e}")


class HttpDownloadParams(BaseModel):
    url: str = Field(..., description="URL to download from")
    output_path: str = Field(..., description="Path to save file")
    timeout: int = Field(300, ge=1, le=600, description="Timeout in seconds")


class HttpDownloadTool(Tool):
    name = "http_download"
    kind = ToolKind.NETWORK
    description = """Download a file from a URL.

Example:
- http_download url="https://example.com/file.zip" output_path="./downloads/file.zip"
"""

    schema = HttpDownloadParams

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        params = HttpDownloadParams(**invocation.params)
        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Download {params.url} to {params.output_path}",
            is_dangerous=False,
        )

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = HttpDownloadParams(**invocation.params)

        output_path = Path(params.output_path)
        if not output_path.is_absolute():
            output_path = invocation.cwd / output_path

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            async with httpx.AsyncClient(timeout=params.timeout) as client:
                async with client.stream("GET", params.url, follow_redirects=True) as response:
                    if response.status_code != 200:
                        return ToolResult.error_result(
                            f"Download failed with status {response.status_code}"
                        )

                    total_size = 0
                    chunk_size = 8192

                    with open(output_path, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=chunk_size):
                            f.write(chunk)
                            total_size += len(chunk)

                    content_type = response.headers.get('content-type', 'unknown')
                    return ToolResult.success_result(
                        f"Downloaded {total_size:,} bytes to {output_path}\n"
                        f"Content-Type: {content_type}",
                        metadata={
                            "size": total_size,
                            "path": str(output_path),
                            "content_type": content_type,
                        }
                    )

        except httpx.TimeoutException:
            return ToolResult.error_result(f"Download timed out after {params.timeout}s")
        except Exception as e:
            return ToolResult.error_result(f"Download failed: {e}")
