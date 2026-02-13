import asyncio
import json
import uuid
from friday_ai.config.config import Config
from friday_ai.config.loader import get_data_dir
from friday_ai.tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class MemoryParams(BaseModel):
    action: str = Field(..., description="Action: 'set', 'get', 'delete', 'list', 'clear'")
    key: str | None = Field(None, description="Memory key (required for `set`, `get`, `delete`)")
    value: str | None = Field(None, description="Value to store (required for `set`)")


class MemoryTool(Tool):
    name = "memory"
    description = "Store and retrieve persistent memory. Use this to remember user preferences, important context or notes."
    kind = ToolKind.MEMORY

    @property
    def schema(self) -> type[MemoryParams]:
        """Get tool schema."""
        return MemoryParams

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._lock = asyncio.Lock()

    async def _load_memory(self) -> dict:
        """Load memory from file (async)."""
        import aiofiles
        import orjson
        from friday_ai.config.loader import get_data_dir

        data_dir = get_data_dir()
        # Use to_thread for blocking mkdir
        await asyncio.to_thread(data_dir.mkdir, parents=True, exist_ok=True)
        path = data_dir / "user_memory.json"

        # Use to_thread for blocking exists()
        if not await asyncio.to_thread(path.exists):
            return {"entries": {}}

        try:
            async with aiofiles.open(path, mode="rb") as f:
                content = await f.read()
                return orjson.loads(content)
        except Exception:
            return {"entries": {}}

    async def _save_memory(self, memory: dict) -> None:
        """Save memory to file (async)."""
        import aiofiles
        import orjson
        from friday_ai.config.loader import get_data_dir

        data_dir = get_data_dir()
        await asyncio.to_thread(data_dir.mkdir, parents=True, exist_ok=True)
        path = data_dir / "user_memory.json"

        async with aiofiles.open(path, mode="wb") as f:
            await f.write(orjson.dumps(memory, option=orjson.OPT_INDENT_2))

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = MemoryParams(**invocation.params)

        async with self._lock:
            if params.action.lower() == "set":
                if not params.key or not params.value:
                    return ToolResult.error_result(
                        "`key` and `value` are required for 'set' action"
                    )
                memory = await self._load_memory()
                memory["entries"][params.key] = params.value
                await self._save_memory(memory)

                return ToolResult.success_result(f"Set memory: {params.key}")
            elif params.action.lower() == "get":
                if not params.key:
                    return ToolResult.error_result("`key` required for 'get' action")

                memory = await self._load_memory()
                if params.key not in memory.get("entries", {}):
                    return ToolResult.success_result(
                        f"Memory not found: {params.key}",
                        metadata={
                            "found": False,
                        },
                    )
                return ToolResult.success_result(
                    f"Memory found: {params.key}: {memory['entries'][params.key]}",
                    metadata={
                        "found": True,
                    },
                )
            elif params.action == "delete":
                if not params.key:
                    return ToolResult.error_result("`key` required for 'get' action")
                memory = await self._load_memory()
                if params.key not in memory.get("entries", {}):
                    return ToolResult.success_result(f"Memory not found: {params.key}")

                del memory["entries"][params.key]
                await self._save_memory(memory)

                return ToolResult.success_result(f"Deleted memory: {params.key}")
            elif params.action == "list":
                memory = await self._load_memory()
                entries = memory.get("entries", {})
                if not entries:
                    return ToolResult.success_result(
                        f"No memories stored",
                        metadata={
                            "found": False,
                        },
                    )
                lines = [f"Stored memories:"]
                for key, value in sorted(entries.items()):
                    lines.append(f"  {key}: {value}")

                return ToolResult.success_result(
                    "\n".join(lines),
                    metadata={
                        "found": True,
                    },
                )
            elif params.action == "clear":
                memory = await self._load_memory()
                count = len(memory.get("entries", {}))
                memory["entries"] = {}
                await self._save_memory(memory)
                return ToolResult.success_result(f"Cleared {count} memory entries")
            else:
                return ToolResult.error_result(f"Unknown action: {params.action}")
