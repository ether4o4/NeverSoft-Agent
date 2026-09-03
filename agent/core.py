"""Minimal tool-using agent loop."""

from __future__ import annotations

import json
from typing import Any

from .llm import LLM
from .tools import TOOLS


SYSTEM_PROMPT = """You are NeverSoft Agent. Solve the user's task directly. Use a tool when it is useful; otherwise answer normally. Keep tool arguments valid JSON."""


def tool_schemas() -> list[dict[str, Any]]:
    schemas = []
    for name, fn in TOOLS.items():
        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": (fn.__doc__ or f"Execute {name}").strip(),
                "parameters": {"type": "object", "properties": {}, "additionalProperties": True},
            },
        })
    return schemas


class Agent:
    def __init__(self, llm: LLM | None = None, max_steps: int = 8):
        self.llm = llm or LLM()
        self.max_steps = max_steps

    def run(self, task: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]

        for _ in range(self.max_steps):
            message = self.llm.chat(messages, tool_schemas() or None)
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                return message.get("content") or ""

            messages.append(message)
            for call in tool_calls:
                name = call["function"]["name"]
                raw_args = call["function"].get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                    result = TOOLS[name](**args)
                except Exception as exc:
                    result = {"error": str(exc)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "name": name,
                    "content": json.dumps(result, default=str),
                })

        raise RuntimeError(f"Agent exceeded max_steps={self.max_steps}")
