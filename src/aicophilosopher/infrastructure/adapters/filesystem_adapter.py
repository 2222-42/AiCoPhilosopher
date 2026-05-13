

class FileSystemAdapter:
    def __init__(self, base_path: str = ""):
        self.base_path = base_path

    async def create_project(self, title: str) -> str:
        raise NotImplementedError

    async def write_document(self, project_id: str, filename: str, content: str) -> str:
        raise NotImplementedError

    async def read_document(self, project_id: str, filename: str) -> str | None:
        raise NotImplementedError

    async def list_workstreams(self, project_id: str) -> list[str]:
        raise NotImplementedError

    async def create_directory(self, path: str) -> None:
        raise NotImplementedError
