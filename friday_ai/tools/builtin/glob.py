import os
from pathlib import Path
import re
from typing import Optional
from friday_ai.tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from friday_ai.utils.paths import is_binary_file, resolve_path
from friday_ai.cache.cache import ttl_cache


class GlobParams(BaseModel):
    pattern: str = Field(..., description="Glob pattern to match")
    path: str = Field(
        ".", description="Directory to search in (default: current directory)"
    )


class GlobTool(Tool):
    name = "glob"
    description = (
        "Find files matching a glob pattern. Supports ** for recursive matching."
    )
    kind = ToolKind.READ
    schema = GlobParams

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache for glob results with 60 second TTL
        self._glob_cache = ttl_cache(maxsize=128, ttl=60)

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = GlobParams(**invocation.params)

        search_path = resolve_path(invocation.cwd, params.path)

        if not search_path.exists() or not search_path.is_dir():
            return ToolResult.error_result(f"Directory does not exist: {search_path}")

        try:
            matches = self._get_glob_matches(str(search_path), params.pattern)
            matches = [p for p in matches if p.is_file()]
        except Exception as e:
            return ToolResult.error_result(f"Error searching: {e}")

        output_lines = []

        for file_path in matches[:1000]:
            try:
                rel_path = file_path.relative_to(invocation.cwd)
            except Exception:
                rel_path = file_path

            output_lines.append(str(rel_path))

        if len(matches) > 1000:
            output_lines.append(f"...(limited to 1000 results)")

        return ToolResult.success_result(
            "\n".join(output_lines),
            metadata={
                "path": str(search_path),
                "matches": len(matches),
            },
        )

    def _get_glob_matches(self, search_path: str, pattern: str) -> list[Path]:
        """Get glob matches with caching.

        Args:
            search_path: Directory to search in
            pattern: Glob pattern

        Returns:
            List of matching file paths
        """
        # Check modification time for cache invalidation
        path_obj = Path(search_path)
        if not path_obj.exists():
            return []

        try:
            mtime = path_obj.stat().st_mtime
        except Exception:
            mtime = 0

        # Use cached result if directory hasn't been modified
        return self._perform_glob(search_path, pattern, mtime)

    @staticmethod
    @ttl_cache(maxsize=256, ttl=60)
    def _perform_glob(search_path: str, pattern: str, mtime: float) -> list[Path]:
        """Perform the actual glob operation (cached).

        Args:
            search_path: Directory to search in
            pattern: Glob pattern
            mtime: Modification time for cache invalidation

        Returns:
            List of matching paths
        """
        path_obj = Path(search_path)
        try:
            return list(path_obj.glob(pattern))
        except Exception:
            return []

    def _find_files(self, search_path: Path) -> list[Path]:
        files = []

        for root, dirs, filenames in os.walk(search_path):
            dirs[:] = [
                d
                for d in dirs
                if d not in {"node_modules", "__pycache__", ".git", ".venv", "venv"}
            ]

            for filename in filenames:
                if filename.startswith("."):
                    continue

                file_path = Path(root) / filename
                if not is_binary_file(file_path):
                    files.append(file_path)
                    if len(files) >= 500:
                        return files

        return files
