import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class QualityManager:
    """Manages code quality and self-healing in the autonomous loop."""
    
    def __init__(self, cwd: Path):
        self.cwd = cwd

    def run_tests(self) -> Dict[str, Any]:
        """Attempts to run tests and returns the result."""
        # Common test commands
        commands = [
            ["pytest", "-v"],
            ["python", "-m", "pytest"],
            ["npm", "test"],
            ["npm", "run", "test"]
        ]
        
        for cmd in commands:
            try:
                # Check if executable exists or command is valid
                result = subprocess.run(
                    cmd,
                    cwd=self.cwd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    return {"success": True, "output": result.stdout, "command": " ".join(cmd)}
                else:
                    return {
                        "success": False, 
                        "output": result.stdout, 
                        "error": result.stderr,
                        "command": " ".join(cmd)
                    }
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
                
        return {"success": False, "error": "No valid test runner found or tests failed to start."}

    def detect_failure_patterns(self, output: str) -> Optional[str]:
        """Analyzes test output for common failure patterns."""
        if "AssertionError" in output:
            return "Assertion failure detected. Check logic vs expected values."
        if "ModuleNotFoundError" in output or "ImportError" in output:
            return "Missing dependency or incorrect import path."
        if "SyntaxError" in output:
            return "Syntax error in code."
        if "TypeError" in output:
            return "Type mismatch or incorrect argument usage."
        return None

    def get_self_healing_prompt(self, test_result: Dict[str, Any]) -> str:
        """Generates a prompt for the agent to fix a detected failure."""
        failure_type = self.detect_failure_patterns(test_result.get("output", "") + test_result.get("error", ""))
        
        prompt = f"\n\n--- SELF-HEALING NOTICE ---\n"
        prompt += f"The latest test run FAILED using command: `{test_result.get('command')}`\n"
        if failure_type:
            prompt += f"Detected Pattern: {failure_type}\n"
        prompt += f"\nRelevant Output:\n{test_result.get('output', '')[-1000:]}\n"
        prompt += f"\nFIX the errors before proceeding."
        return prompt
