"""Skill Installer - Install, update, and manage skills from registry."""

import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging

from friday_ai.claude_integration.skills.registry import (
    SkillMetadata,
    SkillVersion,
    get_skill_metadata,
    resolve_dependencies,
    search_skills,
    get_popular_skills,
    get_all_categories,
    list_skills_by_category,
    REMOTE_SKILL_REGISTRY,
)

logger = logging.getLogger(__name__)


class SkillInstaller:
    """Installer for managing skills from the registry."""

    def __init__(self, skills_dir: Optional[str] = None):
        """Initialize the skill installer.

        Args:
            skills_dir: Directory where skills are stored.
        """
        self.skills_dir = Path(skills_dir) if skills_dir else Path.cwd() / ".claude" / "skills"
        self._installed_skills: dict[str, dict] = {}
        self._load_installed_skills()

    def _load_installed_skills(self) -> None:
        """Load information about installed skills."""
        manifest_path = self.skills_dir / ".installed.json"
        if manifest_path.exists():
            with open(manifest_path, "r") as f:
                self._installed_skills = json.load(f)

    def _save_installed_skills(self) -> None:
        """Save information about installed skills."""
        manifest_path = self.skills_dir
        manifest_path.mkdir(parents=True, exist_ok=True)
        with open(manifest_path / ".installed.json", "w") as f:
            json.dump(self._installed_skills, f, indent=2)

    async def install_skill(
        self,
        skill_name: str,
        version: Optional[str] = None,
        include_dependencies: bool = True,
    ) -> dict:
        """Install a skill from the registry.

        Args:
            skill_name: Name of the skill to install.
            version: Specific version to install (defaults to latest).
            include_dependencies: Whether to install dependencies.

        Returns:
            Installation result dictionary.
        """
        result = {
            "success": False,
            "skill": skill_name,
            "version": version,
            "dependencies": [],
            "message": "",
        }

        # Get skill metadata
        skill_meta = get_skill_metadata(skill_name)
        if not skill_meta:
            result["message"] = f"Skill '{skill_name}' not found in registry"
            return result

        # Determine version
        if version is None:
            version = skill_meta.latest_version

        skill_version = skill_meta.versions.get(version)
        if not skill_version:
            result["message"] = f"Version {version} not found for skill '{skill_name}'"
            return result

        logger.info(f"Installing skill '{skill_name}' version {version}")

        # Install dependencies first
        if include_dependencies:
            deps = resolve_dependencies(skill_name)
            for dep in deps:
                if dep not in self._installed_skills:
                    dep_result = await self.install_skill(dep, include_dependencies=True)
                    result["dependencies"].append(dep_result)

        # Create skill directory
        skill_path = self.skills_dir / skill_name
        version_path = skill_path / version
        version_path.mkdir(parents=True, exist_ok=True)

        try:
            # Download and extract skill
            await self._download_and_extract(skill_version.download_url, version_path)

            # Create symlink to latest version
            latest_link = skill_path / "latest"
            if latest_link.exists() or latest_link.is_symlink():
                latest_link.unlink()
            latest_link.symlink_to(version, target_is_directory=True)

            # Save installation info
            self._installed_skills[skill_name] = {
                "version": version,
                "installed_at": datetime.utcnow().isoformat(),
                "download_url": skill_version.download_url,
                "checksum": await self._compute_checksum(version_path),
                "metadata": {
                    "name": skill_meta.name,
                    "description": skill_meta.description,
                    "author": skill_meta.author,
                    "category": skill_meta.category,
                },
            }
            self._save_installed_skills()

            result["success"] = True
            result["message"] = f"Successfully installed '{skill_name}' version {version}"

        except Exception as e:
            result["message"] = f"Failed to install skill: {str(e)}"
            # Cleanup on failure
            if version_path.exists():
                shutil.rmtree(version_path)

        return result

    async def _download_and_extract(self, url: str, dest_path: Path) -> None:
        """Download and extract a skill package.

        Args:
            url: URL to download.
            dest_path: Destination directory.
        """
        # For now, just create the directory structure
        # In production, this would download and extract from URL
        logger.info(f"Setting up skill at {dest_path}")

        # Create basic skill structure
        (dest_path / "skill.json").write_text(json.dumps({
            "name": dest_path.parent.name,
            "version": dest_path.name,
        }, indent=2))

    async def _compute_checksum(self, path: Path) -> str:
        """Compute checksum for a skill directory.

        Args:
            path: Path to compute checksum for.

        Returns:
            SHA256 checksum.
        """
        hasher = hashlib.sha256()
        for root, dirs, files in os.walk(path):
            for file in sorted(files):
                file_path = Path(root) / file
                relative = file_path.relative_to(path)
                hasher.update(str(relative).encode())
                hasher.update(file_path.read_bytes())
        return hasher.hexdigest()

    async def update_skill(self, skill_name: str) -> dict:
        """Update a skill to the latest version.

        Args:
            skill_name: Name of the skill to update.

        Returns:
            Update result.
        """
        result = {
            "success": False,
            "skill": skill_name,
            "old_version": None,
            "new_version": None,
            "message": "",
        }

        if skill_name not in self._installed_skills:
            result["message"] = f"Skill '{skill_name}' is not installed"
            return result

        old_info = self._installed_skills[skill_name]
        result["old_version"] = old_info["version"]

        skill_meta = get_skill_metadata(skill_name)
        if not skill_meta:
            result["message"] = f"Skill '{skill_name}' not found in registry"
            return result

        new_version = skill_meta.latest_version
        if old_info["version"] == new_version:
            result["message"] = f"Skill '{skill_name}' is already at latest version"
            return result

        # Install new version
        install_result = await self.install_skill(skill_name, version=new_version)
        if install_result["success"]:
            result["success"] = True
            result["new_version"] = new_version
            result["message"] = f"Updated '{skill_name}' from {old_info['version']} to {new_version}"
        else:
            result["message"] = install_result["message"]

        return result

    async def remove_skill(self, skill_name: str, remove_dependencies: bool = False) -> dict:
        """Remove an installed skill.

        Args:
            skill_name: Name of the skill to remove.
            remove_dependencies: Whether to also remove unused dependencies.

        Returns:
            Removal result.
        """
        result = {
            "success": False,
            "skill": skill_name,
            "message": "",
        }

        if skill_name not in self._installed_skills:
            result["message"] = f"Skill '{skill_name}' is not installed"
            return result

        try:
            skill_path = self.skills_dir / skill_name
            if skill_path.exists():
                shutil.rmtree(skill_path)

            del self._installed_skills[skill_name]
            self._save_installed_skills()

            result["success"] = True
            result["message"] = f"Removed skill '{skill_name}'"

        except Exception as e:
            result["message"] = f"Failed to remove skill: {str(e)}"

        return result

    def list_installed_skills(self) -> list[dict]:
        """List all installed skills.

        Returns:
            List of installed skill information.
        """
        return [
            {
                "name": name,
                **info,
            }
            for name, info in self._installed_skills.items()
        ]

    def is_installed(self, skill_name: str) -> bool:
        """Check if a skill is installed.

        Args:
            skill_name: Name of the skill.

        Returns:
            True if installed.
        """
        return skill_name in self._installed_skills

    def get_installed_version(self, skill_name: str) -> Optional[str]:
        """Get the installed version of a skill.

        Args:
            skill_name: Name of the skill.

        Returns:
            Version string or None.
        """
        info = self._installed_skills.get(skill_name)
        return info["version"] if info else None

    async def check_for_updates(self) -> list[dict]:
        """Check for updates to installed skills.

        Returns:
            List of skills with available updates.
        """
        updates = []
        for skill_name, info in self._installed_skills.items():
            skill_meta = get_skill_metadata(skill_name)
            if skill_meta and skill_meta.latest_version != info["version"]:
                updates.append({
                    "skill": skill_name,
                    "current_version": info["version"],
                    "latest_version": skill_meta.latest_version,
                    "description": skill_meta.description,
                })
        return updates

    def search_registry(self, query: str) -> list[dict]:
        """Search the skill registry.

        Args:
            query: Search query.

        Returns:
            List of matching skills.
        """
        skills = search_skills(query)
        return [
            {
                "name": s.name,
                "description": s.description,
                "author": s.author,
                "category": s.category,
                "tags": s.tags,
                "latest_version": s.latest_version,
                "downloads": s.downloads,
                "rating": s.rating,
                "installed": self.is_installed(s.name),
            }
            for s in skills
        ]

    def browse_by_category(self, category: str) -> list[dict]:
        """Browse skills by category.

        Args:
            category: Category name.

        Returns:
            List of skills in the category.
        """
        skills = list_skills_by_category(category)
        return [
            {
                "name": s.name,
                "description": s.description,
                "author": s.author,
                "latest_version": s.latest_version,
                "downloads": s.downloads,
                "rating": s.rating,
                "installed": self.is_installed(s.name),
            }
            for s in skills
        ]

    def get_recommended_skills(self, limit: int = 5) -> list[dict]:
        """Get recommended popular skills.

        Args:
            limit: Maximum number of skills.

        Returns:
            List of popular skills.
        """
        skills = get_popular_skills(limit)
        return [
            {
                "name": s.name,
                "description": s.description,
                "author": s.author,
                "category": s.category,
                "downloads": s.downloads,
                "rating": s.rating,
                "installed": self.is_installed(s.name),
            }
            for s in skills
        ]


