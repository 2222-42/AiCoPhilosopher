

class ChromaAdapter:
    def __init__(self, persist_directory: str = "./chroma_data"):
        self.persist_directory = persist_directory

    async def create_collection(self, name: str, **kwargs: object) -> str:
        raise NotImplementedError

    async def add_documents(self, collection: str, documents: list[str], metadata: list[dict[str, object]], ids: list[str]) -> None:
        raise NotImplementedError

    async def query(self, query: str, collection: str = "", where: dict[str, object] | None = None, **kwargs: object) -> list[dict[str, object]]:
        raise NotImplementedError
