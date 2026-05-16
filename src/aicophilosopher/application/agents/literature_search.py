from typing import Any

from aicophilosopher.domain.data.bridge_notes import BRIDGE_NOTES  # noqa: F401
from aicophilosopher.domain.services.tradition_manager import DEFAULT_DOMAINS
from aicophilosopher.infrastructure.adapters.search_adapter import SearchTool


class LiteratureSearchAgent:
    def __init__(self, agent_id: str, search_tool: SearchTool | None = None, **kwargs: object) -> None:
        self.agent_id = agent_id
        self.search_tool = search_tool or SearchTool()

    def _generate_bridge_notes(self, query: str, traditions: list[str]) -> list[dict[str, Any]]:
        notes: list[dict[str, Any]] = []
        lower_q = query.strip().lower()
        matched = False

        for concept, trad_notes in BRIDGE_NOTES.items():
            if concept in lower_q or lower_q in concept:
                for cross_key, note_text in trad_notes.items():
                    parts = cross_key.split("→")
                    if len(parts) == 2 and parts[0] in traditions and parts[1] in traditions:
                        matched = True
                        notes.append({
                            "from_tradition": parts[0],
                            "to_tradition": parts[1],
                            "note": note_text,
                            "confidence_score": 0.7,
                        })
        if not matched and len(traditions) >= 2:
            for i in range(len(traditions)):
                for j in range(i + 1, len(traditions)):
                    notes.append({
                        "from_tradition": traditions[i],
                        "to_tradition": traditions[j],
                        "note": f"Bridging {traditions[i]} and {traditions[j]} perspectives on '{query}' requires careful methodological alignment. Key terms may have incommensurable meanings across traditions.",
                        "confidence_score": 0.5,
                    })
        return notes

    async def run(self, query: str, **kwargs: object) -> dict[str, Any]:
        raw_traditions = kwargs.get("traditions")
        trad_list: list[str] = list(raw_traditions) if isinstance(raw_traditions, (list, tuple)) else DEFAULT_DOMAINS

        results = await self.search_tool.search(query, traditions=trad_list)

        bridge_notes = self._generate_bridge_notes(query, trad_list)

        bibliography = []
        for i, r in enumerate(results):
            bibliography.append({
                "id": f"ref-{i + 1}",
                "title": r.get("title", ""),
                "authors": r.get("authors", []),
                "year": r.get("year"),
                "abstract": r.get("abstract", ""),
                "url": r.get("url", ""),
                "source": r.get("source", ""),
                "tradition_tag": r.get("tradition_tag", "analytic"),
                "relevance_score": r.get("relevance_score", 0.5),
                "bibtex": f"@article{{ref{i + 1},\n  title={{{r.get('title', '')}}},\n  year={{{r.get('year', 'n.d.')}}},\n}}",
            })

        return {
            "query": query,
            "traditions": trad_list,
            "result_count": len(bibliography),
            "bibliography": bibliography,
            "bridge_notes": bridge_notes,
            "confidence": 0.7 if results else 0.3,
        }
