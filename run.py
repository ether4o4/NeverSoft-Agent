from agent.llm import LLM
from agent.runtime import AgentRuntime


if __name__ == "__main__":
    goal = input("Task: ").strip()
    if goal:
        agent = AgentRuntime(LLM().complete)
        task = agent.plan(goal)
        print("\nPlan:")
        for step in task.steps:
            print("-", step)
        task = agent.run(task)
        print("\nStatus:", task.status)
        print("Verified:", agent.verify(task))
        print("\nResults:")
        for result in task.results:
            print(result)
