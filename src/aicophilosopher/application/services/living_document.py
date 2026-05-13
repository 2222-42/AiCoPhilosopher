from typing import Any


class LivingDocument:
    def __init__(self, project_id: str, title: str = "") -> None:
        self.project_id = project_id
        self.title = title
        self.content: str = ""
        self.frontmatter: dict[str, Any] = {}

    async def create(self, title: str, project_id: str) -> str:
        raise NotImplementedError

    async def add_section(self, name: str, content: str) -> None:
        raise NotImplementedError

    async def embed_annotations(self) -> str:
        raise NotImplementedError

    async def parse_annotations(self) -> list[dict[str, Any]]:
        raise NotImplementedError
