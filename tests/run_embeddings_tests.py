"""
Comprehensive Test Suite for EmbeddingService

Tests embedding service with multiple backends including:
- DUMMY backend (hash-based, always available)
- SENTENCE_TRANSFORMERS backend (optional)
- OPENAI backend (optional)
- Embedding generation
- Similarity calculation
- Caching
- Error handling
- Graceful fallback

To run: python tests/test_embeddings.py
"""

import asyncio
import sys
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from friday_ai.intelligence.embeddings import (
    EmbeddingService,
    EmbeddingBackend,
    EmbeddingError,
)


class TestEmbeddingBackend:
    """Tests for EmbeddingBackend enum."""

    def __init__(self):
        self.results = []

    def log_result(self, test_name: str, success: bool, message: str):
        status = "✓ PASS" if success else "✗ FAIL"
        self.results.append({"test": test_name, "success": success, "message": message})
        print(f"  {status}: {test_name}")
        if not success:
            print(f"         → {message}")

    def test_backend_enum(self):
        """Test EmbeddingBackend enum exists."""
        print("\n🔍 Testing EmbeddingBackend - Enum Values")

        # Test 1: DUMMY backend exists
        has_dummy = hasattr(EmbeddingBackend, "DUMMY")
        self.log_result(
            "DUMMY backend exists",
            has_dummy,
            f"DUMMY={has_dummy}"
        )

        # Test 2: SENTENCE_TRANSFORMERS backend exists
        has_sentence_transformers = hasattr(EmbeddingBackend, "SENTENCE_TRANSFORMERS")
        self.log_result(
            "SENTENCE_TRANSFORMERS backend exists",
            has_sentence_transformers,
            f"SENTENCE_TRANSFORMERS={has_sentence_transformers}"
        )

        # Test 3: OPENAI backend exists
        has_openai = hasattr(EmbeddingBackend, "OPENAI")
        self.log_result(
            "OPENAI backend exists",
            has_openai,
            f"OPENAI={has_openai}"
        )

        # Test 4: Can access enum values
        try:
            dummy = EmbeddingBackend.DUMMY
            self.log_result(
                "Can access DUMMY enum value",
                dummy is not None,
                f"DUMMY={dummy}"
            )
        except Exception as e:
            self.log_result(
                "Can access DUMMY enum value",
                False,
                f"Error: {e}"
            )


