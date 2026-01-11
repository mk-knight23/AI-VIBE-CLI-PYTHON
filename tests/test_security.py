import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import Config
from tools.base import ToolInvocation
from tools.builtin.read_file import ReadFileTool
from tools.builtin.grep import GrepTool

async def test_secret_scrubbing():
    print("🛡️ Testing secret scrubbing...")
    config = Config()
    # Ensure exclude_patterns contains SECRET
    if "*SECRET*" not in config.shell_environment.exclude_patterns:
        config.shell_environment.exclude_patterns.append("*SECRET*")
    
    test_dir = Path(__file__).parent / "security_test_workspace"
    test_dir.mkdir(exist_ok=True)
    
    secret_file = test_dir / "secrets.txt"
    secret_file.write_text("My API_KEY is sk-123456789\nMy PASSWORD is supersecret\nThis is a SECRET message.")
    
    read_tool = ReadFileTool(config)
    grep_tool = GrepTool(config)
    
    # Test read_file scrubbing
    print("  Testing read_file scrubbing...")
    invocation = ToolInvocation(params={"path": str(secret_file)}, cwd=test_dir)
    result = await read_tool.execute(invocation)
    
    if "[REDACTED]" in result.output and "SECRET" not in result.output:
        print("  ✓ PASS: read_file scrubbed successfully")
    else:
        print("  ✗ FAIL: read_file failed to scrub")
        print(f"    Output: {result.output}")

    # Test grep scrubbing
    print("  Testing grep scrubbing...")
    invocation = ToolInvocation(params={"pattern": "SECRET", "path": str(secret_file)}, cwd=test_dir)
    result = await grep_tool.execute(invocation)
    
    if "[REDACTED]" in result.output and "SECRET" not in result.output:
        print("  ✓ PASS: grep scrubbed successfully")
    else:
        print("  ✗ FAIL: grep failed to scrub")
        print(f"    Output: {result.output}")

    # Cleanup
    import shutil
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    asyncio.run(test_secret_scrubbing())
