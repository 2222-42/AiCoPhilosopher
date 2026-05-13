from typing import Protocol


class DialecticalHistoryPort(Protocol):
    async def append_move(self, project_id: str, move: dict[str, object]) -> str:
        ...

    async def query_history(self, project_id: str, **filters: object) -> list[dict[str, object]]:
        ...

    async def get_dialectical_tree(self, project_id: str, move_id: str) -> dict[str, object] | None:
        ...
