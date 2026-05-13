from typing import Any


class SynthesisAgent:
    def __init__(self, agent_id: str, **kwargs: object) -> None:
        self.agent_id = agent_id

    async def run(self, workstream_outputs: list[dict[str, Any]], **kwargs: object) -> dict[str, Any]:
        raise NotImplementedError
