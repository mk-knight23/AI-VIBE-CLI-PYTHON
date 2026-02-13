from pathlib import Path
from friday_ai.tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from friday_ai.utils.paths import resolve_path
from friday_ai.cache.cache import ttl_cache


class ListDirParams(BaseModel):
    path: str = Field(
        ".", description="Directory path to list (default: current directory)"
    )
    include_hidden: bool = Field(
        False,
        description="Whether to include hidden files and directories (default: false",
    )


class ListDirTool(Tool):
    name = "list_dir"
    description = "List contents of a directory"
    kind = ToolKind.READ
    schema = ListDirParams

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache for directory listings with 30 second TTL
        self._list_cache = ttl_cache(maxsize=256, ttl=30)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ListDirParams(**invocation.params)

        dir_path = resolve_path(invocation.cwd, params.path)

        if not dir_path.exists() or not dir_path.is_dir():
            return ToolResult.error_result(f"Directory does not exist: {dir_path}")

        try:
            items = self._get_directory_items(
                str(dir_path),
                params.include_hidden
            )
        except Exception as e:
            return ToolResult.error_result(f"Error listing directory: {e}")

        if not params.include_hidden:
            items = [item for item in items if not item.name.startswith(".")]

        if not items:
            return ToolResult.success_result(
                "Directory is empty", metadata={"path": str(dir_path), "entries": 0}
            )

        lines = []

        for item in items:
            if item.is_dir():
                lines.append(f"{item.name}/")
            else:
                lines.append(item.name)

        return ToolResult.success_result(
            "\n".join(lines),
            metadata={
                "path": str(dir_path),
                "entries": len(items),
            },
        )

    def _get_directory_items(
        self,
        dir_path: str,
        include_hidden: bool
    ) -> list[Path]:
        """Get directory items with caching.

        Args:
            dir_path: Directory path
            include_hidden: Whether to include hidden files

        Returns:
            Sorted list of directory items
        """
        # Check modification time for cache invalidation
        path_obj = Path(dir_path)
        if not path_obj.exists():
            return []

        try:
            mtime = path_obj.stat().st_mtime
        except Exception:
            mtime = 0

        # Use cached result if directory hasn't been modified
        return self._perform_list_dir(dir_path, include_hidden, mtime)

    @staticmethod
    @ttl_cache(maxsize=512, ttl=30)
    def _perform_list_dir(
        dir_path: str,
        include_hidden: bool,
        mtime: float
    ) -> list[Path]:
        """Perform the actual directory listing (cached).

        Args:
            dir_path: Directory path to list
            include_hidden: Whether to include hidden files
            mtime: Modification time for cache invalidation

        Returns:
            Sorted list of directory items
        """
        path_obj = Path(dir_path)
        try:
            return sorted(
                path_obj.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except Exception:
            return []
