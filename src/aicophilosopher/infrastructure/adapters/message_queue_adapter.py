

class MessageQueueAdapter:
    def __init__(self, db_path: str = ""):
        self.db_path = db_path

    async def send(self, message: dict[str, object]) -> str:
        raise NotImplementedError

    async def receive(self, recipient_id: str, timeout: float = 5.0) -> list[dict[str, object]]:
        raise NotImplementedError

    async def broadcast(self, message: dict[str, object], agent_ids: list[str]) -> list[str]:
        raise NotImplementedError

    async def poll_inbox(self, agent_id: str, timeout: float = 5.0) -> list[dict[str, object]]:
        raise NotImplementedError
