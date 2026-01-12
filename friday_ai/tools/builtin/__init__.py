from friday_ai.tools.builtin.edit_file import EditTool
from friday_ai.tools.builtin.glob import GlobTool
from friday_ai.tools.builtin.grep import GrepTool
from friday_ai.tools.builtin.list_dir import ListDirTool
from friday_ai.tools.builtin.memory import MemoryTool
from friday_ai.tools.builtin.read_file import ReadFileTool
from friday_ai.tools.builtin.shell import ShellTool
from friday_ai.tools.builtin.todo import TodosTool
from friday_ai.tools.builtin.web_fetch import WebFetchTool
from friday_ai.tools.builtin.web_search import WebSearchTool
from friday_ai.tools.builtin.write_file import WriteFileTool

__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditTool",
    "ShellTool",
    "ListDirTool",
    "GrepTool",
    "GlobTool",
    "WebSearchTool",
    "WebFetchTool",
    "TodosTool",
    "MemoryTool",
]


def get_all_builtin_tools() -> list[type]:
    return [
        ReadFileTool,
        WriteFileTool,
        EditTool,
        ShellTool,
        ListDirTool,
        GrepTool,
        GlobTool,
        WebSearchTool,
        WebFetchTool,
        TodosTool,
        MemoryTool,
    ]
