

class SearchTool:
    def __init__(self, allow_external: bool = False):
        self.allow_external = allow_external

    async def search(self, query: str, traditions: list[str] | None = None, **kwargs: object) -> list[dict[str, object]]:
        raise NotImplementedError

    async def query_philpapers(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        raise NotImplementedError

    async def query_sep(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        raise NotImplementedError

    async def query_arxiv(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        raise NotImplementedError

    async def query_semantic_scholar(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        raise NotImplementedError
