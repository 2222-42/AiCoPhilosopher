import asyncio
import hashlib
import os
import re
from typing import Any

import fitz  # PyMuPDF

from aicophilosopher.infrastructure.adapters.chroma_adapter import ChromaAdapter


def _sanitize_collection_name(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = re.sub(r"\.{2,}", ".", name)
    name = name.strip("._-")
    if len(name) < 3 or len(name) > 63:
        suffix = hashlib.sha256(name.encode()).hexdigest()[:8]
        base = name[:50] if name else "doc"
        name = f"{base}_{suffix}"
    if not name[0].isalnum() if name else True:
        name = f"d_{name}"
    if len(name) > 63:
        name = name[:63]
    name = name.strip("._-")
    return name or "default_collection"


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError(f"overlap ({overlap}) must be less than chunk_size ({chunk_size})")
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += max(1, chunk_size - overlap)
    return chunks


def _extract_metadata(doc: fitz.Document) -> dict[str, Any]:
    meta = doc.metadata
    keywords_list = [k.strip() for k in meta.get("keywords", "").split(",") if k.strip()]
    return {
        "title": meta.get("title", "").strip(),
        "author": meta.get("author", "").strip(),
        "subject": meta.get("subject", "").strip(),
        "keywords": ", ".join(keywords_list),
        "page_count": doc.page_count,
    }


class PDFRAGTool:
    def __init__(self, chroma_adapter: ChromaAdapter | None = None) -> None:
        self.chroma = chroma_adapter or ChromaAdapter()

    async def ingest_pdf(self, path: str) -> dict[str, Any]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"PDF not found: {path}")

        def _extract() -> dict[str, Any]:
            doc = fitz.open(path)
            try:
                metadata = _extract_metadata(doc)
                all_text = ""
                for page in doc:
                    all_text += page.get_text() + "\n"
                metadata["total_chars"] = len(all_text)
                metadata["total_pages"] = doc.page_count
                chunks = _chunk_text(all_text)
                metadata["chunk_count"] = len(chunks)
                metadata["chunks"] = chunks
                return metadata
            finally:
                doc.close()

        metadata = await asyncio.to_thread(_extract)
        chunks = metadata.pop("chunks", [])
        collection = _sanitize_collection_name(os.path.splitext(os.path.basename(path))[0])

        await self.chroma.create_collection(collection, project_id=metadata.get("title") or collection)
        if chunks:
            await self.chroma.add_documents(
                collection=collection,
                documents=chunks,
                metadata=[{"source": path, "chunk_idx": i} for i in range(len(chunks))],
                ids=[f"{collection}_chunk_{i}" for i in range(len(chunks))],
            )
        return {"collection": collection, "chunks": len(chunks), "metadata": metadata}

    async def query(self, query: str, **kwargs: object) -> list[dict[str, Any]]:
        collection = str(kwargs.pop("collection", ""))
        where = kwargs.pop("where", None)
        where_dict: dict[str, Any] | None = None
        if isinstance(where, dict):
            where_dict = where
        return await self.chroma.query(query, collection=collection, where=where_dict, **kwargs)
