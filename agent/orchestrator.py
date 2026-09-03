"""High-level autonomous orchestration for NeverSoft Agent."""

from __future__ import annotations

import json
import uuid
from typing import Any

from .core import Agent
from .persistence import Memory, TaskRecord, TaskStore


class Orchestrator:
    """Run resumable agent tasks and preserve evidence across interruptions."""

    def __init__(self, agent: Agent | None = None, root: str = ".neversoft"):
        self.agent = agent or Agent()
        self.store = TaskStore(root)
        self.memory = Memory(f"{root}/memory.json")

    def start(self, goal: str) -> TaskRecord:
        task_id = uuid.uuid4().hex[:12]
        record = TaskRecord(task_id=task_id, goal=goal, status="running", phase="reasoning")
        self.store.save(record)
        self.store.append(task_id, {"event": "started", "goal": goal})
        return self.run(record)

    def run(self, record: TaskRecord) -> TaskRecord:
        try:
            result = self.agent.run(record.goal)
            record.status = "completed"
            record.phase = "verified"
            record.history.append({"event": "agent_result", "result": result})
            self.memory.add(f"Completed task: {record.goal}", source=record.task_id)
        except Exception as exc:
            record.status = "paused"
            record.phase = "blocked"
            record.history.append({"event": "failure", "error": str(exc)})
        return self.store.save(record)

    def resume(self, task_id: str) -> TaskRecord:
        record = self.store.load(task_id)
        if record is None:
            raise KeyError(f"Unknown task: {task_id}")
        record.status = "running"
        record.phase = "resuming"
        self.store.save(record)
        return self.run(record)

    def snapshot(self, task_id: str) -> dict[str, Any]:
        record = self.store.load(task_id)
        if record is None:
            raise KeyError(f"Unknown task: {task_id}")
        return json.loads(json.dumps(record.__dict__, default=str))
