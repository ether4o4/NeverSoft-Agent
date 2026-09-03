"""Built-in tools for the NeverSoft Agent.

Tools are deliberately workspace-scoped so the agent can work on a project
without silently gaining unrestricted access to the host filesystem.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

TOOLS: dict[str, Callable] = {}
WORKSPACE = Path(os.getenv("NEVERSOFT_WORKSPACE", "./workspace")).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)


class ToolError(RuntimeError):
    """Raised when a tool request is invalid or outside its allowed scope."""


def tool(name: str):
    def register(fn: Callable):
        TOOLS[name] = fn
        return fn
    return register


def _path(relative: str) -> Path:
    target = (WORKSPACE / relative).resolve()
    if target != WORKSPACE and WORKSPACE not in target.parents:
        raise ToolError("Path is outside the agent workspace")
    return target


@tool("list_files")
def list_files(path: str = ".") -> dict:
    """List files and directories inside the agent workspace."""
    target = _path(path)
    if not target.exists():
        raise ToolError(f"Path does not exist: {path}")
    if not target.is_dir():
        raise ToolError(f"Not a directory: {path}")
    items = []
    for item in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        items.append({"name": item.name, "type": "directory" if item.is_dir() else "file"})
    return {"workspace": str(WORKSPACE), "path": path, "items": items}


@tool("read_file")
def read_file(path: str) -> dict:
    """Read a UTF-8 text file from the agent workspace."""
    target = _path(path)
    if not target.is_file():
        raise ToolError(f"Not a file: {path}")
    text = target.read_text(encoding="utf-8")
    return {"path": path, "content": text[:200_000], "truncated": len(text) > 200_000}


@tool("write_file")
def write_file(path: str, content: str) -> dict:
    """Create or replace a UTF-8 text file inside the agent workspace."""
    target = _path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": path, "bytes": target.stat().st_size, "written": True}


@tool("make_directory")
def make_directory(path: str) -> dict:
    """Create a directory inside the agent workspace."""
    target = _path(path)
    target.mkdir(parents=True, exist_ok=True)
    return {"path": path, "created": True}


@tool("run_shell")
def run_shell(command: str, timeout: int = 30) -> dict:
    """Run a shell command with the agent workspace as its working directory."""
    if not command.strip():
        raise ToolError("Command is empty")
    timeout = max(1, min(int(timeout), 120))
    result = subprocess.run(
        command,
        shell=True,
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, "NEVERSOFT_WORKSPACE": str(WORKSPACE)},
    )
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout[-50_000:],
        "stderr": result.stderr[-20_000:],
    }
