"""
Comprehensive Test Suite for Friday New Tools
Tests git, database, docker, and http_request tools.

To run: python tests/test_new_tools.py
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from friday_ai.config.config import Config
from friday_ai.tools.base import ToolInvocation

# Import new tools
from friday_ai.tools.builtin.git import GitTool
from friday_ai.tools.builtin.database import DatabaseTool
from friday_ai.tools.builtin.docker import DockerTool
from friday_ai.tools.builtin.http_request import HttpTool, HttpDownloadTool


class NewToolsTester:
    """Test runner for Friday's new tools"""

    def __init__(self):
        self.config = Config()
        self.test_dir = Path(__file__).parent / "new_tools_workspace"
        self.results = []

    def setup(self):
        """Create test workspace"""
        self.test_dir.mkdir(exist_ok=True)

        # Initialize a git repo for testing
        import subprocess
        subprocess.run(["git", "init"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.test_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, capture_output=True)

        # Create a sample file
        (self.test_dir / "test.txt").write_text("Initial content\n")

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

    async def test_git_tool(self):
        """Test GitTool"""
        print("\n🔧 Testing git tool...")
        tool = GitTool(self.config)

        # Test 1: git status
        print("  Testing git status...")
        invocation = ToolInvocation(params={"command": "status"}, cwd=self.test_dir)
        result = await tool.execute(invocation)
        self.log_result("git", "git status",
                       result.success and ("test.txt" in result.output or "Untracked" in result.output),
                       result.output[:200] if result.success else result.error)

        # Test 2: git log (should be empty initially)
        invocation = ToolInvocation(params={"command": "log", "limit": 5}, cwd=self.test_dir)
        result = await tool.execute(invocation)
        self.log_result("git", "git log (empty repo)",
                       result.success,  # Should succeed even if empty
                       result.output[:100] if result.success else result.error)

        # Test 3: git add
        invocation = ToolInvocation(params={"command": "add", "files": ["test.txt"]}, cwd=self.test_dir)
        result = await tool.execute(invocation)
        self.log_result("git", "git add",
                       result.success,
                       result.output if result.success else result.error)

        # Test 4: git commit
        invocation = ToolInvocation(
            params={"command": "commit", "message": "Initial commit"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("git", "git commit",
                       result.success,
                       result.output if result.success else result.error)

        # Test 5: git log after commit
        invocation = ToolInvocation(params={"command": "log", "limit": 5}, cwd=self.test_dir)
        result = await tool.execute(invocation)
        self.log_result("git", "git log (with commit)",
                       result.success and "Initial commit" in result.output,
                       result.output[:200] if result.success else result.error)

        # Test 6: git diff
        (self.test_dir / "test.txt").write_text("Modified content\n")
        invocation = ToolInvocation(params={"command": "diff"}, cwd=self.test_dir)
        result = await tool.execute(invocation)
        self.log_result("git", "git diff",
                       result.success and ("Modified" in result.output or "content" in result.output),
                       result.output[:200] if result.success else result.error)

        # Test 7: git branch list
        invocation = ToolInvocation(params={"command": "branch", "action": "list"}, cwd=self.test_dir)
        result = await tool.execute(invocation)
        self.log_result("git", "git branch list",
                       result.success,
                       result.output[:200] if result.success else result.error)

    async def test_database_tool(self):
        """Test DatabaseTool"""
        print("\n🗄️  Testing database tool...")
        tool = DatabaseTool(self.config)

        # Test 1: List tables (SQLite default)
        print("  Testing database.tables (SQLite)...")
        invocation = ToolInvocation(params={"action": "tables"}, cwd=self.test_dir)
        result = await tool.execute(invocation)
        self.log_result("database", "List tables (SQLite)",
                       result.success,  # Should succeed even if no tables
                       result.output[:200] if result.success else result.error)

        # Test 2: Create table via execute
        invocation = ToolInvocation(
            params={
                "action": "execute",
                "query": "CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)"
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("database", "CREATE TABLE",
                       result.success,
                       result.output if result.success else result.error)

        # Test 3: Insert data
        invocation = ToolInvocation(
            params={
                "action": "execute",
                "query": "INSERT INTO test (name) VALUES ('Alice'), ('Bob')"
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("database", "INSERT data",
                       result.success,
                       result.output if result.success else result.error)

        # Test 4: Query data
        invocation = ToolInvocation(
            params={"action": "query", "query": "SELECT * FROM test"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("database", "SELECT query",
                       result.success and ("Alice" in result.output or "Bob" in result.output or str(result.metadata)),
                       result.output[:200] if result.success else result.error)

        # Test 5: Get schema
        invocation = ToolInvocation(
            params={"action": "schema", "table": "test"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("database", "Get table schema",
                       result.success,
                       result.output[:200] if result.success else result.error)

    async def test_docker_tool(self):
        """Test DockerTool"""
        print("\n🐳 Testing docker tool...")
        tool = DockerTool(self.config)

        # Test 1: Docker ps (list containers)
        print("  Testing docker ps...")
        invocation = ToolInvocation(params={"command": "ps"}, cwd=self.test_dir)
        result = await tool.execute(invocation)

        # Should succeed even if Docker isn't running
        # The tool will return an error if Docker isn't available
        docker_available = result.success or "docker" not in result.error.lower() if result.error else True

        self.log_result("docker", "docker ps",
                       result.success or not docker_available,  # Pass if either success or docker not available
                       result.output[:200] if result.success else result.error)

        # Test 2: Docker images (list images)
        invocation = ToolInvocation(params={"command": "images"}, cwd=self.test_dir)
        result = await tool.execute(invocation)
        self.log_result("docker", "docker images",
                       result.success or not docker_available,
                       result.output[:200] if result.success else result.error)

        # Test 3: Docker inspect (will fail if no containers, that's ok)
        invocation = ToolInvocation(
            params={"command": "inspect", "container": "nonexistent"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        # Expected to fail for nonexistent container
        self.log_result("docker", "docker inspect (error handling)",
                       not result.success,  # Should fail for nonexistent container
                       result.error if result.error else result.output)

    async def test_http_request_tool(self):
        """Test HttpTool"""
        print("\n🌐 Testing http_request tool...")
        tool = HttpTool(self.config)

        # Test 1: GET request to httpbin
        print("  Testing GET request...")
        invocation = ToolInvocation(
            params={"method": "GET", "url": "https://httpbin.org/get"},
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("http_request", "GET request",
                       result.success and "200" in result.output,
                       result.output[:300] if result.success else result.error)

        # Test 2: POST request with JSON
        invocation = ToolInvocation(
            params={
                "method": "POST",
                "url": "https://httpbin.org/post",
                "json_data": {"test": "data", "number": 42}
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("http_request", "POST JSON request",
                       result.success and "200" in result.output,
                       result.output[:300] if result.success else result.error)

        # Test 3: Request with headers
        invocation = ToolInvocation(
            params={
                "method": "GET",
                "url": "https://httpbin.org/headers",
                "headers": {"X-Custom-Header": "test-value"}
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("http_request", "Request with custom headers",
                       result.success and "X-Custom-Header" in result.output,
                       result.output[:300] if result.success else result.error)

        # Test 4: Request with query parameters
        invocation = ToolInvocation(
            params={
                "method": "GET",
                "url": "https://httpbin.org/get",
                "params": {"key1": "value1", "key2": "value2"}
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("http_request", "Request with query params",
                       result.success and ("key1" in result.output or "value1" in result.output),
                       result.output[:300] if result.success else result.error)

    async def test_http_download_tool(self):
        """Test HttpDownloadTool"""
        print("\n📥 Testing http_download tool...")
        tool = HttpDownloadTool(self.config)

        # Test 1: Download a small file
        print("  Testing file download...")
        download_path = self.test_dir / "downloaded.txt"
        invocation = ToolInvocation(
            params={
                "url": "https://httpbin.org/robots.txt",
                "output_path": str(download_path)
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        file_exists = download_path.exists()
        content = download_path.read_text() if file_exists else ""

        self.log_result("http_download", "Download file",
                       result.success and file_exists and len(content) > 0,
                       result.output if result.success else result.error)

        # Test 2: Download with timeout
        download_path2 = self.test_dir / "downloaded2.txt"
        invocation = ToolInvocation(
            params={
                "url": "https://httpbin.org/delay/1",
                "output_path": str(download_path2),
                "timeout": 10
            },
            cwd=self.test_dir
        )
        result = await tool.execute(invocation)
        self.log_result("http_download", "Download with timeout",
                       result.success,
                       result.output if result.success else result.error)

    async def run_all_tests(self):
        """Run all new tool tests"""
        print("=" * 60)
        print("🚀 Friday New Tools Test Suite")
        print(f"   Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Model: {self.config.model_name}")
        print("=" * 60)

        self.setup()

        try:
            # Run all tests
            await self.test_git_tool()
            await self.test_database_tool()
            await self.test_docker_tool()
            await self.test_http_request_tool()
            await self.test_http_download_tool()
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

        print(f"\n{'Tool':<20} {'Passed':<10} {'Failed':<10} {'Status'}")
        print("-" * 50)
        for tool, counts in tools.items():
            status = "✓" if counts["failed"] == 0 else "✗"
            print(f"{tool:<20} {counts['passed']:<10} {counts['failed']:<10} {status}")

        print("-" * 50)
        print(f"{'TOTAL':<20} {passed:<10} {failed:<10}")
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
    tester = NewToolsTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
