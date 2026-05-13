from typing import Any


class BaseAgent:
    def __init__(self, agent_id: str, **kwargs: object) -> None:
        self.agent_id = agent_id
        self.tools: dict[str, Any] = {}
        self.config: dict[str, Any] = {}

    async def run(self, **kwargs: object) -> Any:
        raise NotImplementedError

    async def send_message(self, recipient_id: str, message_type: str, payload: dict[str, object]) -> str:
        raise NotImplementedError
