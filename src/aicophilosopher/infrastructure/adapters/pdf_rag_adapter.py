

class PDFRAGTool:
    def __init__(self, chroma_adapter: object = None) -> None:
        self.chroma_adapter = chroma_adapter

    async def ingest_pdf(self, path: str) -> dict[str, object]:
        raise NotImplementedError

    async def query(self, query: str, **kwargs: object) -> list[dict[str, object]]:
        raise NotImplementedError
