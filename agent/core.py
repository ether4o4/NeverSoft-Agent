"""Model-driven tool-using agent loop."""

from __future__ import annotations

import inspect
import json
from typing import Any, get_type_hints

from .llm import LLM
from .tools import TOOLS


SYSTEM_PROMPT = """You are NeverSoft Agent, an autonomous task-solving agent.

Work toward the user's actual goal, not just the wording of the request.
You can inspect files, create or modify files, run commands, and use other tools.

Rules:
- Break complex work into concrete steps.
- Inspect before changing unfamiliar files.
- Use tools instead of pretending an action happened.
- After making changes, verify them with a relevant tool or command.
- If a tool fails, diagnose the failure and try a reasonable correction.
- Keep going until the task is complete or a real external dependency blocks you.
- Never claim success without evidence.
- Be concise in the final response: state what was done and any blocker.
"""


def _json_type(annotation: Any) -> str:
    origin = getattr(annotation, "__origin__", None)
    if annotation is bool:
        return "boolean"
    if annotation in (int, float) or origin in (int, float):
        return "number"
    if annotation in (dict, list) or origin in (dict, list):
        return "object" if annotation is dict or origin is dict else "array"
    return "string"


def tool_schemas() -> list[dict[str, Any]]:
    """Convert registered Python tools into OpenAI-compatible schemas."""
    schemas: list[dict[str, Any]] = []
    for name, fn in TOOLS.items():
        signature = inspect.signature(fn)
        hints = get_type_hints(fn)
        properties: dict[str, Any] = {}
        required: list[str] = []
        for param_name, param in signature.parameters.items():
            if param_name == "return":
                continue
            schema: dict[str, Any] = {"type": _json_type(hints.get(param_name, str))}
            if param.default is not inspect.Parameter.empty:
                schema["default"] = param.default
            else:
                required.append(param_name)
            properties[param_name] = schema

        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": (fn.__doc__ or f"Execute {name}").strip(),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        })
    return schemas


class Agent:
    def __init__(self, llm: LLM | None = None, max_steps: int = 16):
        self.llm = llm or LLM()
        self.max_steps = max_steps

    def run(self, task: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]

        for step in range(1, self.max_steps + 1):
            message = self.llm.chat(messages, tool_schemas() or None)
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                return message.get("content") or ""

            messages.append(message)
            for call in tool_calls:
                call_id = call.get("id", f"call_{step}")
                function = call.get("function") or {}
                name = function.get("name", "")
                raw_args = function.get("arguments") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    if name not in TOOLS:
                        raise KeyError(f"Unknown tool: {name}")
                    result = TOOLS[name](**args)
                except Exception as exc:
                    result = {"error": str(exc), "tool": name}

                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": name,
                    "content": json.dumps(result, default=str),
                })

        raise RuntimeError(f"Agent exceeded max_steps={self.max_steps} without finishing")
