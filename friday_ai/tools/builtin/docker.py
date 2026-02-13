"""Docker tool for container management operations."""

from __future__ import annotations

import json
import logging
import re
import shlex
from typing import Any

from friday_ai.tools.base import Tool, ToolInvocation, ToolResult

logger = logging.getLogger(__name__)


class DockerTool(Tool):
    """Tool for Docker container management operations."""

    name = "docker"
    description = (
        "Execute Docker commands for container management (ps, logs, exec, build, compose)"
    )

    @property
    def schema(self) -> dict[str, Any]:
        """Get tool schema."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": [
                        "ps",
                        "logs",
                        "exec",
                        "build",
                        "images",
                        "inspect",
                        "stats",
                        "compose_ps",
                        "compose_logs",
                        "compose_exec",
                        "compose_build",
                        "compose_up",
                        "compose_down",
                    ],
                    "description": "Docker command to execute",
                },
                "container": {
                    "type": "string",
                    "description": "Container name or ID (for container-specific commands)",
                },
                "image": {
                    "type": "string",
                    "description": "Image name (for build command)",
                },
                "path": {
                    "type": "string",
                    "description": "Path to Dockerfile or compose file directory",
                },
                "service": {
                    "type": "string",
                    "description": "Service name (for compose commands)",
                },
                "cmd": {
                    "type": "string",
                    "description": "Command to execute inside container (for exec)",
                },
                "tail": {
                    "type": "integer",
                    "description": "Number of lines to show from logs (default: 100)",
                    "default": 100,
                },
                "follow": {
                    "type": "boolean",
                    "description": "Follow log output (default: false)",
                    "default": False,
                },
                "all": {
                    "type": "boolean",
                    "description": "Show all containers including stopped (for ps)",
                    "default": False,
                },
            },
            "required": ["command"],
        }

    # Valid container name pattern (alphanumeric, hyphens, underscores)
    _CONTAINER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")

    def _validate_container_name(self, name: str) -> bool:
        """Validate container name against safe pattern.

        Args:
            name: Container name to validate

        Returns:
            True if valid, False otherwise
        """
        if not name or len(name) > 64:
            return False
        return bool(self._CONTAINER_NAME_PATTERN.match(name))

    def is_mutating(self, params: dict[str, Any]) -> bool:
        """Check if the Docker command mutates state."""
        command = params.get("command", "")
        mutating_commands = {
            "exec",
            "build",
            "compose_build",
            "compose_up",
            "compose_down",
        }
        return command in mutating_commands

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute Docker command."""
        params = invocation.params
        command = params.get("command")

        if not command:
            return ToolResult.error_result("No command specified")

        try:
            if command == "ps":
                return await self._container_list(params)
            elif command == "logs":
                return await self._container_logs(params)
            elif command == "exec":
                return await self._container_exec(params)
            elif command == "build":
                return await self._image_build(params)
            elif command == "images":
                return await self._image_list(params)
            elif command == "inspect":
                return await self._container_inspect(params)
            elif command == "stats":
                return await self._container_stats(params)
            elif command.startswith("compose_"):
                return await self._compose_command(command, params)
            else:
                return ToolResult.error_result(f"Unknown command: {command}")
        except Exception as e:
            logger.exception(f"Docker {command} failed")
            return ToolResult.error_result(f"Docker command failed: {e}")

    async def _container_list(self, params: dict[str, Any]) -> ToolResult:
        """List containers."""
        show_all = params.get("all", False)
        cmd_args = ["docker", "ps", "--format", "{{json .}}"]
        if show_all:
            cmd_args.insert(2, "-a")

        result = await self._run_exec(cmd_args)
        if result["success"]:
            containers = []
            for line in result["stdout"].strip().split("\n"):
                if line:
                    try:
                        containers.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return ToolResult.success_result(
                f"Found {len(containers)} containers",
                metadata={"containers": containers},
            )
        return ToolResult.error_result(result["stderr"])

    async def _container_logs(self, params: dict[str, Any]) -> ToolResult:
        """Get container logs."""
        container = params.get("container")
        if not container:
            return ToolResult.error_result("Container name or ID required")

        # Validate container name
        if not self._validate_container_name(container):
            return ToolResult.error_result(f"Invalid container name: {container}")

        tail = params.get("tail", 100)
        follow = params.get("follow", False)

        cmd_args = ["docker", "logs", "--tail", str(tail)]
        if follow:
            cmd_args.append("--follow")
        cmd_args.append(container)

        result = await self._run_exec(cmd_args, timeout=30 if not follow else 10)
        if result["success"]:
            return ToolResult.success_result(
                result["stdout"] or "No logs available",
                metadata={"container": container},
            )
        return ToolResult.error_result(result["stderr"])

    async def _container_exec(self, params: dict[str, Any]) -> ToolResult:
        """Execute command in container."""
        container = params.get("container")
        exec_cmd = params.get("cmd")

        if not container:
            return ToolResult.error_result("Container name or ID required")
        if not exec_cmd:
            return ToolResult.error_result("Command to execute required")

        # Validate container name
        if not self._validate_container_name(container):
            return ToolResult.error_result(f"Invalid container name: {container}")

        # Use exec with list of arguments for safety
        # We still use sh -c for the command inside the container,
        # but we pass it as a separate argument to docker exec
        cmd_args = ["docker", "exec", container, "sh", "-c", exec_cmd]

        result = await self._run_exec(cmd_args)
        if result["success"]:
            return ToolResult.success_result(
                result["stdout"] or "Command executed successfully",
                metadata={"container": container, "command": exec_cmd},
            )
        return ToolResult.error_result(result["stderr"])

    async def _image_build(self, params: dict[str, Any]) -> ToolResult:
        """Build Docker image."""
        path = params.get("path", ".")
        tag = params.get("image", "")

        # Basic validation for path
        if ";" in path or "|" in path or "&" in path:
            return ToolResult.error_result(f"Invalid path: {path}")

        cmd_args = ["docker", "build", path]
        if tag:
            # Validate tag
            if not self._validate_container_name(tag):
                return ToolResult.error_result(f"Invalid image tag: {tag}")
            cmd_args.extend(["-t", tag])

        result = await self._run_exec(cmd_args, timeout=300)
        if result["success"]:
            return ToolResult.success_result(
                f"Image built successfully",
                metadata={"path": path, "tag": tag},
            )
        return ToolResult.error_result(result["stderr"])

    async def _image_list(self, params: dict[str, Any]) -> ToolResult:
        """List Docker images."""
        cmd_args = ["docker", "images", "--format", "{{json .}}"]

        result = await self._run_exec(cmd_args)
        if result["success"]:
            images = []
            for line in result["stdout"].strip().split("\n"):
                if line:
                    try:
                        images.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return ToolResult.success_result(
                f"Found {len(images)} images",
                metadata={"images": images},
            )
        return ToolResult.error_result(result["stderr"])

    async def _container_inspect(self, params: dict[str, Any]) -> ToolResult:
        """Inspect container."""
        container = params.get("container")
        if not container:
            return ToolResult.error_result("Container name or ID required")

        if not self._validate_container_name(container):
            return ToolResult.error_result(f"Invalid container name: {container}")

        cmd_args = ["docker", "inspect", container]

        result = await self._run_exec(cmd_args)
        if result["success"]:
            try:
                data = json.loads(result["stdout"])
                return ToolResult.success_result(
                    f"Container details retrieved",
                    metadata={"inspect": data},
                )
            except json.JSONDecodeError:
                return ToolResult.success_result(result["stdout"])
        return ToolResult.error_result(result["stderr"])

    async def _container_stats(self, params: dict[str, Any]) -> ToolResult:
        """Get container stats."""
        container = params.get("container")

        cmd_args = ["docker", "stats", "--no-stream", "--format", "{{json .}}"]
        if container:
            if not self._validate_container_name(container):
                return ToolResult.error_result(f"Invalid container name: {container}")
            cmd_args.append(container)

        result = await self._run_exec(cmd_args)
        if result["success"]:
            stats = []
            for line in result["stdout"].strip().split("\n"):
                if line:
                    try:
                        stats.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return ToolResult.success_result(
                f"Stats retrieved for {len(stats)} containers",
                metadata={"stats": stats},
            )
        return ToolResult.error_result(result["stderr"])

    async def _compose_command(self, command: str, params: dict[str, Any]) -> ToolResult:
        """Execute docker-compose command."""
        path = params.get("path", ".")
        service = params.get("service", "")

        # Basic validation for path
        if ";" in path or "|" in path or "&" in path:
            return ToolResult.error_result(f"Invalid path: {path}")

        compose_commands = {
            "compose_ps": ["ps"],
            "compose_logs": ["logs"],
            "compose_exec": ["exec"],
            "compose_build": ["build"],
            "compose_up": ["up", "-d"],
            "compose_down": ["down"],
        }

        base_args = compose_commands.get(command)
        if not base_args:
            return ToolResult.error_result(f"Unknown compose command: {command}")

        cmd_args = ["docker-compose", "-f", f"{path}/docker-compose.yml"]
        cmd_args.extend(base_args)

        if command == "compose_logs":
            tail = params.get("tail", 100)
            cmd_args.append(f"--tail={tail}")
        elif command == "compose_exec":
            exec_cmd = params.get("cmd", "sh")
            if service:
                if not self._validate_container_name(service):
                    return ToolResult.error_result(f"Invalid service name: {service}")
                cmd_args.extend([service, exec_cmd])
            else:
                return ToolResult.error_result("Service name required for exec")
        elif command == "compose_build" and service:
            if not self._validate_container_name(service):
                return ToolResult.error_result(f"Invalid service name: {service}")
            cmd_args.append(service)
        elif command == "compose_up" and service:
            if not self._validate_container_name(service):
                return ToolResult.error_result(f"Invalid service name: {service}")
            cmd_args.append(service)
        elif command == "compose_down":
            pass  # No service needed

        timeout = 300 if command in ["compose_build", "compose_up", "compose_down"] else 30

        result = await self._run_exec(cmd_args, timeout=timeout)
        if result["success"]:
            return ToolResult.success_result(
                result["stdout"] or f"Compose {command} completed",
                metadata={"command": command, "path": path},
            )
        return ToolResult.error_result(result["stderr"])

    async def _run_exec(self, cmd_args: list[str], timeout: float = 30) -> dict[str, Any]:
        """Run command using exec (safer than shell).

        Args:
            cmd_args: Command and arguments as a list
            timeout: Timeout in seconds

        Returns:
            Dict with success, stdout, stderr, and returncode
        """
        import asyncio

        # Log command for security auditing
        logger.info(f"Executing command: {' '.join(cmd_args[:10])}...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
            }
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }

        compose_cmd = compose_commands.get(command)
        if not compose_cmd:
            return ToolResult.error_result(f"Unknown compose command: {command}")

        cmd = f"docker-compose -f {path}/docker-compose.yml {compose_cmd}"

        if command == "compose_logs":
            tail = params.get("tail", 100)
            cmd += f" --tail={tail}"
        elif command == "compose_exec":
            exec_cmd = params.get("cmd", "sh")
            if service:
                cmd += f" {service} {exec_cmd}"
            else:
                return ToolResult.error_result("Service name required for exec")
        elif command == "compose_build" and service:
            cmd += f" {service}"
        elif command == "compose_up" and service:
            cmd += f" {service}"
        elif command == "compose_down":
            pass  # No service needed

        timeout = 300 if command in ["compose_build", "compose_up", "compose_down"] else 30

        result = await self._run_shell(cmd, timeout=timeout)
        if result["success"]:
            return ToolResult.success_result(
                result["stdout"] or f"Compose {compose_cmd} completed",
                metadata={"command": command, "path": path},
            )
        return ToolResult.error_result(result["stderr"])

    async def _run_shell(self, command: str, timeout: float = 30) -> dict[str, Any]:
        """Run shell command and return result.

        WARNING: This method uses shell execution and should only be used
        with validated, non-user-controlled inputs.
        """
        import asyncio

        # Log security-relevant commands
        logger.info(f"Executing shell command: {command[:100]}...")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }

    async def _run_exec(self, cmd_args: list[str], timeout: float = 30) -> dict[str, Any]:
        """Run command using exec (safer than shell).

        Args:
            cmd_args: Command and arguments as a list
            timeout: Timeout in seconds

        Returns:
            Dict with success, stdout, stderr, and returncode
        """
        import asyncio

        # Log command for security auditing
        logger.info(f"Executing command: {' '.join(cmd_args[:5])}...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }
