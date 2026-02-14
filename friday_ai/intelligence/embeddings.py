"""Embedding Service - Multi-backend text embedding system.

Supports multiple backends for generating text embeddings:
- DUMMY: Hash-based fallback (always available, no dependencies)
- SENTENCE_TRANSFORMERS: Local models (requires sentence-transformers)
- OPENAI: OpenAI embeddings API (requires openai package)

All backends produce 384-dimensional embeddings (same as OpenAI).
"""

import hashlib
import logging
from enum import Enum
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Exception raised for embedding-related errors."""

    pass


class EmbeddingBackend(Enum):
    """Embedding backend types."""

    DUMMY = "dummy"  # Hash-based, always available
    SENTENCE_TRANSFORMERS = "sentence_transformers"  # Local models
    OPENAI = "openai"  # OpenAI API


class EmbeddingService:
    """Multi-backend embedding service.

    Features:
    - Automatic backend detection
    - Graceful fallback for missing dependencies
    - Result caching
    - 384-dimensional embeddings (standard)
    - Cosine similarity calculation
    """

    # Standard embedding dimension (OpenAI compatible)
    EMBEDDING_DIM = 384

    def __init__(
        self,
        backend: Optional[EmbeddingBackend] = None,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        """Initialize embedding service.

        Args:
            backend: Backend to use. If None, auto-detect.
            model_name: Model name for SENTENCE_TRANSFORMERS backend.

        Raises:
            EmbeddingError: If backend initialization fails.
        """
        self._model = None
        self._model_name = model_name

        # Auto-detect backend if not specified
        if backend is None:
            backend = self._detect_backend()

        # Initialize backend
        self.backend = self._initialize_backend(backend)
        self._cache: dict[str, list[float]] = {}

        logger.info(f"EmbeddingService initialized with {self.backend.value} backend")

    @property
    def embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self.EMBEDDING_DIM

    def _detect_backend(self) -> EmbeddingBackend:
        """Auto-detect best available backend.

        Returns:
            Detected backend.
        """
        # Try OPENAI first (requires API key)
        if self._check_openai_available():
            return EmbeddingBackend.OPENAI

        # Try SENTENCE_TRANSFORMERS (requires package)
        if self._check_sentence_transformers_available():
            return EmbeddingBackend.SENTENCE_TRANSFORMERS

        # Fall back to DUMMY (always available)
        return EmbeddingBackend.DUMMY

    def _initialize_backend(self, backend: EmbeddingBackend) -> EmbeddingBackend:
        """Initialize specified backend with fallback.

        Args:
            backend: Backend to initialize.

        Returns:
            Actual backend used (may fall back to DUMMY).
        """
        if backend == EmbeddingBackend.DUMMY:
            # DUMMY always works
            return EmbeddingBackend.DUMMY

        elif backend == EmbeddingBackend.SENTENCE_TRANSFORMERS:
            if self._check_sentence_transformers_available():
                try:
                    self._load_sentence_transformers_model()
                    return EmbeddingBackend.SENTENCE_TRANSFORMERS
                except Exception as e:
                    logger.warning(f"Failed to load sentence-transformers: {e}")
                    logger.info("Falling back to DUMMY backend")
                    return EmbeddingBackend.DUMMY
            else:
                logger.warning("sentence-transformers not available")
                logger.info("Falling back to DUMMY backend")
                return EmbeddingBackend.DUMMY

        elif backend == EmbeddingBackend.OPENAI:
            if self._check_openai_available():
                try:
                    self._load_openai_model()
                    return EmbeddingBackend.OPENAI
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI: {e}")
                    logger.info("Falling back to DUMMY backend")
                    return EmbeddingBackend.DUMMY
            else:
                logger.warning("OpenAI not available")
                logger.info("Falling back to DUMMY backend")
                return EmbeddingBackend.DUMMY

        else:
            logger.warning(f"Unknown backend: {backend}")
            return EmbeddingBackend.DUMMY

    def _check_sentence_transformers_available(self) -> bool:
        """Check if sentence-transformers is available.

        Returns:
            True if available.
        """
        try:
            import sentence_transformers  # noqa: F401

            return True
        except ImportError:
            return False

    def _check_openai_available(self) -> bool:
        """Check if OpenAI is available.

        Returns:
            True if available.
        """
        try:
            import openai  # noqa: F401

            # Check for API key
            import os

            api_key = os.environ.get("OPENAI_API_KEY")
            return api_key is not None
        except ImportError:
            return False

    def _load_sentence_transformers_model(self):
        """Load sentence-transformers model."""
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self._model_name)
        logger.info(f"Loaded sentence-transformers model: {self._model_name}")

    def _load_openai_model(self):
        """Initialize OpenAI client."""
        import openai

        self._model = openai
        logger.info("Initialized OpenAI client")

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (384 dimensions).

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        if not text:
            # Handle empty text gracefully
            return [0.0] * self.EMBEDDING_DIM

        # Check cache
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Generate embedding based on backend
        try:
            if self.backend == EmbeddingBackend.DUMMY:
                embedding = self._embed_dummy(text)
            elif self.backend == EmbeddingBackend.SENTENCE_TRANSFORMERS:
                embedding = self._embed_sentence_transformers(text)
            elif self.backend == EmbeddingBackend.OPENAI:
                embedding = self._embed_openai(text)
            else:
                raise EmbeddingError(f"Unknown backend: {self.backend}")

            # Cache result
            self._cache[cache_key] = embedding

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")

    def _embed_dummy(self, text: str) -> list[float]:
        """Generate hash-based embedding (DUMMY backend).

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (384 dimensions).
        """
        # Use SHA-256 hash for determinism
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to 384 floats
        embedding = []
        for i in range(self.EMBEDDING_DIM):
            # Use hash bytes cyclically
            byte_index = i % len(hash_bytes)
            # Normalize to [0, 1]
            value = hash_bytes[byte_index] / 255.0
            embedding.append(value)

        return embedding

    def _embed_sentence_transformers(self, text: str) -> list[float]:
        """Generate embedding using sentence-transformers.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (384 dimensions, truncated/padded if needed).
        """
        embedding = self._model.encode(text, convert_to_numpy=True)

        # Ensure 384 dimensions
        if len(embedding) > self.EMBEDDING_DIM:
            embedding = embedding[: self.EMBEDDING_DIM]
        elif len(embedding) < self.EMBEDDING_DIM:
            # Pad with zeros
            padding = [0.0] * (self.EMBEDDING_DIM - len(embedding))
            embedding = list(embedding) + padding

        return list(embedding)

    def _embed_openai(self, text: str) -> list[float]:
        """Generate embedding using OpenAI API.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (384 dimensions, truncated if needed).
        """
        import os

        # Use text-embedding-3-small (cheaper, still high quality)
        # or text-embedding-ada-002 (1536 dimensions)
        model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

        response = self._model.embeddings.create(input=text, model=model)
        embedding = response.data[0].embedding

        # Truncate to 384 dimensions if needed
        if len(embedding) > self.EMBEDDING_DIM:
            embedding = embedding[: self.EMBEDDING_DIM]

        return embedding

    def similarity(
        self, vec1: list[float], vec2: list[float]
    ) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector.
            vec2: Second vector.

        Returns:
            Similarity score in [0, 1].

        Raises:
            EmbeddingError: If vectors have different dimensions.
        """
        # Handle different dimensions
        if len(vec1) != len(vec2):
            # Pad shorter vector
            max_len = max(len(vec1), len(vec2))
            vec1 = vec1 + [0.0] * (max_len - len(vec1))
            vec2 = vec2 + [0.0] * (max_len - len(vec2))

        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Ensure in [0, 1]
        return max(0.0, min(1.0, similarity))

    def clear_cache(self):
        """Clear embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")

    def get_cache_size(self) -> int:
        """Get current cache size.

        Returns:
            Number of cached embeddings.
        """
        return len(self._cache)
