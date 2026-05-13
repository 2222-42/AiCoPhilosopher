"""Skeleton for code execution. Post-MVP."""


class CodeExecutionTool:
    def __init__(self) -> None:
        pass

    async def execute_python(self, code: str, **kwargs: object) -> dict[str, object]:
        raise NotImplementedError

    async def execute_prolog(self, code: str, **kwargs: object) -> dict[str, object]:
        raise NotImplementedError
