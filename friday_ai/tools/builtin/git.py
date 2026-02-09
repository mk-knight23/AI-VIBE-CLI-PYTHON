import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal

from friday_ai.tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult


class GitStatusParams(BaseModel):
    cwd: str | None = Field(None, description="Working directory for git command")


class GitLogParams(BaseModel):
    limit: int = Field(10, ge=1, le=100, description="Number of commits to show")
    cwd: str | None = Field(None, description="Working directory for git command")


class GitDiffParams(BaseModel):
    target: str = Field("HEAD", description="What to diff (commit, branch, file, or HEAD)")
    cwd: str | None = Field(None, description="Working directory for git command")


class GitCommitParams(BaseModel):
    message: str = Field(..., description="Commit message")
    files: list[str] | None = Field(None, description="Specific files to commit (None = all staged)")
    cwd: str | None = Field(None, description="Working directory for git command")


class GitBranchParams(BaseModel):
    action: Literal["list", "create", "delete", "switch"] = Field("list", description="Branch action")
    name: str | None = Field(None, description="Branch name (for create/delete/switch)")
    cwd: str | None = Field(None, description="Working directory for git command")


class GitAddParams(BaseModel):
    files: list[str] = Field(..., description="Files to stage")
    cwd: str | None = Field(None, description="Working directory for git command")


class GitCloneParams(BaseModel):
    url: str = Field(..., description="Repository URL to clone")
    directory: str | None = Field(None, description="Directory name (optional)")
    cwd: str | None = Field(None, description="Working directory for git command")


class GitTool(Tool):
    name = "git"
    kind = ToolKind.SHELL
    description = """Execute git commands for version control operations.

Supports: status, log, diff, add, commit, branch, clone

Examples:
- git status
- git log (shows last 10 commits)
- git diff HEAD
- git add ["file1.py", "file2.py"]
- git commit with message="Fix bug"
- git branch action="list"
- git clone url="https://github.com/user/repo.git"
"""

    schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": ["status", "log", "diff", "add", "commit", "branch", "clone"],
                "description": "Git command to execute"
            },
            "cwd": {"type": "string", "description": "Working directory"},
            "limit": {"type": "integer", "description": "For log: number of commits"},
            "target": {"type": "string", "description": "For diff: commit/branch/file to diff"},
            "message": {"type": "string", "description": "For commit: commit message"},
            "files": {"type": "array", "items": {"type": "string"}, "description": "For add/commit: files to stage/commit"},
            "action": {"type": "string", "enum": ["list", "create", "delete", "switch"], "description": "For branch: action to perform"},
            "name": {"type": "string", "description": "For branch: branch name"},
            "url": {"type": "string", "description": "For clone: repository URL"},
            "directory": {"type": "string", "description": "For clone: target directory name"}
        },
        "required": ["command"]
    }

    async def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        command = invocation.params.get("command", "")

        # Mutating commands need confirmation
        if command in ["commit", "add", "branch", "clone"]:
            return ToolConfirmation(
                tool_name=self.name,
                params=invocation.params,
                description=f"Git {command}",
                is_dangerous=command in ["commit", "branch"],
            )
        return None

    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        command = invocation.params.get("command", "")

        # Resolve working directory
        cwd = invocation.params.get("cwd")
        if cwd:
            working_dir = Path(cwd)
            if not working_dir.is_absolute():
                working_dir = invocation.cwd / working_dir
        else:
            working_dir = invocation.cwd

        # Build git command based on subcommand
        if command == "status":
            return await self._run_git(["status", "-sb"], working_dir)

        elif command == "log":
            limit = invocation.params.get("limit", 10)
            return await self._run_git(
                ["log", f"--max-count={limit}", "--oneline", "--decorate", "--graph"],
                working_dir
            )

        elif command == "diff":
            target = invocation.params.get("target", "HEAD")
            return await self._run_git(["diff", target], working_dir)

        elif command == "add":
            files = invocation.params.get("files", ["."])
            if isinstance(files, str):
                files = [files]
            return await self._run_git(["add"] + files, working_dir)

        elif command == "commit":
            message = invocation.params.get("message", "")
            if not message:
                return ToolResult.error_result("Commit message is required")

            files = invocation.params.get("files")
            if files:
                # Stage specific files first
                if isinstance(files, str):
                    files = [files]
                await self._run_git(["add"] + files, working_dir)

            return await self._run_git(["commit", "-m", message], working_dir)

        elif command == "branch":
            action = invocation.params.get("action", "list")
            name = invocation.params.get("name")

            if action == "list":
                return await self._run_git(["branch", "-a", "-v"], working_dir)
            elif action == "create":
                if not name:
                    return ToolResult.error_result("Branch name is required for create")
                return await self._run_git(["branch", name], working_dir)
            elif action == "delete":
                if not name:
                    return ToolResult.error_result("Branch name is required for delete")
                return await self._run_git(["branch", "-d", name], working_dir)
            elif action == "switch":
                if not name:
                    return ToolResult.error_result("Branch name is required for switch")
                return await self._run_git(["switch", name], working_dir)
            else:
                return ToolResult.error_result(f"Unknown branch action: {action}")

        elif command == "clone":
            url = invocation.params.get("url")
            if not url:
                return ToolResult.error_result("Repository URL is required for clone")

            directory = invocation.params.get("directory")
            cmd = ["clone", url]
            if directory:
                cmd.append(directory)

            return await self._run_git(cmd, working_dir)

        else:
            return ToolResult.error_result(f"Unknown git command: {command}")

    async def _run_git(self, args: list[str], cwd: Path) -> ToolResult:
        """Execute git command with given arguments."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            stdout_data, stderr_data = await asyncio.wait_for(
                process.communicate(),
                timeout=60,
            )

            stdout = stdout_data.decode("utf-8", errors="replace")
            stderr = stderr_data.decode("utf-8", errors="replace")

            output = stdout
            if stderr:
                if output:
                    output += "\n"
                output += stderr

            success = process.returncode == 0

            # Truncate very long output
            if len(output) > 50 * 1024:
                output = output[:50 * 1024] + "\n... [output truncated]"

            return ToolResult(
                success=success,
                output=output.strip() if output else "(no output)",
                error=stderr if not success else None,
                exit_code=process.returncode,
            )

        except asyncio.TimeoutError:
            return ToolResult.error_result("Git command timed out after 60s")
        except FileNotFoundError:
            return ToolResult.error_result("Git is not installed or not found in PATH")
        except Exception as e:
            return ToolResult.error_result(f"Git command failed: {e}")
