import uuid
import asyncio
from friday_ai.config.config import Config
from friday_ai.tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field


class TodosParams(BaseModel):
    action: str = Field(..., description="Action: 'add', 'complete', 'list', 'clear'")
    id: str | None = Field(None, description="Todo ID (for complete)")
    content: str | None = Field(None, description="Todo content (for add)")


class TodosTool(Tool):
    name = "todos"
    description = "Manage a task list for the current session. Use this to track progress on multi-step tasks."
    kind = ToolKind.MEMORY

    @property
    def schema(self) -> type[TodosParams]:
        """Get tool schema."""
        return TodosParams

    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self._lock = asyncio.Lock()

    async def _load_todos(self) -> dict[str, str]:
        """Load todos from file (async)."""
        import aiofiles
        import orjson
        from friday_ai.config.loader import get_data_dir

        data_dir = get_data_dir()
        # Use to_thread for blocking mkdir
        await asyncio.to_thread(data_dir.mkdir, parents=True, exist_ok=True)
        path = data_dir / "todos.json"

        # Use to_thread for blocking exists()
        if not await asyncio.to_thread(path.exists):
            return {}

        try:
            async with aiofiles.open(path, mode="rb") as f:
                content = await f.read()
                return orjson.loads(content)
        except Exception:
            return {}

    async def _save_todos(self, todos: dict[str, str]) -> None:
        """Save todos to file (async)."""
        import aiofiles
        import orjson
        from friday_ai.config.loader import get_data_dir

        data_dir = get_data_dir()
        await asyncio.to_thread(data_dir.mkdir, parents=True, exist_ok=True)
        path = data_dir / "todos.json"

        async with aiofiles.open(path, mode="wb") as f:
            await f.write(orjson.dumps(todos, option=orjson.OPT_INDENT_2))

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = TodosParams(**invocation.params)

        async with self._lock:
            if params.action.lower() == "add":
                if not params.content:
                    return ToolResult.error_result("`content` required for 'add' action")

                todos = await self._load_todos()
                todo_id = str(uuid.uuid4())[:8]
                todos[todo_id] = params.content
                await self._save_todos(todos)

                return ToolResult.success_result(f"Added todo [{todo_id}]: {params.content}")
            elif params.action.lower() == "complete":
                if not params.id:
                    return ToolResult.error_result("`id` required for 'complete' action")

                todos = await self._load_todos()
                if params.id not in todos:
                    return ToolResult.error_result(f"Todo not found: {params.id}")

                content = todos.pop(params.id)
                await self._save_todos(todos)

                return ToolResult.success_result(f"Completed todo [{params.id}]: {content}")
            elif params.action == "list":
                todos = await self._load_todos()
                if not todos:
                    return ToolResult.success_result("No todos")
                lines = ["Todos:"]

                for todo_id, content in sorted(todos.items()):
                    lines.append(f"  [{todo_id}] {content}")
                return ToolResult.success_result("\n".join(lines))
            elif params.action == "clear":
                todos = await self._load_todos()
                count = len(todos)
                await self._save_todos({})
                return ToolResult.success_result(f"Cleared {count} todos")
            else:
                return ToolResult.error_result(f"Unknown action: {params.action}")
