from agent.core import Agent


if __name__ == "__main__":
    task = input("NeverSoft > ").strip()
    if task:
        print("\nWorking...\n")
        result = Agent().run(task)
        print(result)
