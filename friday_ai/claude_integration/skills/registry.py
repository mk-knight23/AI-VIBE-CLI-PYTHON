"""Remote Skill Registry - For community skills sharing."""

from dataclasses import dataclass, field
from typing import Optional
import json
from pathlib import Path


@dataclass
class SkillVersion:
    """Version information for a skill."""

    version: str
    description: str
    friday_version: str  # Minimum Friday version required
    download_url: str
    changelog: Optional[str] = None
    release_date: Optional[str] = None


@dataclass
class SkillMetadata:
    """Metadata for a skill in the registry."""

    name: str
    description: str
    author: str
    category: str
    tags: list[str]
    versions: dict[str, SkillVersion]
    latest_version: str
    downloads: int
    rating: float
    repo_url: Optional[str] = None
    docs_url: Optional[str] = None
    requires_skills: list[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# In-memory registry (in production, this would be a remote API)
REMOTE_SKILL_REGISTRY: dict[str, SkillMetadata] = {
    "web-dev-master": SkillMetadata(
        name="web-dev-master",
        description="Complete web development skill with React, Vue, Next.js patterns",
        author="Friday AI Team",
        category="Frontend",
        tags=["react", "vue", "nextjs", "frontend", "web"],
        versions={
            "1.0.0": SkillVersion(
                version="1.0.0",
                description="Initial release with React and Vue patterns",
                friday_version=">=1.0.0",
                download_url="https://registry.friday.ai/skills/web-dev-master/v1.0.0.zip",
                changelog="Initial release",
                release_date="2024-01-01",
            ),
        },
        latest_version="1.0.0",
        downloads=1500,
        rating=4.8,
        repo_url="https://github.com/friday-ai/web-dev-master",
        docs_url="https://docs.friday.ai/skills/web-dev-master",
        requires_skills=["frontend-patterns"],
    ),
    "api-design-pro": SkillMetadata(
        name="api-design-pro",
        description="REST and GraphQL API design best practices",
        author="API Expert",
        category="Backend",
        tags=["api", "rest", "graphql", "backend", "design"],
        versions={
            "1.0.0": SkillVersion(
                version="1.0.0",
                description="REST and GraphQL patterns",
                friday_version=">=1.0.0",
                download_url="https://registry.friday.ai/skills/api-design-pro/v1.0.0.zip",
                changelog="Initial release",
                release_date="2024-01-15",
            ),
        },
        latest_version="1.0.0",
        downloads=1200,
        rating=4.6,
        repo_url="https://github.com/friday-ai/api-design-pro",
        docs_url="https://docs.friday.ai/skills/api-design-pro",
        requires_skills=[],
    ),
    "cloud-architect": SkillMetadata(
        name="cloud-architect",
        description="AWS, GCP, Azure cloud architecture patterns",
        author="Cloud Team",
        category="DevOps",
        tags=["aws", "gcp", "azure", "cloud", "architecture"],
        versions={
            "1.0.0": SkillVersion(
                version="1.0.0",
                description="Multi-cloud architecture patterns",
                friday_version=">=1.0.0",
                download_url="https://registry.friday.ai/skills/cloud-architect/v1.0.0.zip",
                changelog="Initial release",
                release_date="2024-02-01",
            ),
        },
        latest_version="1.0.0",
        downloads=800,
        rating=4.5,
        repo_url="https://github.com/friday-ai/cloud-architect",
        docs_url="https://docs.friday.ai/skills/cloud-architect",
        requires_skills=["security-review"],
    ),
    "database-master": SkillMetadata(
        name="database-master",
        description="PostgreSQL, MongoDB, Redis optimization patterns",
        author="DB Team",
        category="Database",
        tags=["postgresql", "mongodb", "redis", "database", "sql"],
        versions={
            "1.0.0": SkillVersion(
                version="1.0.0",
                description="Database optimization patterns",
                friday_version=">=1.0.0",
                download_url="https://registry.friday.ai/skills/database-master/v1.0.0.zip",
                changelog="Initial release",
                release_date="2024-02-15",
            ),
        },
        latest_version="1.0.0",
        downloads=950,
        rating=4.7,
        repo_url="https://github.com/friday-ai/database-master",
        docs_url="https://docs.friday.ai/skills/database-master",
        requires_skills=[],
    ),
    "security-expert": SkillMetadata(
        name="security-expert",
        description="Comprehensive security patterns and vulnerability scanning",
        author="Security Team",
        category="Security",
        tags=["security", "owasp", "vulnerability", "audit"],
        versions={
            "1.0.0": SkillVersion(
                version="1.0.0",
                description="Security patterns and scanning",
                friday_version=">=1.0.0",
                download_url="https://registry.friday.ai/skills/security-expert/v1.0.0.zip",
                changelog="Initial release",
                release_date="2024-03-01",
            ),
        },
        latest_version="1.0.0",
        downloads=1100,
        rating=4.9,
        repo_url="https://github.com/friday-ai/security-expert",
        docs_url="https://docs.friday.ai/skills/security-expert",
        requires_skills=[],
    ),
    "testing-champion": SkillMetadata(
        name="testing-champion",
        description="Unit, integration, and E2E testing patterns",
        author="QA Team",
        category="Testing",
        tags=["testing", "pytest", "jest", "e2e", "coverage"],
        versions={
            "1.0.0": SkillVersion(
                version="1.0.0",
                description="Comprehensive testing patterns",
                friday_version=">=1.0.0",
                download_url="https://registry.friday.ai/skills/testing-champion/v1.0.0.zip",
                changelog="Initial release",
                release_date="2024-03-15",
            ),
        },
        latest_version="1.0.0",
        downloads=1300,
        rating=4.8,
        repo_url="https://github.com/friday-ai/testing-champion",
        docs_url="https://docs.friday.ai/skills/testing-champion",
        requires_skills=[],
    ),
}


def get_skill_metadata(name: str) -> Optional[SkillMetadata]:
    """Get metadata for a skill.

    Args:
        name: Skill name.

    Returns:
        Skill metadata or None.
    """
    return REMOTE_SKILL_REGISTRY.get(name)


def search_skills(query: str) -> list[SkillMetadata]:
    """Search for skills in the registry.

    Args:
        query: Search query.

    Returns:
        List of matching skills.
    """
    query_lower = query.lower()
    results = []
    for skill in REMOTE_SKILL_REGISTRY.values():
        if (query_lower in skill.name.lower() or
            query_lower in skill.description.lower() or
            any(query_lower in tag.lower() for tag in skill.tags)):
            results.append(skill)
    return results


def list_skills_by_category(category: str) -> list[SkillMetadata]:
    """List skills by category.

    Args:
        category: Category name.

    Returns:
        List of skills in the category.
    """
    return [s for s in REMOTE_SKILL_REGISTRY.values() if s.category.lower() == category.lower()]


def get_all_categories() -> list[str]:
    """Get all skill categories.

    Returns:
        List of category names.
    """
    return list(set(s.category for s in REMOTE_SKILL_REGISTRY.values()))


def get_popular_skills(limit: int = 10) -> list[SkillMetadata]:
    """Get most popular skills.

    Args:
        limit: Maximum number of skills to return.

    Returns:
        List of popular skills sorted by downloads.
    """
    sorted_skills = sorted(REMOTE_SKILL_REGISTRY.values(), key=lambda x: x.downloads, reverse=True)
    return sorted_skills[:limit]


def get_top_rated_skills(limit: int = 10) -> list[SkillMetadata]:
    """Get highest rated skills.

    Args:
        limit: Maximum number of skills to return.

    Returns:
        List of top rated skills.
    """
    sorted_skills = sorted(REMOTE_SKILL_REGISTRY.values(), key=lambda x: x.rating, reverse=True)
    return sorted_skills[:limit]


def get_new_skills(limit: int = 10) -> list[SkillMetadata]:
    """Get newest skills.

    Args:
        limit: Maximum number of skills to return.

    Returns:
        List of newest skills.
    """
    sorted_skills = sorted(
        REMOTE_SKILL_REGISTRY.values(),
        key=lambda x: x.updated_at or "",
        reverse=True
    )
    return sorted_skills[:limit]


def resolve_dependencies(skill_name: str) -> list[str]:
    """Resolve dependencies for a skill.

    Args:
        skill_name: Name of the skill.

    Returns:
        List of dependent skill names.
    """
    skill = get_skill_metadata(skill_name)
    if not skill:
        return []

    # Get direct dependencies
    dependencies = list(skill.requires_skills)

    # Resolve transitive dependencies
    all_dependencies = set(dependencies)
    for dep in dependencies:
        transitive = resolve_dependencies(dep)
        all_dependencies.update(transitive)

    return list(all_dependencies)


def export_registry() -> dict:
    """Export the registry as JSON.

    Returns:
        Registry dictionary.
    """
    registry_data = {}
    for name, skill in REMOTE_SKILL_REGISTRY.items():
        registry_data[name] = {
            "name": skill.name,
            "description": skill.description,
            "author": skill.author,
            "category": skill.category,
            "tags": skill.tags,
            "versions": {
                ver: {
                    "version": v.version,
                    "description": v.description,
                    "friday_version": v.friday_version,
                    "download_url": v.download_url,
                    "changelog": v.changelog,
                    "release_date": v.release_date,
                }
                for ver, v in skill.versions.items()
            },
            "latest_version": skill.latest_version,
            "downloads": skill.downloads,
            "rating": skill.rating,
            "repo_url": skill.repo_url,
            "docs_url": skill.docs_url,
            "requires_skills": skill.requires_skills,
            "created_at": skill.created_at,
            "updated_at": skill.updated_at,
        }
    return registry_data
