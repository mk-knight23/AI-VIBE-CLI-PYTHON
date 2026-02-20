"""RAG Index Tool - Index codebase for semantic search."""

import json
import os
from pathlib import Path
from typing import Optional

from friday_ai.tools.base import Tool, ToolInvocation, ToolKind, ToolResult
from friday_ai.utils.paths import is_binary_file, resolve_path
from friday_ai.cache.cache import ttl_cache


class RagIndexParams:
    """Parameters for RAG index tool."""

    def __init__(self, path: str = "."):
        self.path = path


class RagIndexTool(Tool):
    """Tool for indexing codebase with semantic embeddings."""

    name = "rag_index"
    description = (
        "Index a directory for semantic code search. "
        "Creates embeddings for all files and saves to .friday_rag_index.json"
    )
    kind = ToolKind.READ
    schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory to index"}
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache for glob results with 60 second TTL
        self._glob_cache = ttl_cache(maxsize=128, ttl=60)
        self._embedding_service = None

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        """Execute RAG indexing.

        Args:
            invocation: Tool invocation with parameters

        Returns:
            Tool result with indexing statistics
        """
        params = RagIndexParams(**invocation.params)
        index_path = resolve_path(invocation.cwd, params.path)

        if not index_path.exists() or not index_path.is_dir():
            return ToolResult.error_result(f"Directory does not exist: {index_path}")

        try:
            # Initialize embedding service
            if self._embedding_service is None:
                from friday_ai.intelligence.embeddings import EmbeddingService

                self._embedding_service = EmbeddingService()

            # Collect all files to index
            files = self._collect_files(index_path)

            if not files:
                return ToolResult.success_result("No files found to index")

            # Index files
            stats = await self._index_files(files, invocation.cwd)

            # Save index
            index_file = invocation.cwd / ".friday_rag_index.json"
            self._save_index(stats, index_file)

            output_lines = [
                f"Indexed {stats['total_files']} files",
                f"  Total chunks: {stats['total_chunks']}",
                f"  Total tokens: {stats['total_tokens']}",
                f"  Index saved to: {index_file}",
            ]

            return ToolResult.success_result(
                "\n".join(output_lines),
                metadata=stats,
            )

        except Exception as e:
            return ToolResult.error_result(f"Error indexing: {e}")

    def _collect_files(self, index_path: Path) -> list[Path]:
        """Collect all files to index.

        Args:
            index_path: Directory to index

        Returns:
            List of file paths
        """
        files = []
        ignored_dirs = {
            "node_modules",
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            ".friday",
            "dist",
            "build",
            ".pytest_cache",
        }

        for root, dirs, filenames in os.walk(index_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignored_dirs]

            for filename in filenames:
                if filename.startswith("."):
                    continue

                file_path = Path(root) / filename

                # Skip binary files
                if is_binary_file(file_path):
                    continue

                # Only index source files
                if file_path.suffix not in {
                    ".py",
                    ".js",
                    ".ts",
                    ".tsx",
                    ".jsx",
                    ".go",
                    ".rs",
                    ".java",
                    ".cpp",
                    ".c",
                    ".h",
                    ".cs",
                    ".rb",
                    ".php",
                    ".swift",
                    ".kt",
                    ".scala",
                    ".md",
                    ".txt",
                    ".yaml",
                    ".yml",
                    ".json",
                    ".toml",
                }:
                    continue

                files.append(file_path)

                # Limit to 1000 files
                if len(files) >= 1000:
                    return files

        return files

    async def _index_files(
        self, files: list[Path], cwd: Path
    ) -> dict:
        """Index files with embeddings.

        Args:
            files: List of files to index
            cwd: Current working directory

        Returns:
            Indexing statistics
        """
        stats = {
            "total_files": len(files),
            "total_chunks": 0,
            "total_tokens": 0,
            "files": [],
        }

        for file_path in files:
            try:
                # Read file
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Estimate tokens (roughly 4 chars per token)
                tokens = len(content) // 4
                stats["total_tokens"] += tokens

                # Split into chunks
                chunks = self._split_into_chunks(content, file_path)
                stats["total_chunks"] += len(chunks)

                # Generate embeddings for chunks
                chunk_embeddings = []
                for chunk in chunks:
                    embedding = self._embedding_service.embed(chunk)
                    chunk_embeddings.append(embedding)

                # Get relative path
                try:
                    rel_path = file_path.relative_to(cwd)
                except ValueError:
                    rel_path = file_path

                # Store file info
                stats["files"].append(
                    {
                        "path": str(rel_path),
                        "chunks": len(chunks),
                        "tokens": tokens,
                        "embeddings": chunk_embeddings,
                    }
                )

            except Exception as e:
                # Log error but continue
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to index {file_path}: {e}")

        return stats

    def _split_into_chunks(self, content: str, file_path: Path) -> list[str]:
        """Split file content into chunks.

        Args:
            content: File content
            file_path: Path to file

        Returns:
            List of content chunks
        """
        # Determine chunk size based on file type
        ext = file_path.suffix.lower()

        large_files = {".py", ".js", ".ts", ".java", ".go", ".rs"}
        medium_files = {".cpp", ".c", ".h", ".cs", ".rb"}

        if ext in large_files:
            chunk_size = 2000
        elif ext in medium_files:
            chunk_size = 1500
        else:
            chunk_size = 3000

        # Split by lines
        lines = content.split("\n")
        chunks = []
        overlap = chunk_size // 4

        i = 0
        while i < len(lines):
            chunk_lines = lines[i : i + chunk_size]
            chunk_content = "\n".join(chunk_lines)
            chunks.append(chunk_content)

            # Move forward with overlap
            i += chunk_size - overlap

        return chunks

    def _save_index(self, stats: dict, index_file: Path):
        """Save index to file.

        Args:
            stats: Index statistics
            index_file: Path to save index
        """
        # Don't save embeddings (too large), just metadata
        save_stats = {
            "total_files": stats["total_files"],
            "total_chunks": stats["total_chunks"],
            "total_tokens": stats["total_tokens"],
            "files": [
                {
                    "path": f["path"],
                    "chunks": f["chunks"],
                    "tokens": f["tokens"],
                }
                for f in stats["files"]
            ],
        }

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(save_stats, f, indent=2)