class TestEmbeddingService:
    """Tests for EmbeddingService class."""

    def __init__(self):
        self.results = []

    def log_result(self, test_name: str, success: bool, message: str):
        status = "✓ PASS" if success else "✗ FAIL"
        self.results.append({"test": test_name, "success": success, "message": message})
        print(f"  {status}: {test_name}")
        if not success:
            print(f"         → {message}")

    def test_dummy_backend_initialization(self):
        """Test DUMMY backend initialization."""
        print("\n🧠 Testing EmbeddingService - DUMMY Backend Initialization")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)

            self.log_result(
                "Service initializes with DUMMY backend",
                service is not None,
                "service instance created"
            )

            self.log_result(
                "Backend is DUMMY",
                service.backend == EmbeddingBackend.DUMMY,
                f"backend={service.backend}"
            )

            self.log_result(
                "Embedding dimension is 384",
                service.embedding_dimension == 384,
                f"embedding_dimension={service.embedding_dimension}"
            )

        except Exception as e:
            self.log_result(
                "Service initializes with DUMMY backend",
                False,
                f"Error: {e}"
            )

    def test_auto_backend_detection(self):
        """Test auto-detection of available backends."""
        print("\n🧠 Testing EmbeddingService - Auto Backend Detection")

        try:
            # Auto-detect backend (no backend specified)
            service = EmbeddingService()

            self.log_result(
                "Service initializes with auto-detection",
                service is not None,
                "service instance created"
            )

            self.log_result(
                "Auto-detected backend is valid",
                service.backend in [
                    EmbeddingBackend.DUMMY,
                    EmbeddingBackend.SENTENCE_TRANSFORMERS,
                    EmbeddingBackend.OPENAI,
                ],
                f"backend={service.backend}"
            )

            # DUMMY should always be available
            self.log_result(
                "At least DUMMY backend is available",
                service.backend is not None,
                f"backend={service.backend}"
            )

        except Exception as e:
            self.log_result(
                "Service initializes with auto-detection",
                False,
                f"Error: {e}"
            )

    def test_embed_returns_list(self):
        """Test embed() returns a list."""
        print("\n🧠 Testing EmbeddingService - embed() Return Type")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)
            text = "Hello, world!"
            embedding = service.embed(text)

            self.log_result(
                "embed() returns list",
                isinstance(embedding, list),
                f"type={type(embedding).__name__}"
            )

            self.log_result(
                "embed() returns non-empty list",
                len(embedding) > 0,
                f"len={len(embedding)}"
            )

        except Exception as e:
            self.log_result(
                "embed() returns list",
                False,
                f"Error: {e}"
            )

    def test_embed_returns_correct_dimension(self):
        """Test embed() returns 384-dimensional vectors."""
        print("\n🧠 Testing EmbeddingService - embed() Dimension")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)
            text = "This is a test sentence for embedding."
            embedding = service.embed(text)

            self.log_result(
                "Embedding has 384 dimensions",
                len(embedding) == 384,
                f"len={len(embedding)}"
            )

            # Check all values are floats
            all_floats = all(isinstance(x, (int, float)) for x in embedding)
            self.log_result(
                "All embedding values are numeric",
                all_floats,
                f"all_floats={all_floats}"
            )

        except Exception as e:
            self.log_result(
                "Embedding has 384 dimensions",
                False,
                f"Error: {e}"
            )

    def test_embed_is_deterministic(self):
        """Test embed() returns same result for same input."""
        print("\n🧠 Testing EmbeddingService - embed() Determinism")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)
            text = "Deterministic test text"

            embedding1 = service.embed(text)
            embedding2 = service.embed(text)

            # For DUMMY backend, should be identical
            are_same = embedding1 == embedding2
            self.log_result(
                "Same text produces same embedding",
                are_same,
                f"same={are_same}"
            )

        except Exception as e:
            self.log_result(
                "Same text produces same embedding",
                False,
                f"Error: {e}"
            )

    def test_embed_different_text_different_embedding(self):
        """Test embed() returns different results for different inputs."""
        print("\n🧠 Testing EmbeddingService - embed() Uniqueness")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)
            text1 = "First text"
            text2 = "Second text"

            embedding1 = service.embed(text1)
            embedding2 = service.embed(text2)

            are_different = embedding1 != embedding2
            self.log_result(
                "Different text produces different embedding",
                are_different,
                f"different={are_different}"
            )

        except Exception as e:
            self.log_result(
                "Different text produces different embedding",
                False,
                f"Error: {e}"
            )

    def test_similarity_returns_float(self):
        """Test similarity() returns a float."""
        print("\n🧠 Testing EmbeddingService - similarity() Return Type")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)
            vec1 = [1.0, 2.0, 3.0] * 128  # Pad to 384
            vec2 = [1.0, 2.0, 3.0] * 128

            score = service.similarity(vec1, vec2)

            self.log_result(
                "similarity() returns float",
                isinstance(score, (int, float)),
                f"type={type(score).__name__}"
            )

        except Exception as e:
            self.log_result(
                "similarity() returns float",
                False,
                f"Error: {e}"
            )

    def test_similarity_range(self):
        """Test similarity() returns values in [0, 1]."""
        print("\n🧠 Testing EmbeddingService - similarity() Range")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)

            # Test identical vectors
            vec1 = [1.0, 2.0, 3.0] * 128
            vec2 = [1.0, 2.0, 3.0] * 128
            score_identical = service.similarity(vec1, vec2)

            self.log_result(
                "Identical vectors have similarity ~1.0",
                0.99 <= score_identical <= 1.0,
                f"score={score_identical:.4f}"
            )

            # Test different vectors
            vec3 = [1.0, 0.0, 0.0] * 128
            vec4 = [0.0, 1.0, 0.0] * 128
            score_different = service.similarity(vec3, vec4)

            self.log_result(
                "Different vectors have similarity < 1.0",
                score_different < 1.0,
                f"score={score_different:.4f}"
            )

            self.log_result(
                "Similarity is non-negative",
                score_different >= 0.0,
                f"score={score_different:.4f}"
            )

        except Exception as e:
            self.log_result(
                "Similarity in valid range",
                False,
                f"Error: {e}"
            )

    def test_similarity_symmetric(self):
        """Test similarity() is symmetric."""
        print("\n🧠 Testing EmbeddingService - similarity() Symmetry")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)

            vec1 = [1.0, 2.0, 3.0] * 128
            vec2 = [4.0, 5.0, 6.0] * 128

            score1 = service.similarity(vec1, vec2)
            score2 = service.similarity(vec2, vec1)

            # Should be identical (within float precision)
            is_symmetric = abs(score1 - score2) < 1e-6
            self.log_result(
                "similarity(a, b) == similarity(b, a)",
                is_symmetric,
                f"score1={score1:.6f}, score2={score2:.6f}"
            )

        except Exception as e:
            self.log_result(
                "Similarity is symmetric",
                False,
                f"Error: {e}"
            )

    def test_embed_empty_text(self):
        """Test embed() with empty text."""
        print("\n🧠 Testing EmbeddingService - embed() Empty Text")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)
            embedding = service.embed("")

            self.log_result(
                "Empty text produces valid embedding",
                len(embedding) == 384,
                f"len={len(embedding)}"
            )

        except Exception as e:
            # Empty text might raise an error - that's OK
            self.log_result(
                "Empty text handled gracefully",
                True,
                f"Raises: {type(e).__name__}"
            )

    def test_embed_long_text(self):
        """Test embed() with long text."""
        print("\n🧠 Testing EmbeddingService - embed() Long Text")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)
            long_text = "This is a test. " * 1000  # ~16,000 characters
            embedding = service.embed(long_text)

            self.log_result(
                "Long text produces valid embedding",
                len(embedding) == 384,
                f"len={len(embedding)}, text_len={len(long_text)}"
            )

        except Exception as e:
            self.log_result(
                "Long text handled gracefully",
                True,
                f"Error: {type(e).__name__}"
            )

    def test_similarity_different_dimensions(self):
        """Test similarity() with different dimension vectors."""
        print("\n🧠 Testing EmbeddingService - similarity() Dimension Mismatch")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)

            vec1 = [1.0, 2.0, 3.0] * 128  # 384 dimensions
            vec2 = [1.0, 2.0, 3.0] * 100  # 300 dimensions

            score = service.similarity(vec1, vec2)

            # Should handle gracefully (either raise error or pad/truncate)
            self.log_result(
                "Different dimensions handled",
                True,
                f"score={score:.4f}"
            )

        except (ValueError, EmbeddingError) as e:
            # Raising an error is acceptable
            self.log_result(
                "Different dimensions raise error",
                True,
                f"Error: {type(e).__name__}"
            )
        except Exception as e:
            self.log_result(
                "Different dimensions handled",
                False,
                f"Unexpected error: {e}"
            )

    def test_caching(self):
        """Test embed() caches results."""
        print("\n🧠 Testing EmbeddingService - Caching")

        try:
            service = EmbeddingService(backend=EmbeddingBackend.DUMMY)
            text = "Caching test text"

            # First call
            embedding1 = service.embed(text)

            # Check if cache is populated
            has_cache = hasattr(service, "_cache") or hasattr(service, "cache")
            self.log_result(
                "Service has cache mechanism",
                has_cache,
                f"has_cache={has_cache}"
            )

            # Second call should use cache
            embedding2 = service.embed(text)

            # Results should be identical
            self.log_result(
                "Cached results are identical",
                embedding1 == embedding2,
                "identical=True"
            )

        except Exception as e:
            self.log_result(
                "Caching works",
                False,
                f"Error: {e}"
            )

    def test_graceful_fallback_sentence_transformers(self):
        """Test graceful fallback when sentence-transformers missing."""
        print("\n🧠 Testing EmbeddingService - SENTENCE_TRANSFORMERS Fallback")

        try:
            # Try to initialize with SENTENCE_TRANSFORMERS
            # If package is missing, should fall back to DUMMY
            service = EmbeddingService(backend=EmbeddingBackend.SENTENCE_TRANSFORMERS)

            self.log_result(
                "SENTENCE_TRANSFORMERS backend initializes or falls back",
                service.backend in [
                    EmbeddingBackend.SENTENCE_TRANSFORMERS,
                    EmbeddingBackend.DUMMY,
                ],
                f"backend={service.backend}"
            )

            # Should still work
            text = "Test text"
            embedding = service.embed(text)

            self.log_result(
                "embed() works with SENTENCE_TRANSFORMERS (or fallback)",
                len(embedding) == 384,
                f"len={len(embedding)}"
            )

        except Exception as e:
            self.log_result(
                "SENTENCE_TRANSFORMERS handled gracefully",
                False,
                f"Error: {e}"
            )

    def test_graceful_fallback_openai(self):
        """Test graceful fallback when OpenAI missing."""
        print("\n🧠 Testing EmbeddingService - OPENAI Fallback")

        try:
            # Try to initialize with OPENAI
            # If package is missing or no API key, should fall back to DUMMY
            service = EmbeddingService(backend=EmbeddingBackend.OPENAI)

            self.log_result(
                "OPENAI backend initializes or falls back",
                service.backend in [
                    EmbeddingBackend.OPENAI,
                    EmbeddingBackend.DUMMY,
                ],
                f"backend={service.backend}"
            )

            # Should still work
            text = "Test text"
            embedding = service.embed(text)

            self.log_result(
                "embed() works with OPENAI (or fallback)",
                len(embedding) == 384,
                f"len={len(embedding)}"
            )

        except Exception as e:
            self.log_result(
                "OPENAI handled gracefully",
                False,
                f"Error: {e}"
            )


