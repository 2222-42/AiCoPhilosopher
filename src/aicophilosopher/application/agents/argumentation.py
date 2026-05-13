from typing import Any


class ArgumentationAgent:
    def __init__(self, agent_id: str, **kwargs: object) -> None:
        self.agent_id = agent_id

    async def run(self, question: str, **kwargs: object) -> dict[str, Any]:
        raise NotImplementedError
