from friday_ai.tools.builtin.database import DatabaseTool
from friday_ai.tools.builtin.docker import DockerTool
from friday_ai.tools.builtin.edit_file import EditTool
from friday_ai.tools.builtin.git import GitTool
from friday_ai.tools.builtin.glob import GlobTool
from friday_ai.tools.builtin.grep import GrepTool
from friday_ai.tools.builtin.http_client import HttpClient, get_http_client, shutdown_http_client
from friday_ai.tools.builtin.http_request import HttpDownloadTool, HttpTool
from friday_ai.tools.builtin.list_dir import ListDirTool
from friday_ai.tools.builtin.memory import MemoryTool
from friday_ai.tools.builtin.rag_index import RagIndexTool
from friday_ai.tools.builtin.read_file import ReadFileTool
from friday_ai.tools.builtin.shell import ShellTool
from friday_ai.tools.builtin.security_audit import SecurityAuditLogTool
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
    "GitTool",
    "HttpRequestTool",
    "HttpDownloadTool",
    "DockerTool",
    "DatabaseTool",
    "SecurityAuditLogTool",
    "RagIndexTool",
    "HttpClient",
    "get_http_client",
    "shutdown_http_client",
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
        GitTool,
        HttpTool,
        HttpDownloadTool,
        DockerTool,
        DatabaseTool,
        RagIndexTool,
    ]
