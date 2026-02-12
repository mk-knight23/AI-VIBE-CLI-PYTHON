"""Path utilities with security enhancements.

Provides secure path resolution with traversal prevention.
"""

from pathlib import Path
from typing import Union


def resolve_path(base: Union[str, Path], path: Union[str, Path]) -> Path:
    """Resolve path relative to base and validate it's within bounds.

    Args:
        base: Base directory path
        path: Path to resolve (can be absolute or relative)

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path tries to traverse outside base directory
    """
    target = Path(path)
    base_path = Path(base).resolve()

    # Resolve to absolute path
    if target.is_absolute():
        resolved = target.resolve()
    else:
        # For relative paths, join with base first
        resolved = (base_path / target).resolve()

    # Security: Prevent path traversal attacks
    # Verify resolved path is within base directory
    try:
        resolved.relative_to(base_path)
    except ValueError:
        raise ValueError(
            f"Path traversal detected: {path} attempts to access "
            f"files outside base directory {base_path}"
        )

    return resolved


def is_safe_path(path: Path, base: Path) -> bool:
    """Check if path is safe from traversal attacks.

    Args:
        path: Path to check
        base: Base directory path

    Returns:
        True if path is within base directory bounds
    """
    try:
        path.relative_to(base)
        return True
    except ValueError:
            return False
