"""Durable task state and lightweight memory for NeverSoft Agent."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TaskRecord:
    task_id: str
    goal: str
    status: str = "pending"
    phase: str = "received"
    iteration: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class TaskStore:
    """Persist task records as human-readable JSON without external dependencies."""

    def __init__(self, root: str | Path = ".neversoft"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _file(self, task_id: str) -> Path:
        safe = "".join(c for c in task_id if c.isalnum() or c in "-_")
        if not safe:
            raise ValueError("Invalid task id")
        return self.root / f"{safe}.json"

    def save(self, record: TaskRecord) -> TaskRecord:
        record.updated_at = time.time()
        target = self._file(record.task_id)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(record), indent=2, default=str), encoding="utf-8")
        tmp.replace(target)
        return record

    def load(self, task_id: str) -> TaskRecord | None:
        target = self._file(task_id)
        if not target.exists():
            return None
        return TaskRecord(**json.loads(target.read_text(encoding="utf-8")))

    def list(self) -> list[TaskRecord]:
        records = []
        for path in sorted(self.root.glob("*.json")):
            try:
                records.append(TaskRecord(**json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
        return sorted(records, key=lambda r: r.updated_at, reverse=True)

    def append(self, task_id: str, event: dict[str, Any]) -> TaskRecord:
        record = self.load(task_id)
        if record is None:
            raise KeyError(task_id)
        record.history.append({"timestamp": time.time(), **event})
        return self.save(record)


class Memory:
    """Small durable memory store for reusable facts learned during tasks."""

    def __init__(self, path: str | Path = ".neversoft/memory.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"facts": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return {"facts": []}

    def add(self, fact: str, source: str = "agent") -> None:
        fact = fact.strip()
        if not fact:
            return
        data = self._read()
        facts = data.setdefault("facts", [])
        if not any(item.get("fact") == fact for item in facts):
            facts.append({"fact": fact, "source": source, "timestamp": time.time()})
            self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        terms = {word.lower() for word in query.split() if len(word) > 2}
        scored = []
        for item in self._read().get("facts", []):
            text = item.get("fact", "").lower()
            score = sum(term in text for term in terms)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]
