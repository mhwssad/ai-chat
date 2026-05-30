"""核心业务能力。"""


def __getattr__(name: str):
    if name == "container":
        from src.ai.core.container import container

        return container
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
