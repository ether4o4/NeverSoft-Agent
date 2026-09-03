"""Autonomous task runtime: plan, execute, observe, recover, verify."""
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Task:
    goal: str
    steps: list[str] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)
    status: str = "pending"


class AgentRuntime:
    def __init__(self, llm: Callable[[str], str], tools: dict[str, Callable] | None = None):
        self.llm = llm
        self.tools = tools or {}

    def plan(self, goal: str) -> Task:
        prompt = (
            "Break this goal into the smallest useful executable steps. "
            "Return one step per line, no numbering.\n\nGoal: " + goal
        )
        raw = self.llm(prompt)
        steps = [line.strip(" -*\t") for line in raw.splitlines() if line.strip()]
        return Task(goal=goal, steps=steps)

    def run(self, task: Task, max_steps: int = 20) -> Task:
        task.status = "running"
        for _ in range(min(max_steps, len(task.steps))):
            step = task.steps.pop(0)
            try:
                result = self.execute(step)
                task.results.append({"step": step, "result": result, "status": "ok"})
            except Exception as exc:
                task.results.append({"step": step, "error": str(exc), "status": "failed"})
                recovery = self.llm(
                    f"The step failed: {step}\nError: {exc}\n"
                    "Return one corrected replacement step only."
                ).strip()
                if recovery:
                    task.steps.insert(0, recovery)
                else:
                    task.status = "failed"
                    return task
        task.status = "completed" if not task.steps else "paused"
        return task

    def execute(self, step: str) -> Any:
        # Explicit tool syntax: tool_name: argument
        if ":" in step:
            name, argument = step.split(":", 1)
            name = name.strip()
            if name in self.tools:
                return self.tools[name](argument.strip())
        return self.llm(step)

    def verify(self, task: Task) -> bool:
        evidence = "\n".join(str(item) for item in task.results)
        answer = self.llm(
            f"Goal: {task.goal}\nEvidence:\n{evidence}\n"
            "Did the evidence demonstrate that the goal was completed? "
            "Answer only YES or NO."
        ).strip().upper()
        return answer.startswith("YES")
