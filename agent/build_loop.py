"""Build Completion Loop: inspect, implement, audit, build, verify, recover."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class BuildState:
    goal: str
    phase: str = "received"
    iteration: int = 0
    max_iterations: int = 12
    commands: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    verified: bool = False


class BuildCompletionLoop:
    """Own a build from request through verified artifact, retrying failures."""

    def __init__(self, workspace: str | Path, llm: Callable[[str], str], max_iterations: int = 12):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.llm = llm
        self.max_iterations = max_iterations
        self.state_file = self.workspace / ".neversoft-build-state.json"

    def save(self, state: BuildState) -> None:
        self.state_file.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")

    def inspect(self) -> dict[str, Any]:
        files = []
        for path in self.workspace.rglob("*"):
            if ".git" in path.parts or path.name == ".neversoft-build-state.json":
                continue
            if path.is_file():
                files.append(str(path.relative_to(self.workspace)))
        return {
            "files": sorted(files)[:2000],
            "has_gradle": any((self.workspace / name).exists() for name in ("gradlew", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts")),
            "has_android": (self.workspace / "app" / "src" / "main" / "AndroidManifest.xml").exists(),
            "has_package_json": (self.workspace / "package.json").exists(),
            "has_pyproject": (self.workspace / "pyproject.toml").exists(),
        }

    def choose_build_commands(self, info: dict[str, Any]) -> list[str]:
        if info["has_gradle"] and info["has_android"]:
            if (self.workspace / "gradlew").exists():
                wrapper = "./gradlew" if os.name != "nt" else "gradlew.bat"
                return [f"{wrapper} assembleDebug", f"{wrapper} test"]
            return ["gradle assembleDebug", "gradle test"]
        if info["has_package_json"]:
            return ["npm test", "npm run build"]
        if info["has_pyproject"]:
            return ["python -m pytest", "python -m build"]
        return ["python -m compileall ."]

    def run_command(self, command: str, timeout: int = 900) -> dict[str, Any]:
        try:
            result = subprocess.run(command, shell=True, cwd=self.workspace, capture_output=True, text=True, timeout=timeout, env={**os.environ, "NEVERSOFT_WORKSPACE": str(self.workspace)})
            return {"command": command, "returncode": result.returncode, "stdout": result.stdout[-30000:], "stderr": result.stderr[-30000:]}
        except subprocess.TimeoutExpired as exc:
            return {"command": command, "returncode": 124, "stdout": str(exc.stdout or ""), "stderr": "Command timed out"}

    def artifacts(self) -> list[str]:
        found: set[str] = set()
        for pattern in ("*.apk", "*.aab", "*.ipa"):
            for path in self.workspace.rglob(pattern):
                if path.is_file() and ".git" not in path.parts:
                    found.add(str(path.relative_to(self.workspace)))
        for directory in ("dist", "build/libs"):
            root = self.workspace / directory
            if root.exists():
                for path in root.rglob("*"):
                    if path.is_file():
                        found.add(str(path.relative_to(self.workspace)))
        return sorted(found)

    def audit_prompt(self, goal: str, info: dict[str, Any], outputs: list[dict[str, Any]]) -> str:
        return (
            "You are the final implementation auditor for an autonomous build.\n"
            "Goal: " + goal + "\n"
            "Project inspection: " + json.dumps(info) + "\n"
            "Recent build outputs: " + json.dumps(outputs) + "\n"
            "Find concrete missing requirements, bugs, edge cases, or required implementation work. "
            "If changes are needed, return concise actionable instructions. If complete, return COMPLETE."
        )

    def run(self, goal: str, implement: Callable[[str], str] | None = None) -> BuildState:
        state = BuildState(goal=goal, max_iterations=self.max_iterations)
        self.save(state)
        for iteration in range(1, self.max_iterations + 1):
            state.iteration = iteration
            state.phase = "inspect"
            self.save(state)
            info = self.inspect()
            state.phase = "implement"
            instruction = f"Build completion request: {goal}\nProject state: {json.dumps(info)}\nImplement everything required for a genuinely finished build. Do not merely describe changes; make them. Include necessary error handling, state, navigation, validation, loading/empty states, accessibility, platform requirements, edge cases, and 2-3 useful luxury improvements."
            if implement:
                implement(instruction)
            state.phase = "build"
            outputs: list[dict[str, Any]] = []
            failed = False
            for command in self.choose_build_commands(self.inspect()):
                state.commands.append(command)
                result = self.run_command(command)
                outputs.append(result)
                if result["returncode"] != 0:
                    failed = True
                    state.failures.append(result["stderr"] or result["stdout"] or "Build command failed")
                    state.phase = "recover"
                    if implement:
                        implement("Fix this build/test failure and make the project build again.\n" + json.dumps(result))
                    break
            if failed:
                self.save(state)
                continue
            state.phase = "audit"
            audit = self.llm(self.audit_prompt(goal, self.inspect(), outputs)).strip()
            if not audit.upper().startswith("COMPLETE"):
                if implement:
                    implement(audit)
                self.save(state)
                continue
            found = self.artifacts()
            state.artifacts = found
            state.verified = bool(found) if self.inspect()["has_android"] else True
            if state.verified:
                state.phase = "complete"
                self.save(state)
                return state
            state.phase = "recover"
            state.failures.append("Build completed but the required artifact was not found.")
            if implement:
                implement("The build completed but the required artifact was not found. Inspect the project, produce the required artifact, and verify its path.")
            self.save(state)
        state.phase = "failed"
        self.save(state)
        return state
