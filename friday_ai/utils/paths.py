"""Path utilities with security enhancements.

Provides secure path resolution with traversal prevention.
"""

import os
import re
from pathlib import Path

# FIX-013: Valid filename pattern (alphanumeric, hyphens, underscores, dots)
_VALID_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")

# Binary file signatures (magic bytes)
_BINARY_SIGNATURES = [
    b"\x00",  # Null byte
    b"\xff\xfe",  # UTF-16 LE
    b"\xfe\xff",  # UTF-16 BE
    b"\xff\xfb",  # JPEG
    b"\x89PNG",  # PNG
    b"GIF8",  # GIF
    b"PK\x03\x04",  # ZIP
    b"\x1f\x8b",  # GZIP
    b"ELF",  # ELF executable
    b"\xca\xfe\xba\xbe",  # Mach-O binary
    b"MZ",  # Windows executable
]


def is_binary_file(path: str | Path) -> bool:
    """Check if a file is binary by examining its content.

    Args:
        path: Path to the file to check

    Returns:
        True if file appears to be binary, False if text

    Note:
        This is a heuristic check that looks for binary signatures
        and null bytes in the first 8KB of the file.
    """
    try:
        path_obj = Path(path)
        if not path_obj.is_file():
            return False

        # Read first 8KB for checking
        with open(path_obj, "rb") as f:
            chunk = f.read(8192)

        if not chunk:
            return False  # Empty file is considered text

        # Check for binary signatures
        for signature in _BINARY_SIGNATURES:
            if chunk.startswith(signature):
                return True

        # Check for null bytes (strong indicator of binary)
        if b"\x00" in chunk:
            return True

        # Check if content is mostly text (high ratio of printable characters)
        text_characters = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
        non_text = chunk.translate(None, text_characters)
        return len(non_text) / len(chunk) > 0.3 if chunk else False

    except OSError:
        return False


def is_text_file(path: str | Path) -> bool:
    """Check if a file is text (opposite of is_binary_file).

    Args:
        path: Path to the file to check

    Returns:
        True if file appears to be text, False if binary
    """
    return not is_binary_file(path)


def _validate_filename(name: str) -> bool:
    """Validate a single filename component.

    Args:
        name: Filename to validate

    Returns:
        True if valid, False otherwise
    """
    if not name or len(name) > 255:
        return False
    # Reject path separators and null bytes
    if "/" in name or "\\" in name or "\x00" in name:
        return False
    # Check for directory traversal attempts
    if name in ("..", "."):
        return False
    return bool(_VALID_NAME_PATTERN.match(name))


def ensure_parent_directory(path: str | Path) -> Path:
    """Ensure parent directory of a path exists.

    Args:
        path: Path whose parent directory should be created

    Returns:
        The path with ensured parent directory

    Example:
        path = ensure_parent_directory("dir/subdir/file.txt")
        # Creates dir/subdir/ if it doesn't exist
    """
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    return path_obj


def resolve_path(base: str | Path, path: str | Path) -> Path:
    """Resolve path relative to base and validate it's within bounds.

    Args:
        base: Base directory path
        path: Path to resolve (must be relative, no absolute paths allowed)

    Returns:
        Resolved absolute path

    Raises:
        ValueError: If path tries to traverse outside base directory or contains invalid characters
    """
    target = Path(path)
    base_path = Path(base).resolve()

    # FIX-013: Reject absolute paths entirely
    if target.is_absolute():
        raise ValueError(f"Absolute paths not allowed: {path}. Use relative paths only.")

    # FIX-013: Check for symlinks in path components
    for part in target.parts:
        if not _validate_filename(part):
            raise ValueError(
                f"Invalid path component: {part}. "
                f"Path components must be alphanumeric with hyphens, underscores, or dots only."
            )

    # FIX-013: Check for symlinks before resolving the full path
    # Build the path incrementally and check each component
    current = base_path
    for part in target.parts:
        next_path = current / part
        # Check if this component exists and is a symlink
        if next_path.exists() and next_path.is_symlink():
            raise ValueError(
                f"Symbolic links not allowed in path: {part} at {next_path}. "
                f"Symlinks can be used to escape the base directory."
            )
        current = next_path

    # Resolve to absolute path
    resolved = (base_path / target).resolve()

    # FIX-013: Additional check - ensure resolved path starts with base_path
    # This catches edge cases like symlinks that escape the base directory
    resolved_str = str(resolved)
    base_str = str(base_path)

    # Ensure base path ends with separator for proper prefix check
    if not base_str.endswith(os.sep):
        base_str += os.sep

    if not resolved_str.startswith(base_str):
        raise ValueError(
            f"Path traversal detected: {path} resolves to {resolved} "
            f"which is outside base directory {base_path}"
        )

    # Also check with pathlib for defense in depth
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

    Performs comprehensive security checks including:
    - Path traversal validation (using pathlib.relative_to)
    - String prefix validation (to catch edge cases)
    - Symlink detection

    Args:
        path: Path to check
        base: Base directory path

    Returns:
        True if path is within base directory bounds and contains no symlinks
    """
    try:
        # Check that path is relative to base
        path.relative_to(base)

        # FIX-013: Additional string prefix check for defense in depth
        path_str = str(path)
        base_str = str(base)

        # Ensure base path ends with separator for proper prefix check
        if not base_str.endswith(os.sep):
            base_str += os.sep

        if not path_str.startswith(base_str):
            return False

        # FIX-013: Check for symlinks in the path
        # Only check if the path exists
        if path.exists():
            current = base
            # Check each component of the relative path
            relative_parts = path.relative_to(base).parts
            for part in relative_parts:
                current = current / part
                if current.is_symlink():
                    return False

        return True
    except ValueError:
        return False


def display_path_rel_to_cwd(path: str | Path, cwd: str | Path | None = None) -> Path:
    """Display path relative to current working directory.

    Args:
        path: Path to display
        cwd: Current working directory (defaults to os.getcwd())

    Returns:
        Path relative to cwd if possible, otherwise absolute path
    """
    path_obj = Path(path)
    if cwd is None:
        cwd = Path.cwd()
    else:
        cwd = Path(cwd)

    try:
        return path_obj.relative_to(cwd)
    except ValueError:
        # Path is not relative to cwd, return as-is
        return path_obj
