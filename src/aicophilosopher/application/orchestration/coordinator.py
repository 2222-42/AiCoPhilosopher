from typing import Any


class ProjectCoordinatorAgent:
    def __init__(self, project_id: str, **kwargs: object) -> None:
        self.project_id = project_id
        self.dialogue_history: list[dict[str, Any]] = []

    async def run(self, user_input: str) -> dict[str, Any]:
        raise NotImplementedError

    async def propose_workstream(self, workstream_type: str, **kwargs: object) -> dict[str, Any]:
        raise NotImplementedError

    async def handle_steering_command(self, command: str, **kwargs: object) -> dict[str, Any]:
        raise NotImplementedError

    async def get_status_summary(self) -> dict[str, Any]:
        raise NotImplementedError
