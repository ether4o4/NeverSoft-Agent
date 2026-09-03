import re

from agent.build_loop import BuildCompletionLoop
from agent.core import Agent
from agent.llm import LLM
from agent.tools import WORKSPACE


BUILD_TRIGGERS = re.compile(
    r"\b(build this|complete the build|finish it|full build|make it complete|build the apk|make an apk|build the whole thing)\b",
    re.IGNORECASE,
)


if __name__ == "__main__":
    task = input("NeverSoft > ").strip()
    if not task:
        raise SystemExit(0)

    llm = LLM()
    agent = Agent(llm=llm, max_steps=24)

    if BUILD_TRIGGERS.search(task):
        loop = BuildCompletionLoop(WORKSPACE, llm=lambda prompt: llm.chat([
            {"role": "system", "content": "You are the NeverSoft implementation worker. Execute the requested implementation using available tools. Do not just explain."},
            {"role": "user", "content": prompt},
        ]).get("content", ""))

        def implement(prompt: str) -> str:
            return agent.run(prompt)

        state = loop.run(task, implement=implement)
        print(state.phase)
        if state.verified:
            print("Verified artifact:", ", ".join(state.artifacts))
        else:
            print("Build did not reach verified completion.")
    else:
        print("\nWorking...\n")
        print(agent.run(task))
