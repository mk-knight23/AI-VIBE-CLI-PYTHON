"""
Comprehensive Test Suite for Friday Built-in Tools
Tests all tools with the MiniMax AI model.

To run: python tests/test_all_tools.py
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import Config
from tools.base import ToolInvocation

# Import all tools
from tools.builtin.read_file import ReadFileTool
from tools.builtin.write_file import WriteFileTool
from tools.builtin.edit_file import EditTool
from tools.builtin.list_dir import ListDirTool
from tools.builtin.glob import GlobTool
from tools.builtin.grep import GrepTool
from tools.builtin.shell import ShellTool
from tools.builtin.web_search import WebSearchTool
from tools.builtin.web_fetch import WebFetchTool
from tools.builtin.memory import MemoryTool
from tools.builtin.todo import TodosTool


class ToolTester:
    """Test runner for all Friday built-in tools"""
    
    def __init__(self):
        self.config = Config()
        self.test_dir = Path(__file__).parent / "test_workspace"
        self.results = []
        
    def setup(self):
        """Create test workspace and test files"""
        self.test_dir.mkdir(exist_ok=True)
        
        # Create sample test files
        (self.test_dir / "sample.txt").write_text(
            "Line 1: Hello World\n"
            "Line 2: This is a test file\n"
            "Line 3: Python is great\n"
            "Line 4: Testing tools\n"
            "Line 5: End of file\n"
        )
        
        (self.test_dir / "sample.py").write_text(
            "#!/usr/bin/env python3\n"
            "# Sample Python file\n"
            "\n"
            "def hello():\n"
            "    print('Hello World')\n"
            "\n"
            "def greet(name):\n"
            "    return f'Hello, {name}!'\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    hello()\n"
        )
        
        # Create subdirectory with files
        subdir = self.test_dir / "subdir"
        subdir.mkdir(exist_ok=True)
        (subdir / "nested.txt").write_text("Nested file content\n")
        (subdir / "data.json").write_text('{"key": "value", "number": 42}\n')
        
        print(f"✓ Created test workspace: {self.test_dir}")
        
    def cleanup(self):
        """Clean up test workspace"""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            print(f"✓ Cleaned up test workspace")
    
    def log_result(self, tool_name: str, test_name: str, success: bool, message: str):
        """Log test result"""
        status = "✓ PASS" if success else "✗ FAIL"
        self.results.append({
            "tool": tool_name,
            "test": test_name,
            "success": success,
            "message": message
        })
        print(f"  {status}: {test_name}")
        if not success:
            print(f"         → {message}")
    
    async def test_read_file(self):
        """Test ReadFileTool"""
        print("\n📖 Testing read_file tool...")
        tool = ReadFileTool(self.config)
        
        # Test 1: Read entire file
        invocation = ToolInvocation(
            params={"path": str(self.test_dir / "sample.txt")},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("read_file", "Read entire file", 
                       result.success and "Hello World" in result.output,
                       result.output[:100] if result.success else result.error)
        
        # Test 2: Read with offset and limit
        invocation = ToolInvocation(
            params={"path": str(self.test_dir / "sample.txt"), "offset": 2, "limit": 2},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("read_file", "Read with offset/limit",
                       result.success and "Line 2" in result.output,
                       result.output[:100] if result.success else result.error)
        
        # Test 3: Read non-existent file
        invocation = ToolInvocation(
            params={"path": "nonexistent.txt"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("read_file", "Handle missing file",
                       not result.success and "not found" in result.error.lower(),
                       result.error or "No error message")

        # Test 4: Read large file chunking (Simulated)
        large_path = self.test_dir / "large.txt"
        large_path.write_text("line\n" * 1000)
        invocation = ToolInvocation(
            params={"path": str(large_path), "offset": 500, "limit": 10},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("read_file", "Large file chunking",
                       result.success and "Showing lines 500-509" in result.output,
                       result.output[:100])

    async def test_write_file(self):
        """Test WriteFileTool"""
        print("\n✍️  Testing write_file tool...")
        tool = WriteFileTool(self.config)
        
        # Test 1: Write new file
        new_file = self.test_dir / "new_file.txt"
        invocation = ToolInvocation(
            params={
                "path": str(new_file),
                "content": "This is a new file\nWith multiple lines\n"
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("write_file", "Create new file",
                       result.success and new_file.exists(),
                       result.output if result.success else result.error)
        
        # Test 2: Overwrite existing file
        invocation = ToolInvocation(
            params={
                "path": str(new_file),
                "content": "Updated content\n"
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        content = new_file.read_text() if new_file.exists() else ""
        self.log_result("write_file", "Overwrite existing file",
                       result.success and "Updated" in content,
                       result.output if result.success else result.error)
        
        # Test 3: Create file with directories
        nested_file = self.test_dir / "new_dir" / "nested_new.txt"
        invocation = ToolInvocation(
            params={
                "path": str(nested_file),
                "content": "Nested content\n",
                "create_directories": True
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("write_file", "Create with parent directories",
                       result.success and nested_file.exists(),
                       result.output if result.success else result.error)

    async def test_edit_file(self):
        """Test EditTool"""
        print("\n✏️  Testing edit tool...")
        tool = EditTool(self.config)
        
        # Create a file to edit
        edit_file = self.test_dir / "edit_test.txt"
        edit_file.write_text("Hello World\nThis is original\nEnd\n")
        
        # Test 1: Simple replacement
        invocation = ToolInvocation(
            params={
                "path": str(edit_file),
                "old_string": "original",
                "new_string": "modified"
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        content = edit_file.read_text()
        self.log_result("edit", "Simple text replacement",
                       result.success and "modified" in content,
                       result.output if result.success else result.error)
        
        # Test 2: Create new file with empty old_string
        new_edit_file = self.test_dir / "edit_new.txt"
        invocation = ToolInvocation(
            params={
                "path": str(new_edit_file),
                "old_string": "",
                "new_string": "Created via edit\n"
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("edit", "Create new file",
                       result.success and new_edit_file.exists(),
                       result.output if result.success else result.error)
        
        # Test 3: Replace all occurrences
        multi_file = self.test_dir / "multi_replace.txt"
        multi_file.write_text("foo bar foo baz foo\n")
        invocation = ToolInvocation(
            params={
                "path": str(multi_file),
                "old_string": "foo",
                "new_string": "FOO",
                "replace_all": True
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        content = multi_file.read_text()
        self.log_result("edit", "Replace all occurrences",
                       result.success and content.count("FOO") == 3,
                       result.output if result.success else result.error)

        # Test 4: Surgical surgical edit on Python code
        invocation = ToolInvocation(
            params={
                "path": "sample.py",
                "old_string": "    print('Hello World')",
                "new_string": "    print('Hello expanded world')\n    print('Line 2')"
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        content = (self.test_dir / "sample.py").read_text()
        self.log_result("edit", "Surgical code edit with indentation",
                       result.success and "Hello expanded world" in content and "    print('Line 2')" in content,
                       result.output if result.success else result.error)

    async def test_list_dir(self):
        """Test ListDirTool"""
        print("\n📁 Testing list_dir tool...")
        tool = ListDirTool(self.config)
        
        # Test 1: List directory
        invocation = ToolInvocation(
            params={"path": "."},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("list_dir", "List directory contents",
                       result.success and "sample.txt" in result.output,
                       result.output[:200] if result.success else result.error)
        
        # Test 2: List with hidden files
        hidden_file = self.test_dir / ".hidden"
        hidden_file.write_text("hidden content\n")
        
        invocation = ToolInvocation(
            params={"path": ".", "include_hidden": True},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("list_dir", "Include hidden files",
                       result.success and ".hidden" in result.output,
                       result.output[:200] if result.success else result.error)
        
        # Test 3: List non-existent directory
        invocation = ToolInvocation(
            params={"path": "nonexistent_dir"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("list_dir", "Handle missing directory",
                       not result.success,
                       result.error or "No error")

    async def test_glob(self):
        """Test GlobTool"""
        print("\n🔍 Testing glob tool...")
        tool = GlobTool(self.config)
        
        # Test 1: Find Python files
        invocation = ToolInvocation(
            params={"pattern": "*.py", "path": "."},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("glob", "Find *.py files",
                       result.success and "sample.py" in result.output,
                       result.output if result.success else result.error)
        
        # Test 2: Recursive search
        invocation = ToolInvocation(
            params={"pattern": "**/*.txt", "path": "."},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("glob", "Recursive search **/*.txt",
                       result.success and "nested.txt" in result.output,
                       result.output if result.success else result.error)
        
        # Test 3: No matches
        invocation = ToolInvocation(
            params={"pattern": "*.xyz", "path": "."},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("glob", "Handle no matches",
                       result.success and result.output.strip() == "",
                       f"Output: '{result.output}'" if result.success else result.error)

    async def test_grep(self):
        """Test GrepTool"""
        print("\n🔎 Testing grep tool...")
        tool = GrepTool(self.config)
        
        # Test 1: Simple search
        invocation = ToolInvocation(
            params={"pattern": "Hello", "path": "."},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("grep", "Simple pattern search",
                       result.success and "Hello" in result.output,
                       result.output[:200] if result.success else result.error)
        
        # Test 2: Case insensitive search
        invocation = ToolInvocation(
            params={"pattern": "hello", "path": ".", "case_insensitive": True},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("grep", "Case insensitive search",
                       result.success and "Hello" in result.output,
                       result.output[:200] if result.success else result.error)
        
        # Test 3: Regex pattern
        invocation = ToolInvocation(
            params={"pattern": r"def \w+\(", "path": "sample.py"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("grep", "Regex pattern search",
                       result.success and ("def hello" in result.output or "def greet" in result.output),
                       result.output[:200] if result.success else result.error)
        
        # Test 4: No matches
        invocation = ToolInvocation(
            params={"pattern": "ZZZZNOTFOUND", "path": "."},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("grep", "Handle no matches",
                       result.success and "No matches" in result.output,
                       result.output if result.success else result.error)

    async def test_shell(self):
        """Test ShellTool"""
        print("\n💻 Testing shell tool...")
        tool = ShellTool(self.config)
        
        # Test 1: Simple command
        invocation = ToolInvocation(
            params={"command": "echo 'Hello from shell'"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("shell", "Simple echo command",
                       result.success and "Hello from shell" in result.output,
                       result.output if result.success else result.error)
        
        # Test 2: Command with output
        invocation = ToolInvocation(
            params={"command": "ls -la"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("shell", "ls command",
                       result.success and "sample" in result.output,
                       result.output[:200] if result.success else result.error)
        
        # Test 3: Command with custom cwd
        invocation = ToolInvocation(
            params={"command": "pwd", "cwd": "subdir"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("shell", "Command with custom cwd",
                       result.success and "subdir" in result.output,
                       result.output if result.success else result.error)
        
        # Test 4: Blocked dangerous command
        invocation = ToolInvocation(
            params={"command": "rm -rf /"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("shell", "Block dangerous command",
                       not result.success and "blocked" in result.error.lower(),
                       result.error or "No error")

        # Test 5: Command piping and redirection
        invocation = ToolInvocation(
            params={"command": "echo 'piped content' | grep piped"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("shell", "Command piping",
                       result.success and "piped content" in result.output,
                       result.output if result.success else result.error)

    async def test_web_search(self):
        """Test WebSearchTool"""
        print("\n🌐 Testing web_search tool...")
        tool = WebSearchTool(self.config)
        
        # Test 1: Basic search
        invocation = ToolInvocation(
            params={"query": "Python programming language", "max_results": 3},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("web_search", "Basic web search",
                       result.success and ("Python" in result.output or "results" in result.output.lower()),
                       result.output[:300] if result.success else result.error)

    async def test_web_fetch(self):
        """Test WebFetchTool"""
        print("\n📥 Testing web_fetch tool...")
        tool = WebFetchTool(self.config)
        
        # Test 1: Fetch a simple page
        invocation = ToolInvocation(
            params={"url": "https://httpbin.org/get", "timeout": 30},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("web_fetch", "Fetch URL content",
                       result.success and "headers" in result.output.lower(),
                       result.output[:300] if result.success else result.error)
        
        # Test 2: Invalid URL scheme
        invocation = ToolInvocation(
            params={"url": "ftp://invalid.scheme"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("web_fetch", "Reject invalid URL scheme",
                       not result.success,
                       result.error or "No error")

    async def test_memory(self):
        """Test MemoryTool"""
        print("\n🧠 Testing memory tool...")
        tool = MemoryTool(self.config)
        
        # Test 1: Set memory
        invocation = ToolInvocation(
            params={"action": "set", "key": "test_key", "value": "test_value_123"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("memory", "Set memory",
                       result.success and "test_key" in result.output,
                       result.output if result.success else result.error)
        
        # Test 2: Get memory
        invocation = ToolInvocation(
            params={"action": "get", "key": "test_key"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("memory", "Get memory",
                       result.success and "test_value_123" in result.output,
                       result.output if result.success else result.error)
        
        # Test 3: List memories
        invocation = ToolInvocation(
            params={"action": "list"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("memory", "List memories",
                       result.success and "test_key" in result.output,
                       result.output if result.success else result.error)
        
        # Test 4: Delete memory
        invocation = ToolInvocation(
            params={"action": "delete", "key": "test_key"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("memory", "Delete memory",
                       result.success and "Deleted" in result.output,
                       result.output if result.success else result.error)

    async def test_todos(self):
        """Test TodosTool"""
        print("\n📝 Testing todos tool...")
        tool = TodosTool(self.config)
        
        # Test 1: Add todo
        invocation = ToolInvocation(
            params={"action": "add", "content": "Test task 1"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        # Extract todo ID from response
        todo_id = None
        if result.success and "[" in result.output and "]" in result.output:
            start = result.output.index("[") + 1
            end = result.output.index("]")
            todo_id = result.output[start:end]
        self.log_result("todos", "Add todo",
                       result.success and "Added" in result.output,
                       result.output if result.success else result.error)
        
        # Test 2: List todos
        invocation = ToolInvocation(
            params={"action": "list"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("todos", "List todos",
                       result.success and "Test task 1" in result.output,
                       result.output if result.success else result.error)
        
        # Test 3: Complete todo
        if todo_id:
            invocation = ToolInvocation(
                params={"action": "complete", "id": todo_id},
                cwd=self.test_dir
            )
            result = await tool.execute(invocation)
            self.log_result("todos", "Complete todo",
                           result.success and "Completed" in result.output,
                           result.output if result.success else result.error)
        
        # Test 4: Clear todos
        # First add another todo
        await tool.execute(ToolInvocation(
            params={"action": "add", "content": "Another task"},
            cwd=self.test_dir
        ))
        invocation = ToolInvocation(
            params={"action": "clear"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("todos", "Clear todos",
                       result.success and "Cleared" in result.output,
                       result.output if result.success else result.error)

    async def run_all_tests(self):
        """Run all tool tests"""
        print("=" * 60)
        print("🚀 Friday Built-in Tools Test Suite")
        print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Model: {self.config.model_name}")
        print("=" * 60)
        
        self.setup()
        
        try:
            # Run all tests
            await self.test_read_file()
            await self.test_write_file()
            await self.test_edit_file()
            await self.test_list_dir()
            await self.test_glob()
            await self.test_grep()
            await self.test_shell()
            await self.test_web_search()
            await self.test_web_fetch()
            await self.test_memory()
            await self.test_todos()
        finally:
            self.cleanup()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r["success"])
        failed = sum(1 for r in self.results if not r["success"])
        total = len(self.results)
        
        # Group by tool
        tools = {}
        for r in self.results:
            if r["tool"] not in tools:
                tools[r["tool"]] = {"passed": 0, "failed": 0}
            if r["success"]:
                tools[r["tool"]]["passed"] += 1
            else:
                tools[r["tool"]]["failed"] += 1
        
        print(f"\n{'Tool':<15} {'Passed':<10} {'Failed':<10} {'Status'}")
        print("-" * 45)
        for tool, counts in tools.items():
            status = "✓" if counts["failed"] == 0 else "✗"
            print(f"{tool:<15} {counts['passed']:<10} {counts['failed']:<10} {status}")
        
        print("-" * 45)
        print(f"{'TOTAL':<15} {passed:<10} {failed:<10}")
        print(f"\nOverall: {passed}/{total} tests passed ({100*passed/total:.1f}%)")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for r in self.results:
                if not r["success"]:
                    print(f"  • {r['tool']}.{r['test']}: {r['message']}")
        else:
            print("\n✅ All tests passed!")
        
        print("=" * 60)
        
        return failed == 0


async def main():
    tester = ToolTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