class SkillVersionManager:
    """Manager for skill versions."""

    def __init__(self, skills_dir: Optional[str] = None):
        """Initialize the version manager.

        Args:
            skills_dir: Directory where skills are stored.
        """
        self.skills_dir = Path(skills_dir) if skills_dir else Path.cwd() / ".claude" / "skills"
        self._versions_cache: dict[str, list[str]] = {}

    def get_installed_versions(self, skill_name: str) -> list[str]:
        """Get all installed versions of a skill.

        Args:
            skill_name: Name of the skill.

        Returns:
            List of version strings.
        """
        skill_path = self.skills_dir / skill_name
        if not skill_path.exists():
            return []

        versions = []
        for item in skill_path.iterdir():
            if item.is_dir() and item.name != "latest":
                versions.append(item.name)

        return sorted(versions, key=lambda v: [int(x) for x in v.split(".")])

    def switch_version(self, skill_name: str, version: str) -> bool:
        """Switch to a different version of a skill.

        Args:
            skill_name: Name of the skill.
            version: Version to switch to.

        Returns:
            True if successful.
        """
        skill_path = self.skills_dir / skill_name
        version_path = skill_path / version
        latest_link = skill_path / "latest"

        if not version_path.exists():
            return False

        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(version, target_is_directory=True)

        return True

    def get_current_version(self, skill_name: str) -> Optional[str]:
        """Get the current active version of a skill.

        Args:
            skill_name: Name of the skill.

        Returns:
            Current version string or None.
        """
        skill_path = self.skills_dir / skill_name
        latest_link = skill_path / "latest"

        if latest_link.is_symlink():
            return os.readlink(str(latest_link))

        versions = self.get_installed_versions(skill_name)
        return versions[-1] if versions else None

    def compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings.

        Args:
            v1: First version.
            v2: Second version.

        Returns:
            -1 if v1 < v2, 0 if equal, 1 if v1 > v2.
        """
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]

        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1

        if len(parts1) < len(parts2):
            return -1
        elif len(parts1) > len(parts2):
            return 1

        return 0

    def cleanup_old_versions(
        self,
        skill_name: str,
        keep_versions: int = 2,
    ) -> list[str]:
        """Remove old versions of a skill.

        Args:
            skill_name: Name of the skill.
            keep_versions: Number of recent versions to keep.

        Returns:
            List of removed versions.
        """
        versions = self.get_installed_versions(skill_name)
        current = self.get_current_version(skill_name)

        # Remove current version from list
        if current in versions:
            versions.remove(current)

        # Keep only the most recent versions
        to_remove = versions[:-keep_versions] if len(versions) > keep_versions else []

        removed = []
        skill_path = self.skills_dir / skill_name
        for version in to_remove:
            version_path = skill_path / version
            if version_path.exists():
                shutil.rmtree(version_path)
                removed.append(version)

        return removed
