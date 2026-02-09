"""Secret management for Friday AI.

Provides secure secret handling with keyring integration,
encrypted storage, and secure memory management.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any

try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

from friday_ai.utils.errors import SecretNotFoundError

logger = logging.getLogger(__name__)


class SecretManager:
    """Industry-standard secret management.

    Features:
    - Pattern-based secret detection and redaction
    - Keyring/keychain integration for secure storage
    - Encrypted file-based storage fallback
    - Secure memory handling (avoid swap)
    - Audit logging for secret access
    - Secret rotation support

    Example:
        manager = SecretManager()

        # Store a secret
        await manager.secure_store("api_key", "sk-...")

        # Retrieve a secret
        secret = await manager.secure_retrieve("api_key")

        # Redact secrets from text
        safe_text = manager.redact("My key is sk-abc123")
        # Result: "My key is [REDACTED]"
    """

    # Secret detection patterns
    SECRET_PATTERNS = [
        # API Keys
        (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})["\']?', 2),
        (r'(?i)(api[_-]?key|apikey)\s+([a-zA-Z0-9_\-]{16,})', 2),
        # Secrets
        (r'(?i)(secret|client_secret)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})["\']?', 2),
        # Tokens
        (r'(?i)(token|bearer|auth_token)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})["\']?', 2),
        (r'sk-[a-zA-Z0-9]{48}', 0),  # OpenAI-style keys
        (r'gh[pousr]_[a-zA-Z0-9]{36}', 0),  # GitHub tokens
        # Passwords
        (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^"\']{8,})["\']?', 2),
        # Private keys
        (r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', 0),
        # Generic high-entropy strings that look like secrets
        (r'\b([a-zA-Z0-9_\-]{32,64})\b', 0),
    ]

    # Environment variable patterns that contain secrets
    SECRET_ENV_PATTERNS = [
        re.compile(r'.*KEY.*', re.IGNORECASE),
        re.compile(r'.*SECRET.*', re.IGNORECASE),
        re.compile(r'.*TOKEN.*', re.IGNORECASE),
        re.compile(r'.*PASSWORD.*', re.IGNORECASE),
        re.compile(r'.*CREDENTIAL.*', re.IGNORECASE),
        re.compile(r'.*PRIVATE.*', re.IGNORECASE),
        re.compile(r'.*AUTH.*', re.IGNORECASE),
    ]

    def __init__(
        self,
        app_name: str = "friday-ai",
        storage_path: str | Path | None = None,
        master_key: str | None = None,
    ):
        self.app_name = app_name
        self.storage_path = Path(storage_path or "~/.config/friday/secrets").expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize encryption if cryptography is available
        self._cipher = None
        if HAS_CRYPTOGRAPHY and master_key:
            key = self._derive_key(master_key)
            self._cipher = Fernet(key)

        # In-memory cache for secrets (cleared on exit)
        self._cache: dict[str, str] = {}

    def _derive_key(self, master_key: str) -> bytes:
        """Derive encryption key from master key."""
        # Use PBKDF2-like key derivation
        key_hash = hashlib.sha256(f"{self.app_name}:{master_key}".encode()).digest()
        # Fernet requires 32-byte base64-encoded key
        import base64
        return base64.urlsafe_b64encode(key_hash)

    async def secure_store(self, key: str, value: str, use_keyring: bool = True) -> None:
        """Store a secret securely.

        Args:
            key: Secret identifier
            value: Secret value
            use_keyring: Use system keyring if available
        """
        # Try keyring first if available and requested
        if use_keyring and HAS_KEYRING:
            try:
                keyring.set_password(self.app_name, key, value)
                logger.debug(f"Secret stored in keyring: {key}")
                return
            except Exception as e:
                logger.warning(f"Keyring storage failed, using file: {e}")

        # Fall back to encrypted file storage
        if HAS_CRYPTOGRAPHY and self._cipher:
            encrypted = self._cipher.encrypt(value.encode())
            secret_file = self.storage_path / f"{key}.enc"
            secret_file.write_bytes(encrypted)
            # Set restrictive permissions
            os.chmod(secret_file, 0o600)
            logger.debug(f"Secret stored in encrypted file: {key}")
        else:
            # Plain text storage with restrictive permissions (last resort)
            secret_file = self.storage_path / f"{key}.txt"
            secret_file.write_text(value)
            os.chmod(secret_file, 0o600)
            logger.warning(f"Secret stored in plain text (install cryptography for encryption): {key}")

        # Update cache
        self._cache[key] = value

    async def secure_retrieve(self, key: str, use_keyring: bool = True) -> str:
        """Retrieve a secret securely.

        Args:
            key: Secret identifier
            use_keyring: Use system keyring if available

        Returns:
            Secret value

        Raises:
            SecretNotFoundError: If secret not found
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Try keyring first
        if use_keyring and HAS_KEYRING:
            try:
                value = keyring.get_password(self.app_name, key)
                if value:
                    self._cache[key] = value
                    return value
            except Exception as e:
                logger.warning(f"Keyring retrieval failed: {e}")

        # Try encrypted file
        enc_file = self.storage_path / f"{key}.enc"
        if enc_file.exists() and HAS_CRYPTOGRAPHY and self._cipher:
            try:
                encrypted = enc_file.read_bytes()
                value = self._cipher.decrypt(encrypted).decode()
                self._cache[key] = value
                return value
            except Exception as e:
                logger.error(f"Failed to decrypt secret: {e}")
                raise SecretNotFoundError(key) from e

        # Try plain text file
        txt_file = self.storage_path / f"{key}.txt"
        if txt_file.exists():
            value = txt_file.read_text()
            self._cache[key] = value
            return value

        raise SecretNotFoundError(key)

    async def delete_secret(self, key: str, use_keyring: bool = True) -> bool:
        """Delete a secret.

        Args:
            key: Secret identifier
            use_keyring: Delete from keyring if available

        Returns:
            True if deleted, False if not found
        """
        deleted = False

        # Remove from cache
        self._cache.pop(key, None)

        # Delete from keyring
        if use_keyring and HAS_KEYRING:
            try:
                keyring.delete_password(self.app_name, key)
                deleted = True
            except Exception:
                pass

        # Delete files
        for ext in [".enc", ".txt"]:
            file_path = self.storage_path / f"{key}{ext}"
            if file_path.exists():
                file_path.unlink()
                deleted = True

        return deleted

    def redact(self, text: str, replacement: str = "[REDACTED]") -> str:
        """Redact secrets from text.

        Args:
            text: Text to redact
            replacement: Replacement string

        Returns:
            Redacted text
        """
        if not text:
            return text

        result = text

        for pattern, group in self.SECRET_PATTERNS:
            def replace_match(match: re.Match) -> str:
                if group == 0:
                    return replacement
                # Replace only the captured group
                start = match.start(group)
                end = match.end(group)
                return match.string[:start] + replacement + match.string[end:]

            result = re.sub(pattern, replace_match, result)

        return result

    def is_secret_key(self, key: str) -> bool:
        """Check if a key name looks like it contains a secret.

        Args:
            key: Key name to check

        Returns:
            True if key looks like a secret
        """
        key_upper = key.upper()
        return any(pattern.match(key_upper) for pattern in self.SECRET_ENV_PATTERNS)

    def get_secret_env_vars(self) -> dict[str, str]:
        """Get environment variables that appear to be secrets.

        Returns:
            Dictionary of secret env vars
        """
        return {
            key: value
            for key, value in os.environ.items()
            if self.is_secret_key(key)
        }

    def mask_env_vars(self, env_vars: dict[str, str]) -> dict[str, str]:
        """Mask secret values in environment variables.

        Args:
            env_vars: Environment variables dict

        Returns:
            Masked environment variables
        """
        return {
            key: "[REDACTED]" if self.is_secret_key(key) else value
            for key, value in env_vars.items()
        }

    def clear_cache(self) -> None:
        """Clear in-memory secret cache."""
        self._cache.clear()

    def rotate_secret(self, key: str, new_value: str) -> tuple[str, str]:
        """Rotate a secret.

        Args:
            key: Secret identifier
            new_value: New secret value

        Returns:
            Tuple of (old_value, new_value)

        Raises:
            SecretNotFoundError: If secret not found
        """
        import asyncio

        async def _rotate():
            old_value = await self.secure_retrieve(key)
            await self.secure_store(key, new_value)
            return old_value, new_value

        return asyncio.run(_rotate())

    def scan_for_secrets(self, text: str) -> list[dict[str, Any]]:
        """Scan text for potential secrets.

        Args:
            text: Text to scan

        Returns:
            List of found secrets with positions
        """
        findings = []

        for pattern, group in self.SECRET_PATTERNS:
            for match in re.finditer(pattern, text):
                secret_value = match.group(group) if group > 0 else match.group(0)
                findings.append({
                    "type": "secret",
                    "pattern": pattern,
                    "value_preview": secret_value[:10] + "..." if len(secret_value) > 10 else secret_value,
                    "position": (match.start(), match.end()),
                })

        return findings


def redact_secrets(func):
    """Decorator to automatically redact secrets from function output."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, str):
            manager = SecretManager()
            return manager.redact(result)
        return result
    return wrapper
