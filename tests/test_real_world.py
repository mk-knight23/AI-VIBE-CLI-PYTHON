"""
Real-World Scenario Tests for Friday Tools
Tests multi-tool integration workflows mimicking developer tasks.
"""

import asyncio
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import Config
from tools.base import ToolInvocation

# Import tools
from tools.builtin.read_file import ReadFileTool
from tools.builtin.write_file import WriteFileTool
from tools.builtin.edit_file import EditTool
from tools.builtin.list_dir import ListDirTool
from tools.builtin.glob import GlobTool
from tools.builtin.grep import GrepTool
from tools.builtin.shell import ShellTool
from tools.builtin.memory import MemoryTool
from tools.builtin.todo import TodosTool


class RealWorldTester:
    def __init__(self):
        self.config = Config()
        self.test_dir = Path(__file__).parent / "real_world_workspace"
        self.results = []

    def setup(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir(exist_ok=True)
        
        # Create a mock project structure
        src = self.test_dir / "src"
        src.mkdir()
        (src / "app.py").write_text("def run():\n    print('app running')\n    # BUG: division by zero below\n    res = 1/0\n")
        (src / "utils.py").write_text("def helper():\n    return True\n")
        
        logs = self.test_dir / "logs"
        logs.mkdir()
        (logs / "error.log").write_text("2024-01-01 10:00:00 INFO Initializing\n2024-01-01 10:05:00 ERROR ZeroDivisionError in app.py:4\n2024-01-01 10:10:00 WARN Retrying\n")

        print(f"✓ Created real-world workspace: {self.test_dir}")

    def cleanup(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        print("✓ Cleaned up real-world workspace")

    def log_result(self, scenario: str, success: bool, message: str):
        status = "✓ PASS" if success else "✗ FAIL"
        self.results.append({"scenario": scenario, "success": success, "message": message})
        print(f"  {status}: {scenario}")

    async def scenario_bug_fix(self):
        """Scenario: Find a bug via grep, read it, fix it via edit, and verify."""
        print("\n🐞 Scenario: Bug Investigation and Fix Workflow")
        
        glob_tool = GlobTool(self.config)
        grep_tool = GrepTool(self.config)
        read_tool = ReadFileTool(self.config)
        edit_tool = EditTool(self.config)
        shell_tool = ShellTool(self.config)

        # 1. Search for files
        res = await glob_tool.execute(ToolInvocation(params={"pattern": "src/*.py"}, cwd=self.test_dir))
        if "app.py" not in res.output:
            return self.log_result("Bug Fix", False, "Could not find app.py")

        # 2. Grep for BUG
        res = await grep_tool.execute(ToolInvocation(params={"pattern": "BUG", "path": "src"}, cwd=self.test_dir))
        if "division by zero" not in res.output:
            return self.log_result("Bug Fix", False, "Could not find BUG comment")

        # 3. Read the file
        res = await read_tool.execute(ToolInvocation(params={"path": "src/app.py"}, cwd=self.test_dir))
        if "1/0" not in res.output:
            return self.log_result("Bug Fix", False, "Could not read buggy line")

        # 4. Fix the bug
        res = await edit_tool.execute(ToolInvocation(params={
            "path": "src/app.py",
            "old_string": "res = 1/0",
            "new_string": "try:\n        res = 1/0\n    except ZeroDivisionError:\n        res = 0"
        }, cwd=self.test_dir))
        if not res.success:
            return self.log_result("Bug Fix", False, f"Edit failed: {res.error}")

        # 5. Verify via shell (syntax check)
        res = await shell_tool.execute(ToolInvocation(params={"command": "python3 -m py_compile src/app.py"}, cwd=self.test_dir))
        self.log_result("Bug Fix", res.success, res.output if res.success else res.error)

    async def scenario_log_analysis(self):
        """Scenario: Read logs, extract error signature, and remember it."""
        print("\n📋 Scenario: Log Analysis and Memory Workflow")
        
        read_tool = ReadFileTool(self.config)
        mem_tool = MemoryTool(self.config)
        todo_tool = TodosTool(self.config)

        # 1. Add todo
        await todo_tool.execute(ToolInvocation(params={"action": "add", "content": "Analyze logs"}, cwd=self.test_dir))

        # 2. Read logs
        res = await read_tool.execute(ToolInvocation(params={"path": "logs/error.log"}, cwd=self.test_dir))
        error_line = [l for l in res.output.split('\n') if "ERROR" in l][0]

        # 3. Save to memory
        res = await mem_tool.execute(ToolInvocation(params={
            "action": "set",
            "key": "last_error",
            "value": error_line
        }, cwd=self.test_dir))

        # 4. Check memory
        res = await mem_tool.execute(ToolInvocation(params={"action": "get", "key": "last_error"}, cwd=self.test_dir))
        self.log_result("Log Analysis", "ZeroDivisionError" in res.output, res.output)

    async def run_all(self):
        print("=" * 60)
        print("🚀 Friday Real-World Integration Tests")
        print("=" * 60)
        self.setup()
        try:
            await self.scenario_bug_fix()
            await self.scenario_log_analysis()
        finally:
            self.cleanup()
        
        print("\n" + "=" * 60)
        passed = sum(1 for r in self.results if r["success"])
        print(f"Summary: {passed}/{len(self.results)} scenarios passed")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(RealWorldTester().run_all())
