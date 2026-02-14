"""Remote Skills Registry client for community skills.

Provides functionality to search, discover, and install skills
from a community registry.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class RemoteSkillInfo:
    """Information about a remote skill.

    Attributes:
        name: Skill name
        description: Skill description
        version: Skill version
        author: Skill author
        tags: List of tags for categorization
        url: Download URL
        dependencies: List of required skills
        downloads: Download count
        rating: Community rating (0-5)
    """

    name: str
    description: str
    version: str
    author: str
    tags: list[str] = field(default_factory=list)
    url: str = ""
    dependencies: list[str] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RemoteSkillInfo:
        """Create RemoteSkillInfo from dictionary.

        Args:
            data: Dictionary containing skill information.

        Returns:
            RemoteSkillInfo instance.
        """
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "unknown"),
            tags=data.get("tags", []),
            url=data.get("url", ""),
            dependencies=data.get("dependencies", []),
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "url": self.url,
            "dependencies": self.dependencies,
            "downloads": self.downloads,
            "rating": self.rating,
        }


class RemoteSkillClient:
    """Client for interacting with remote skills registry.

    Features:
    - Search skills by name, tags, or description
    - Install skills from registry
    - Update installed skills
    - Cache management for performance
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize remote skill client.

        Args:
            config: Configuration dictionary with:
                - registry_url: Base URL of registry
                - cache_ttl: Cache TTL in seconds (default: 3600)
                - timeout: Request timeout in seconds (default: 30)
        """
        self.config = config
        self.registry_url = config.get("registry_url", "https://registry.skills.ai")
        self.cache_ttl = config.get("cache_ttl", 3600)
        self.timeout = config.get("timeout", 30)
        self._cache: dict[str, dict] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session.

        Returns:
            HTTP session.
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def search_skills(
        self,
        query: str,
        tags: Optional[list[str]] = None,
        limit: int = 20,
    ) -> list[RemoteSkillInfo]:
        """Search for skills in the registry.

        Args:
            query: Search query string.
            tags: Optional tag filters.
            limit: Maximum results to return.

        Returns:
            List of matching skills.
        """
        # Check cache
        cache_key = f"search:{query}:{','.join(tags or [])}:{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.debug(f"Cache hit for search: {query}")
            return [RemoteSkillInfo.from_dict(s) for s in cached]

        # Build search URL
        search_url = urljoin(
            self.registry_url, f"/api/v1/skills/search?q={query}&limit={limit}"
        )
        if tags:
            tag_param = ",".join(tags)
            search_url += f"&tags={tag_param}"

        try:
            session = await self._get_session()
            async with session.get(search_url) as response:
                if response.status == 200:
                    data = await response.json()
                    skills = data.get("skills", [])

                    # Cache results
                    self._add_to_cache(cache_key, skills)

                    return [RemoteSkillInfo.from_dict(s) for s in skills]
                else:
                    logger.warning(
                        f"Search failed with status {response.status}: {response.text}"
                    )
                    return []

        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    async def get_skill_info(self, skill_name: str) -> Optional[RemoteSkillInfo]:
        """Get detailed information about a skill.

        Args:
            skill_name: Name of the skill.

        Returns:
            Skill info or None if not found.
        """
        # Check cache
        cache_key = f"info:{skill_name}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return RemoteSkillInfo.from_dict(cached[0] if cached else None)

        info_url = urljoin(self.registry_url, f"/api/v1/skills/{skill_name}")

        try:
            session = await self._get_session()
            async with session.get(info_url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Cache result
                    self._add_to_cache(cache_key, [data])

                    return RemoteSkillInfo.from_dict(data)
                else:
                    logger.warning(f"Failed to get skill info: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Get skill info error: {e}")
            return None

    async def install_skill(
        self,
        skill_name: str,
        url: str,
        target_dir: Path,
        install_deps: bool = True,
    ) -> bool:
        """Install a skill from the registry.

        Args:
            skill_name: Name of the skill.
            url: Download URL.
            target_dir: Target installation directory.
            install_deps: Whether to install dependencies.

        Returns:
            True if installation succeeded.
        """
        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Download failed: {response.status}")
                    return False

                content = await response.read()

                # Try to parse as JSON first
                try:
                    data = json.loads(content.decode())
                    skill_content = data.get("content", content.decode())
                    dependencies = data.get("dependencies", [])
                except (json.JSONDecodeError, UnicodeDecodeError):
                    skill_content = content.decode()
                    dependencies = []

                # Create skill directory
                skill_dir = target_dir / skill_name
                skill_dir.mkdir(parents=True, exist_ok=True)

                # Write SKILL.md
                skill_file = skill_dir / "SKILL.md"
                skill_file.write_text(skill_content, encoding="utf-8")

                # Write config.json
                config_file = skill_dir / "config.json"
                config_file.write_text(
                    json.dumps(
                        {
                            "name": skill_name,
                            "version": "1.0.0",
                            "dependencies": dependencies,
                            "installed_from": url,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )

                logger.info(f"Installed skill: {skill_name}")

                # Install dependencies if requested
                if install_deps and dependencies:
                    for dep in dependencies:
                        dep_info = await self.get_skill_info(dep)
                        if dep_info:
                            await self.install_skill(
                                dep, dep_info.url, target_dir, install_deps
                            )

                return True

        except Exception as e:
            logger.error(f"Install skill error: {e}")
            return False

    async def update_skill(
        self,
        skill_name: str,
        url: str,
        skills_dir: Path,
    ) -> bool:
        """Update an installed skill.

        Args:
            skill_name: Name of the skill.
            url: Download URL.
            skills_dir: Skills directory.

        Returns:
            True if update succeeded.
        """
        skill_dir = skills_dir / skill_name
        if not skill_dir.exists():
            logger.warning(f"Skill not installed: {skill_name}")
            return False

        # Backup current version
        backup_file = skill_dir / "SKILL.md.bak"
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            backup_file.write_text(skill_file.read_text(encoding="utf-8"), encoding="utf-8")

        # Install new version
        success = await self.install_skill(skill_name, url, skills_dir, False)

        # Remove backup on success
        if success and backup_file.exists():
            backup_file.unlink()

        return success

    async def list_installed_skills(self, skills_dir: Path) -> list[str]:
        """List all installed skills.

        Args:
            skills_dir: Skills directory path.

        Returns:
            List of skill names.
        """
        if not skills_dir.exists():
            return []

        skills = []
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skills.append(skill_dir.name)

        return sorted(skills)

    def clear_cache(self) -> None:
        """Clear the search cache."""
        self._cache.clear()
        logger.debug("Cache cleared")

    def _get_from_cache(self, key: str) -> Optional[list]:
        """Get data from cache if not expired.

        Args:
            key: Cache key.

        Returns:
            Cached data or None.
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        age = time.time() - entry["timestamp"]

        if age > self.cache_ttl:
            del self._cache[key]
            return None

        return entry["data"]

    def _add_to_cache(self, key: str, data: list) -> None:
        """Add data to cache.

        Args:
            key: Cache key.
            data: Data to cache.
        """
        self._cache[key] = {
            "data": data,
            "timestamp": time.time(),
        }

        # Limit cache size
        if len(self._cache) > 100:
            # Remove oldest 20 entries
            oldest_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"],
            )[:20]
            for k in oldest_keys:
                del self._cache[k]
