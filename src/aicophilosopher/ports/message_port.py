from typing import Protocol


class MessagePort(Protocol):
    async def send(self, message: dict[str, object]) -> str:
        ...

    async def receive(self, recipient_id: str, timeout: float = 5.0) -> list[dict[str, object]]:
        ...

    async def broadcast(self, message: dict[str, object], agent_ids: list[str]) -> list[str]:
        ...

    async def poll_inbox(self, agent_id: str, timeout: float = 5.0) -> list[dict[str, object]]:
        ...
