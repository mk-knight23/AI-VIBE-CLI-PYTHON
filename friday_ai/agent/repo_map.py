import os
import ast
from pathlib import Path
from typing import Dict, List, Optional

class RepoMap:
    """Generates a compressed map of the repository structure."""
    
    def __init__(self, root_dir: Path, exclude_patterns: List[str] = None):
        self.root_dir = root_dir
        self.exclude_patterns = exclude_patterns or [".git", "__pycache__", "node_modules", "venv", ".ai-agent"]

    def should_exclude(self, path: Path) -> bool:
        for pattern in self.exclude_patterns:
            if pattern in path.parts:
                return True
        return False

    def scan_python_file(self, file_path: Path) -> str:
        """Extracts classes and functions from a Python file using AST."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            items = []
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    items.append(f"class {node.name}({', '.join(methods)})")
                elif isinstance(node, ast.FunctionDef):
                    items.append(f"def {node.name}()")
            return ", ".join(items) if items else ""
        except Exception:
            return ""

    def generate_map(self) -> str:
        """Generates a string representation of the repo map."""
        lines = []
        for root, dirs, files in os.walk(self.root_dir):
            root_path = Path(root)
            if self.should_exclude(root_path):
                dirs[:] = []  # Don't descend into excluded dirs
                continue

            rel_path = root_path.relative_to(self.root_dir)
            if rel_path == Path("."):
                depth = 0
            else:
                depth = len(rel_path.parts)
            
            indent = "  " * depth
            if rel_path != Path("."):
                lines.append(f"{indent}📁 {rel_path.name}/")
            
            for file in files:
                file_path = root_path / file
                if self.should_exclude(file_path):
                    continue
                
                file_info = ""
                if file.endswith(".py"):
                    file_info = f" # {self.scan_python_file(file_path)}"
                
                lines.append(f"{indent}  📄 {file}{file_info}")
                
        return "\n".join(lines)

def get_repo_map(root_dir: Path) -> str:
    mapper = RepoMap(root_dir)
    return mapper.generate_map()
