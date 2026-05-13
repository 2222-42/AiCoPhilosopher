

class SQLiteAdapter:
    def __init__(self, db_path: str = ""):
        self.db_path = db_path

    async def save_project(self, project: dict[str, object]) -> str:
        raise NotImplementedError

    async def load_project(self, project_id: str) -> dict[str, object] | None:
        raise NotImplementedError

    async def save_workstream(self, project_id: str, workstream: dict[str, object]) -> str:
        raise NotImplementedError

    async def load_workstream(self, project_id: str, workstream_id: str) -> dict[str, object] | None:
        raise NotImplementedError

    async def query_uncertainty(self, project_id: str, **filters: object) -> list[dict[str, object]]:
        raise NotImplementedError

    async def save_note(self, project_id: str, note: dict[str, object]) -> str:
        raise NotImplementedError

    async def list_projects(self) -> list[dict[str, object]]:
        raise NotImplementedError

    async def delete_project(self, project_id: str) -> bool:
        raise NotImplementedError
