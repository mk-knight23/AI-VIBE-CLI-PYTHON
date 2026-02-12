"""RAG (Retrieval-Augmented Generation) for codebase knowledge."""

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """A chunk of a document."""

    content: str
    file_path: str
    start_line: int
    end_line: int
    chunk_id: str
    embedding: Optional[list[float]] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class QueryResult:
    """Result from a knowledge base query."""

    chunks: list[DocumentChunk]
    score: float
    source: str


class CodebaseRAG:
    """RAG system for codebase knowledge retrieval."""

    def __init__(self, index_dir: Optional[str] = None):
        """Initialize the RAG system.

        Args:
            index_dir: Directory to store the index.
        """
        self.index_dir = Path(index_dir) if index_dir else Path.cwd() / ".friday" / "rag_index"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._chunks: dict[str, DocumentChunk] = {}
        self._file_index: dict[str, list[str]] = {}  # file_path -> chunk_ids

    def index_file(
        self,
        file_path: str,
        content: str,
        language: Optional[str] = None,
    ) -> list[str]:
        """Index a file for retrieval.

        Args:
            file_path: Path to the file.
            content: Content of the file.
            language: Programming language (for metadata).

        Returns:
            List of chunk IDs created.
        """
        # Determine chunk size based on file type
        chunk_size = self._get_chunk_size(file_path)
        overlap = chunk_size // 4

        chunks = self._split_into_chunks(
            content,
            file_path,
            chunk_size,
            overlap,
        )

        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk

        # Update file index
        self._file_index[file_path] = [c.chunk_id for c in chunks]

        # Save index
        self._save_index()

        logger.info(f"Indexed {len(chunks)} chunks from {file_path}")
        return [c.chunk_id for c in chunks]

    def _get_chunk_size(self, file_path: str) -> int:
        """Determine chunk size based on file type.

        Args:
            file_path: Path to the file.

        Returns:
            Chunk size in characters.
        """
        ext = Path(file_path).suffix.lower()

        # Smaller chunks for complex files
        large_files = {".py", ".java", ".js", ".ts", ".go", ".rs"}
        medium_files = {".cpp", ".c", ".h", ".cs", ".rb"}

        if ext in large_files:
            return 2000
        elif ext in medium_files:
            return 1500
        else:
            return 3000

    def _split_into_chunks(
        self,
        content: str,
        file_path: str,
        chunk_size: int,
        overlap: int,
    ) -> list[DocumentChunk]:
        """Split content into overlapping chunks.

        Args:
            content: File content.
            file_path: Path to the file.
            chunk_size: Maximum chunk size.
            overlap: Overlap between chunks.

        Returns:
            List of document chunks.
        """
        lines = content.split("\n")
        chunks = []
        chunk_id = 0

        i = 0
        while i < len(lines):
            chunk_lines = lines[i : i + chunk_size]
            chunk_content = "\n".join(chunk_lines)

            # Generate chunk ID
            content_hash = hashlib.md5(chunk_content.encode()).hexdigest()[:8]
            cid = f"{Path(file_path).stem}_{chunk_id}_{content_hash}"

            # Determine line numbers
            start_line = i + 1
            end_line = min(i + chunk_size, len(lines))

            # Try to chunk at natural boundaries
            if i + chunk_size < len(lines):
                # Look for code structure boundaries
                last_newline = chunk_content.rfind("\n")
                if last_newline > chunk_size * 0.7:
                    # Trim to natural boundary
                    lines = lines[: i + (last_newline + 1)]
                    chunk_content = "\n".join(lines[i : i + chunk_size])
                    end_line = min(i + chunk_size, len(lines))

            chunk = DocumentChunk(
                content=chunk_content,
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                chunk_id=cid,
                metadata={
                    "file_type": Path(file_path).suffix,
                    "total_lines": len(lines),
                },
            )

            chunks.append(chunk)
            chunk_id += 1

            # Move forward with overlap
            i += chunk_size - overlap
            if i < 0:
                i = 0

        return chunks

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.
        """
        # Simple TF-IDF-like embedding for code
        # In production, use sentence-transformers or OpenAI embeddings
        words = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", text.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Create a simple embedding (in production, use actual embeddings)
        embedding = list(word_freq.values())
        return embedding[:100]  # Limit dimensions

    def search(
        self,
        query: str,
        top_k: int = 5,
        file_filter: Optional[list[str]] = None,
    ) -> list[QueryResult]:
        """Search the knowledge base.

        Args:
            query: Search query.
            top_k: Number of results to return.
            file_filter: Optional list of file paths to filter.

        Returns:
            List of query results.
        """
        query_words = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", query.lower()))

        results = []

        for chunk_id, chunk in self._chunks.items():
            # Apply file filter
            if file_filter and chunk.file_path not in file_filter:
                continue

            # Calculate simple relevance score
            chunk_words = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", chunk.content.lower()))
            overlap = len(query_words & chunk_words)

            if overlap > 0:
                # Normalize by chunk size
                score = overlap / (len(chunk_words) + 1)

                # Boost exact matches
                if query.lower() in chunk.content.lower():
                    score *= 2

                results.append(
                    QueryResult(
                        chunks=[chunk],
                        score=score,
                        source=chunk.file_path,
                    )
                )

        # Sort by score and return top k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def get_context(self, query: str, max_tokens: int = 4000) -> str:
        """Get relevant context for a query.

        Args:
            query: Search query.
            max_tokens: Maximum tokens in context.

        Returns:
            Concatenated context string.
        """
        results = self.search(query, top_k=10)

        context_parts = []
        current_length = 0

        for result in results:
            for chunk in result.chunks:
                chunk_text = f"\n--- {chunk.file_path}:{chunk.start_line}-{chunk.end_line} ---\n"
                chunk_text += chunk.content

                if current_length + len(chunk_text) > max_tokens:
                    # Truncate this chunk
                    remaining = max_tokens - current_length
                    if remaining > 100:
                        chunk_text = chunk_text[:remaining]
                        context_parts.append(chunk_text)
                    break

                context_parts.append(chunk_text)
                current_length += len(chunk_text)

        return "\n".join(context_parts)

    def remove_file(self, file_path: str) -> bool:
        """Remove a file from the index.

        Args:
            file_path: Path to the file.

        Returns:
            True if successful.
        """
        if file_path not in self._file_index:
            return False

        chunk_ids = self._file_index[file_path]
        for chunk_id in chunk_ids:
            if chunk_id in self._chunks:
                del self._chunks[chunk_id]

        del self._file_index[file_path]
        self._save_index()

        logger.info(f"Removed {file_path} from index")
        return True

    def reindex_file(self, file_path: str, content: str) -> list[str]:
        """Reindex a file.

        Args:
            file_path: Path to the file.
            content: New content.

        Returns:
            List of chunk IDs.
        """
        self.remove_file(file_path)
        return self.index_file(file_path, content)

    def _save_index(self) -> None:
        """Save the index to disk."""
        index_data = {
            "chunks": {
                cid: {
                    "content": chunk.content,
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "chunk_id": chunk.chunk_id,
                    "metadata": chunk.metadata,
                }
                for cid, chunk in self._chunks.items()
            },
            "file_index": self._file_index,
        }

        with open(self.index_dir / "index.json", "w") as f:
            json.dump(index_data, f)

    def _load_index(self) -> None:
        """Load the index from disk."""
        index_path = self.index_dir / "index.json"
        if not index_path.exists():
            return

        with open(index_path, "r") as f:
            index_data = json.load(f)

        for cid, data in index_data.get("chunks", {}).items():
            self._chunks[cid] = DocumentChunk(
                content=data["content"],
                file_path=data["file_path"],
                start_line=data["start_line"],
                end_line=data["end_line"],
                chunk_id=data["chunk_id"],
                metadata=data.get("metadata", {}),
            )

        self._file_index = index_data.get("file_index", {})

    def get_index_stats(self) -> dict:
        """Get statistics about the index.

        Returns:
            Statistics dictionary.
        """
        return {
            "total_chunks": len(self._chunks),
            "total_files": len(self._file_index),
            "index_dir": str(self.index_dir),
        }

    def clear_index(self) -> None:
        """Clear the entire index."""
        self._chunks.clear()
        self._file_index.clear()
        self._save_index()
        logger.info("Cleared RAG index")


class CodebaseQA:
    """Question-answering system for codebase."""

    def __init__(self, rag: Optional[CodebaseRAG] = None):
        """Initialize the QA system.

        Args:
            rag: RAG system to use.
        """
        self.rag = rag or CodebaseRAG()

    def answer_question(
        self,
        question: str,
        context: Optional[str] = None,
    ) -> dict:
        """Answer a question about the codebase.

        Args:
            question: The question.
            context: Additional context to include.

        Returns:
            Answer with sources.
        """
        # Get relevant context from RAG
        relevant_context = self.rag.get_context(question, max_tokens=3000)

        # Combine with any provided context
        full_context = relevant_context
        if context:
            full_context = f"{context}\n\n{relevant_context}"

        return {
            "question": question,
            "answer": "",  # Would be filled by LLM
            "context": full_context,
            "sources": [],
        }

    def find_related_code(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[dict]:
        """Find code related to a query.

        Args:
            query: Search query.
            max_results: Maximum results.

        Returns:
            List of code snippets with locations.
        """
        results = self.rag.search(query, top_k=max_results)

        return [
            {
                "file": r.source,
                "score": r.score,
                "chunks": [
                    {
                        "content": c.content,
                        "start_line": c.start_line,
                        "end_line": c.end_line,
                    }
                    for c in r.chunks
                ],
            }
            for r in results
        ]
