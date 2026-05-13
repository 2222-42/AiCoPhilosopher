from typing import Any


class LaunchWorkstreamUseCase:
    async def execute(self, project_id: str, workstream_type: str, **kwargs: object) -> dict[str, Any]:
        raise NotImplementedError
