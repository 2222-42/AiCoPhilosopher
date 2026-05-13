from typing import Any


class StartProjectUseCase:
    async def execute(self, title: str, question: str = "", **kwargs: object) -> dict[str, Any]:
        raise NotImplementedError
