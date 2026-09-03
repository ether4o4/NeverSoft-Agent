from collections.abc import Callable

TOOLS: dict[str, Callable] = {}


def tool(name: str):
    def register(fn: Callable):
        TOOLS[name] = fn
        return fn
    return register
