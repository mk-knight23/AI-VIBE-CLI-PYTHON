"""Plugin manager for Friday AI.

Manages plugin lifecycle, versioning, and loading.
"""

import hashlib
import importlib.metadata
import json
import logging
from pathlib import Path
from typing import Any, Optional

from friday_ai.config.config import Config

logger = logging.getLogger(__name__)


class PluginVersion:
    """Plugin version information."""

    def __init__(self, major: int, minor: int, patch: int):
        """Initialize plugin version.

        Args:
            major: Major version number
            minor: Minor version number
            patch: Patch version number
        """
        self.major = major
        self.minor = minor
        self.patch = patch

    def __str__(self) -> str:
        """Return version string."""
        return f"{self.major}.{self.minor}.{self.patch}"

    def increment(self, amount: int = 1) -> "PluginVersion":
        """Increment patch version.

        Args:
            amount: Number to increment by

        Returns:
            New version object
        """
        self.patch += amount
        return self

    def __eq__(self, other: Any) -> bool:
        """Check version equality."""
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch


class PluginMetadata:
    """Metadata for a plugin."""

    def __init__(
        self,
        name: str,
        version: PluginVersion,
        description: str,
        author: str,
        dependencies: list[str] = None,
        friday_version: str = "2.1.0",
    ):
        """Initialize plugin metadata.

        Args:
            name: Plugin name
            version: Plugin version
            description: Plugin description
            author: Plugin author
            dependencies: List of dependencies
            friday_version: Required Friday version
        """
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.dependencies = dependencies or []
        self.friday_version = friday_version


class Plugin:
    """Represents a loadable plugin."""

    def __init__(self, file_path: Path):
        """Initialize plugin from file path.

        Args:
            file_path: Path to plugin file
        """
        self.file_path = file_path
        self.metadata = None
        self._module = None

    def load(self) -> bool:
        """Load plugin metadata and module.

        Returns:
            True if loaded successfully
        """
        try:
            # Load metadata
            meta_path = self.file_path.with_suffix(".json")
            if not meta_path.exists():
                logger.warning(f"Plugin metadata not found: {meta_path}")
                return False

            with open(meta_path, "r") as f:
                metadata = json.load(f)

            self.metadata = PluginMetadata(**metadata)

            # Load module
            self._module = importlib.import_module(f"friday_ai.plugins.{self.metadata.name}")
            self._module = importlib.import_module(f"friday_ai.plugins.{self.metadata.name}")
            logger.info(f"Loaded plugin: {self.metadata.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load plugin {self.metadata.name}: {e}")
            return False


class PluginManager:
    """Manages plugin discovery and loading."""

    def __init__(self, config: Config):
        """Initialize plugin manager.

        Args:
            config: Configuration
        """
        self.config = config
        self.plugins = {}
        self.plugin_dir = Path.cwd / "friday_ai/plugins"

    def discover(self) -> None:
        """Discover and load all plugins."""
        if not self.plugin_dir.exists():
            logger.info("No plugins directory found")
            return

        for plugin_file in self.plugin_dir.glob("*.json"):
            plugin = Plugin(plugin_file)
            if plugin.load():
                self.plugins[plugin.metadata.name] = plugin

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get loaded plugin by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance or None
        """
        return self.plugins.get(name)
