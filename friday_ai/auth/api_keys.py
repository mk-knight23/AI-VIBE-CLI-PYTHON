"""API key management.

Simple API key authentication for Phase 1.
In production, this should be backed by a database with proper hashing.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from friday_ai.database.redis_backend import RedisSessionBackend


class APIKeyManager:
    """Manage API key validation and metadata."""

    def __init__(self, redis_backend: RedisSessionBackend):
        self.redis = redis_backend
        self._cache: Dict[str, dict] = {}

    def generate_key(self, user_id: str, tier: str = "free") -> str:
        """Generate a new API key.

        Args:
            user_id: Associated user ID
            tier: API tier (free, pro, enterprise)

        Returns:
            New API key (store this securely!)
        """
        # Generate random key
        key = "friday_" + secrets.token_urlsafe(32)

        # Hash for storage
        key_hash = hashlib.sha256(key.encode()).hexdigest()

        # Store metadata
        metadata = {
            "key_hash": key_hash,
            "user_id": user_id,
            "tier": tier,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_used": None,
            "is_active": True,
        }

        # Store in Redis (in production, use a proper DB)
        # For now, just cache locally
        self._cache[key_hash] = metadata

        return key

    async def validate_key(self, api_key: str) -> Optional[dict]:
        """Validate an API key.

        Args:
            api_key: API key to validate

        Returns:
            Key metadata if valid, None otherwise
        """
        if not api_key:
            return None

        # Hash the key for lookup
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Check cache first
        if key_hash in self._cache:
            metadata = self._cache[key_hash]
            if metadata.get("is_active"):
                metadata["last_used"] = datetime.now(timezone.utc).isoformat()
                return metadata
            return None

        # FIX-012: Removed hardcoded test key - use environment variable instead
        # For testing, set FRIDAY_TEST_API_KEY environment variable
        test_key = os.getenv("FRIDAY_TEST_API_KEY")
        if test_key and api_key == test_key:
            return {
                "user_id": "test_user",
                "tier": "pro",
                "is_active": True,
            }

        return None

    async def revoke_key(self, key_hash: str) -> bool:
        """Revoke an API key.

        Args:
            key_hash: Hash of the key to revoke

        Returns:
            True if revoked, False if not found
        """
        if key_hash in self._cache:
            self._cache[key_hash]["is_active"] = False
            return True
        return False
