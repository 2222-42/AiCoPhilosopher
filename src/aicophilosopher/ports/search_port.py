from typing import Protocol


class SearchPort(Protocol):
    async def query_philpapers(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        ...

    async def query_sep(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        ...

    async def query_arxiv(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        ...

    async def query_semantic_scholar(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        ...

    async def search(self, query: str, traditions: list[str] | None = None, **kwargs: object) -> list[dict[str, object]]:
        ...
