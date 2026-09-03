from agent.core import Agent


if __name__ == "__main__":
    task = input("NeverSoft > ").strip()
    if task:
        print(Agent().run(task))
