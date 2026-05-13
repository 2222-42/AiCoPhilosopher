from typing import Any


class DocumentParser:
    async def parse(self, file_path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        raise NotImplementedError

    async def validate_annotations(self, annotations: list[dict[str, Any]]) -> bool:
        raise NotImplementedError
