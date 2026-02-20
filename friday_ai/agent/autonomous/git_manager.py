import subprocess
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class GitManager:
    """Manages Git operations for the autonomous loop."""
    
    def __init__(self, cwd: Path):
        self.cwd = cwd

    def is_git_repo(self) -> bool:
        """Checks if the current directory is a Git repository."""
        return (self.cwd / ".git").exists()

    def get_changed_files(self) -> List[str]:
        """Returns a list of staged and unstaged changes."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return [line[3:].strip() for line in result.stdout.splitlines() if line.strip()]
        except Exception as e:
            logger.error(f"Failed to get git status: {e}")
            return []

    def commit_changes(self, message: str) -> bool:
        """Stages all changes and creates a commit."""
        try:
            # Stage all
            subprocess.run(["git", "add", "."], cwd=self.cwd, check=True)
            # Commit
            subprocess.run(["git", "commit", "-m", message], cwd=self.cwd, check=True)
            logger.info(f"Committed changes with message: {message}")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during git commit: {e}")
            return False

    def auto_commit_iteration(self, loop_number: int, summary: str = "") -> bool:
        """Performs an automatic commit for a loop iteration."""
        if not self.is_git_repo():
            return False
        
        changed = self.get_changed_files()
        if not changed:
            return False
            
        msg = f"chore(autonomous): iteration {loop_number}\n\n{summary}" if summary else f"chore(autonomous): iteration {loop_number}"
        return self.commit_changes(msg)
