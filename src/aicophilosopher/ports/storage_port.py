from typing import Protocol


class StoragePort(Protocol):
    async def save_project(self, project: dict[str, object]) -> str:
        ...

    async def load_project(self, project_id: str) -> dict[str, object] | None:
        ...

    async def save_workstream(self, project_id: str, workstream: dict[str, object]) -> str:
        ...

    async def load_workstream(self, project_id: str, workstream_id: str) -> dict[str, object] | None:
        ...

    async def query_uncertainty(self, project_id: str, **filters: object) -> list[dict[str, object]]:
        ...

    async def save_note(self, project_id: str, note: dict[str, object]) -> str:
        ...

    async def list_projects(self) -> list[dict[str, object]]:
        ...

    async def delete_project(self, project_id: str) -> bool:
        ...