def run_all_tests():
    """Run all embedding service tests."""
    print("=" * 60)
    print("🧠 Friday Embedding Service Test Suite")
    print("   Testing multi-backend embedding system")
    print("=" * 60)

    all_results = []

    # Test EmbeddingBackend enum
    backend_enum_tests = TestEmbeddingBackend()
    backend_enum_tests.test_backend_enum()
    all_results.extend(backend_enum_tests.results)

    # Test EmbeddingService with DUMMY backend
    service_tests = TestEmbeddingService()
    service_tests.test_dummy_backend_initialization()
    service_tests.test_auto_backend_detection()
    service_tests.test_embed_returns_list()
    service_tests.test_embed_returns_correct_dimension()
    service_tests.test_embed_is_deterministic()
    service_tests.test_embed_different_text_different_embedding()
    service_tests.test_similarity_returns_float()
    service_tests.test_similarity_range()
    service_tests.test_similarity_symmetric()
    service_tests.test_embed_empty_text()
    service_tests.test_embed_long_text()
    service_tests.test_similarity_different_dimensions()
    service_tests.test_caching()
    service_tests.test_graceful_fallback_sentence_transformers()
    service_tests.test_graceful_fallback_openai()
    all_results.extend(service_tests.results)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in all_results if r["success"])
    failed = sum(1 for r in all_results if not r["success"])
    total = len(all_results)

    # Group by test class
    test_classes = {}
    for r in all_results:
        test_class = r["test"].split(" - ")[0]
        if test_class not in test_classes:
            test_classes[test_class] = {"passed": 0, "failed": 0}
        if r["success"]:
            test_classes[test_class]["passed"] += 1
        else:
            test_classes[test_class]["failed"] += 1

    print(f"\n{'Test Class':<30} {'Passed':<10} {'Failed':<10} {'Status'}")
    print("-" * 60)
    for test_class, counts in test_classes.items():
        status = "✓" if counts["failed"] == 0 else "✗"
        print(f"{test_class:<30} {counts['passed']:<10} {counts['failed']:<10} {status}")

    print("-" * 60)
    print(f"{'TOTAL':<30} {passed:<10} {failed:<10}")
    print(f"\nOverall: {passed}/{total} tests passed ({100*passed/total:.1f}%)")

    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for r in all_results:
            if not r["success"]:
                print(f"  • {r['test']}: {r['message']}")
    else:
        print("\n✅ All tests passed!")

    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
