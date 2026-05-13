import asyncio
from typing import Any

import chromadb
from chromadb.config import Settings


class ChromaAdapter:
    def __init__(self, persist_directory: str = "./chroma_data") -> None:
        self._client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )

    async def create_collection(self, name: str, **kwargs: object) -> str:
        metadata: dict[str, str] | None = None
        if "project_id" in kwargs and kwargs["project_id"]:
            metadata = {"project_id": str(kwargs["project_id"])}

        def _create() -> None:
            self._client.get_or_create_collection(name=name, metadata=metadata)

        await asyncio.to_thread(_create)
        return name

    async def add_documents(
        self,
        collection: str,
        documents: list[str],
        metadata: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        def _add() -> None:
            col = self._client.get_or_create_collection(name=collection)
            col.add(documents=documents, metadatas=metadata, ids=ids)  # type: ignore[arg-type]

        await asyncio.to_thread(_add)

    async def query(
        self,
        query: str,
        collection: str = "",
        where: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> list[dict[str, Any]]:

        def _query() -> list[dict[str, Any]]:
            col = self._client.get_or_create_collection(name=collection)
            n_results = int(str(kwargs.get("n_results", "10")))
            where_filter = where or None
            results = col.query(query_texts=[query], n_results=n_results, where=where_filter)
            output = []
            if results["ids"]:
                for i in range(len(results["ids"][0])):
                    entry: dict[str, Any] = {
                        "id": results["ids"][0][i],
                        "score": float(results["distances"][0][i]) if results["distances"] else 0.0,
                        "document": results["documents"][0][i] if results["documents"] else "",
                    }
                    if results["metadatas"] and results["metadatas"][0]:
                        entry["metadata"] = results["metadatas"][0][i]
                    output.append(entry)
            return output

        return await asyncio.to_thread(_query)

    async def delete_collection(self, collection: str) -> None:
        def _delete() -> None:
            try:
                self._client.delete_collection(collection)
            except ValueError:
                pass

        await asyncio.to_thread(_delete)

    def list_collections(self) -> list[str]:
        cols = self._client.list_collections()
        return [c.name for c in cols]
