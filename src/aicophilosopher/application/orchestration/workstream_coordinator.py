from typing import Any


class WorkstreamCoordinatorAgent:
    def __init__(self, workstream_id: str, workstream_type: str, **kwargs: object) -> None:
        self.workstream_id = workstream_id
        self.workstream_type = workstream_type
        self.status: str = "pending"

    async def start(self) -> None:
        raise NotImplementedError

    async def pause(self) -> None:
        raise NotImplementedError

    async def resume(self) -> None:
        raise NotImplementedError

    async def steer(self, instruction: str) -> None:
        raise NotImplementedError

    async def get_progress(self) -> dict[str, Any]:
        raise NotImplementedError
