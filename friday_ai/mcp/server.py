"""MCP Server implementation for Friday AI.

Implements Friday as an MCP (Model Context Protocol) server,
allowing external tools to use Friday's capabilities.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncGenerator

from friday_ai.config.config import Config

if TYPE_CHECKING:
    from friday_ai.agent.agent import Agent

logger = logging.getLogger(__name__)


class TransportType(Enum):
    """MCP transport types."""
    STDIO = "stdio"
    SSE = "sse"


@dataclass
class MCPResource:
    """An MCP resource (file, data, etc.)."""

    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPTool:
    """An MCP tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: callable


@dataclass
class MCPMessage:
    """An MCP message."""

    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str | None = None
    params: dict[str, Any] | None = None
    result: Any | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        msg = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            msg["id"] = self.id
        if self.method is not None:
            msg["method"] = self.method
        if self.params is not None:
            msg["params"] = self.params
        if self.result is not None:
            msg["result"] = self.result
        if self.error is not None:
            msg["error"] = self.error
        return msg


class MCPServer:
    """MCP Server for Friday AI."""

    def __init__(
        self,
        config: Config,
        transport: TransportType = TransportType.STDIO,
    ):
        """Initialize the MCP server.

        Args:
            config: Friday configuration.
            transport: Transport type (stdio or sse).
        """
        self.config = config
        self.transport = transport
        self.tools: dict[str, MCPTool] = {}
        self.resources: dict[str, MCPResource] = {}
        self.prompts: dict[str, dict[str, Any]] = {}

        # Register built-in tools
        self._register_built_in_tools()

    def _register_built_in_tools(self) -> None:
        """Register built-in Friday tools as MCP tools."""
        from friday_ai.tools.base import ToolRegistry

        registry = ToolRegistry()

        for tool_name, tool_class in registry.get_all_tools().items():
            tool = tool_class(self.config)

            # Convert to MCP tool format
            self.tools[tool_name] = MCPTool(
                name=tool_name,
                description=tool.description,
                input_schema=self._tool_to_input_schema(tool),
                handler=self._create_tool_handler(tool),
            )

    def _tool_to_input_schema(self, tool: Any) -> dict[str, Any]:
        """Convert Friday tool to MCP input schema.

        Args:
            tool: The Friday tool instance.

        Returns:
            JSON Schema for the tool input.
        """
        schema = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for param in tool.parameters:
            prop_schema = {"type": param.type, "description": param.description}
            schema["properties"][param.name] = prop_schema
            if param.required:
                schema["required"].append(param.name)

        return schema

    def _create_tool_handler(self, tool: Any) -> callable:
        """Create an async handler for the tool.

        Args:
            tool: The Friday tool instance.

        Returns:
            Async callable that executes the tool.
        """
        async def handler(**kwargs: Any) -> str:
            from friday_ai.tools.base import ToolInvocation

            invocation = ToolInvocation(params=kwargs, cwd=Path.cwd())
            result = await tool.execute(invocation)

            if result.success:
                return result.output or "Tool executed successfully"
            else:
                raise Exception(result.error or "Tool execution failed")

        return handler

    def register_tool(self, tool: MCPTool) -> None:
        """Register a custom tool.

        Args:
            tool: The MCP tool to register.
        """
        self.tools[tool.name] = tool
        logger.info(f"Registered MCP tool: {tool.name}")

    def register_resource(self, resource: MCPResource) -> None:
        """Register a resource.

        Args:
            resource: The MCP resource to register.
        """
        self.resources[resource.uri] = resource
        logger.info(f"Registered MCP resource: {resource.uri}")

    def register_prompt(self, name: str, prompt: dict[str, Any]) -> None:
        """Register a prompt template.

        Args:
            name: Prompt name.
            prompt: Prompt definition.
        """
        self.prompts[name] = prompt
        logger.info(f"Registered MCP prompt: {name}")

    async def handle_message(self, message: MCPMessage) -> MCPMessage:
        """Handle an incoming MCP message.

        Args:
            message: The MCP message to handle.

        Returns:
            Response message.
        """
        try:
            if message.method == "initialize":
                return await self._handle_initialize(message)
            elif message.method == "tools/list":
                return await self._handle_tools_list(message)
            elif message.method == "tools/call":
                return await self._handle_tools_call(message)
            elif message.method == "resources/list":
                return await self._handle_resources_list(message)
            elif message.method == "resources/read":
                return await self._handle_resources_read(message)
            elif message.method == "prompts/list":
                return await self._handle_prompts_list(message)
            elif message.method == "prompts/get":
                return await self._handle_prompts_get(message)
            else:
                return MCPMessage(
                    id=message.id,
                    error={
                        "code": -32601,
                        "message": f"Method not found: {message.method}",
                    },
                )

        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            return MCPMessage(
                id=message.id,
                error={
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                },
            )

    async def _handle_initialize(self, message: MCPMessage) -> MCPMessage:
        """Handle initialize request.

        Args:
            message: The initialize message.

        Returns:
            Server capabilities.
        """
        params = message.params or {}
        client_info = params.get("clientInfo", {})

        logger.info(f"MCP client connected: {client_info.get('name', 'unknown')}")

        return MCPMessage(
            id=message.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
                "serverInfo": {
                    "name": "friday-ai-teammate",
                    "version": "0.3.0",
                },
            },
        )

    async def _handle_tools_list(self, message: MCPMessage) -> MCPMessage:
        """Handle tools/list request.

        Args:
            message: The tools/list message.

        Returns:
            List of available tools.
        """
        tools_list = []
        for tool_name, tool in self.tools.items():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            })

        return MCPMessage(
            id=message.id,
            result={"tools": tools_list},
        )

    async def _handle_tools_call(self, message: MCPMessage) -> MCPMessage:
        """Handle tools/call request.

        Args:
            message: The tools/call message.

        Returns:
            Tool execution results.
        """
        params = message.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return MCPMessage(
                id=message.id,
                error={
                    "code": -32602,
                    "message": f"Tool not found: {tool_name}",
                },
            )

        tool = self.tools[tool_name]

        try:
            result = await tool.handler(**arguments)
            return MCPMessage(
                id=message.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": result,
                        }
                    ]
                },
            )
        except Exception as e:
            return MCPMessage(
                id=message.id,
                error={
                    "code": -32603,
                    "message": f"Tool execution error: {str(e)}",
                },
            )

    async def _handle_resources_list(self, message: MCPMessage) -> MCPMessage:
        """Handle resources/list request.

        Args:
            message: The resources/list message.

        Returns:
            List of available resources.
        """
        resources_list = []
        for uri, resource in self.resources.items():
            resources_list.append({
                "uri": uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mime_type,
            })

        return MCPMessage(
            id=message.id,
            result={"resources": resources_list},
        )

    async def _handle_resources_read(self, message: MCPMessage) -> MCPMessage:
        """Handle resources/read request.

        Args:
            message: The resources/read message.

        Returns:
            Resource content.
        """
        params = message.params or {}
        uri = params.get("uri")

        if uri not in self.resources:
            return MCPMessage(
                id=message.id,
                error={
                    "code": -32602,
                    "message": f"Resource not found: {uri}",
                },
            )

        resource = self.resources[uri]

        # Read resource content
        if "metadata" in resource.metadata and "path" in resource.metadata:
            path = Path(resource.metadata["path"])
            if path.exists():
                content = path.read_text()
                return MCPMessage(
                    id=message.id,
                    result={
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": resource.mime_type,
                                "text": content,
                            }
                        ]
                    },
                )

        return MCPMessage(
            id=message.id,
            error={
                "code": -32603,
                "message": f"Could not read resource: {uri}",
            },
        )

    async def _handle_prompts_list(self, message: MCPMessage) -> MCPMessage:
        """Handle prompts/list request.

        Args:
            message: The prompts/list message.

        Returns:
            List of available prompts.
        """
        prompts_list = []
        for name, prompt in self.prompts.items():
            prompts_list.append({
                "name": name,
                "description": prompt.get("description", ""),
            })

        return MCPMessage(
            id=message.id,
            result={"prompts": prompts_list},
        )

    async def _handle_prompts_get(self, message: MCPMessage) -> MCPMessage:
        """Handle prompts/get request.

        Args:
            message: The prompts/get message.

        Returns:
            Prompt template.
        """
        params = message.params or {}
        name = params.get("name")
        arguments = params.get("arguments", {})

        if name not in self.prompts:
            return MCPMessage(
                id=message.id,
                error={
                    "code": -32602,
                    "message": f"Prompt not found: {name}",
                },
            )

        prompt = self.prompts[name]

        # Build prompt from template
        template = prompt.get("template", "")
        messages = prompt.get("messages", [])

        # Apply arguments to template
        if arguments:
            for key, value in arguments.items():
                template = template.replace(f"{{{{{key}}}}}", value)

        return MCPMessage(
            id=message.id,
            result={
                "description": prompt.get("description", ""),
                "messages": [
                    {
                        "role": msg.get("role", "user"),
                        "content": {
                            "type": "text",
                            "text": template,
                        },
                    }
                    for msg in messages
                ],
            },
        )

    async def run_stdio(self) -> None:
        """Run the MCP server with stdio transport.

        Reads messages from stdin, writes responses to stdout.
        """
        logger.info("Starting MCP server (stdio transport)")

        import sys

        while True:
            try:
                # Read message from stdin
                line = sys.stdin.readline()
                if not line:
                    break

                # Parse JSON message
                data = json.loads(line)
                message = MCPMessage(
                    id=data.get("id"),
                    method=data.get("method"),
                    params=data.get("params"),
                )

                # Handle message
                response = await self.handle_message(message)

                # Write response
                response_line = json.dumps(response.to_dict())
                sys.stdout.write(response_line + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                continue
            except Exception as e:
                logger.exception(f"Error in stdio loop: {e}")
                break

    async def run_sse(self, host: str = "localhost", port: int = 8000) -> None:
        """Run the MCP server with SSE transport.

        Args:
            host: Host to bind to.
            port: Port to bind to.
        """
        from aiohttp import web

        logger.info(f"Starting MCP server (SSE transport) on {host}:{port}")

        app = web.Application()

        async def handle_sse(request: web.Request) -> web.Response:
            """Handle SSE connection."""
            response = web.Response(
                content_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
            )

            async def send_events():
                # Send initial connection event
                yield f"event: connected\ndata: {json.dumps({'server': 'friday-ai'})}\n\n"

                # Keep connection alive
                while True:
                    await asyncio.sleep(10)
                    yield ": keepalive\n\n"

            response.body = send_events()
            return response

        async def handle_message(request: web.Request) -> web.Response:
            """Handle MCP message over HTTP."""
            data = await request.json()

            message = MCPMessage(
                id=data.get("id"),
                method=data.get("method"),
                params=data.get("params"),
            )

            response = await self.handle_message(message)

            return web.json_response(response.to_dict())

        app.router.add_get("/sse", handle_sse)
        app.router.add_post("/message", handle_message)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        logger.info(f"MCP server listening on http://{host}:{port}")

        try:
            # Run forever
            await asyncio.Future()
        except asyncio.CancelledError:
            logger.info("MCP server shutting down")
        finally:
            await runner.cleanup()


async def start_mcp_server(
    config: Config,
    transport: TransportType = TransportType.STDIO,
    **kwargs: Any,
) -> None:
    """Start the MCP server.

    Args:
        config: Friday configuration.
        transport: Transport type.
        **kwargs: Additional arguments (host, port for SSE).
    """
    server = MCPServer(config, transport)

    if transport == TransportType.STDIO:
        await server.run_stdio()
    else:
        await server.run_sse(**kwargs)
