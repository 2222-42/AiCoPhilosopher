from typing import Any

from aicophilosopher.infrastructure.adapters.search_adapter import SearchTool

BRIDGE_NOTES: dict[str, dict[str, str]] = {
    "mind": {
        "analytic→buddhist": "The concept of 'mind' in analytic philosophy (consciousness/qualia) parallels Buddhist vinnana (consciousness) and citta (mind), but Buddhist analysis denies a substantial self (anatta) that much Western philosophy of mind presupposes.",
        "analytic→confucian": "Analytic philosophy of mind focuses on mental representation; Confucian xin (心, heart-mind) integrates cognition and emotion as a unified moral-psychological faculty.",
        "analytic→daoist": "Analytic mental representation contrasts with Daoist xin (心) as spontaneous responsiveness (wúwéi), rejecting inner-outer dualism.",
        "buddhist→continental": "Buddhist citta (mind) and no-self doctrine intersect with continental critiques of the Cartesian cogito (Sartre, Derrida).",
    },
    "self": {
        "analytic→buddhist": "Analytic personal identity theories (Parfit, Locke) challenge the unity of self; Buddhist anatta (no-self) radically extends this by denying any permanent substratum.",
        "analytic→confucian": "Analytic self is individual and autonomous; Confucian self is relational, constituted through roles (五伦, five relationships).",
        "analytic→daoist": "Analytic self-ownership models contrast with Daoist self-abandonment (wúwǒ, 无我) as spontaneous attunement to Dào.",
    },
    "free will": {
        "analytic→buddhist": "Analytic compatibilism vs libertarianism debates parallel Buddhist karma-and-free-will discourses. Buddhists reject fixed determinism while affirming moral responsibility through pratityasamutpada (dependent origination).",
        "analytic→confucian": "Confucian ming (命, fate) and tian (天, heaven) offer a non-Western compatibilism: moral agency within cosmic order.",
    },
    "ethics": {
        "analytic→confucian": "Western duty-based ethics vs Confucian role-based ethics (ren, 仁). Both are universalist but the Confucian self is irreducibly social.",
        "analytic→buddhist": "Consequentialist welfare calculations parallel Buddhist karuna (compassion) ethics, but Buddhist ethics is grounded in phenomenological insight (prajna) rather than utility maximization.",
    },
    "knowledge": {
        "analytic→buddhist": "Analytic JTB epistemology vs Buddhist pramana theory. Buddhists accept perception and inference as valid instruments but reject testimony-independent justification.",
    },
    "truth": {
        "analytic→buddhist": "Correspondence truth vs Buddhist two-truths doctrine (conventional + ultimate). Nagarjuna's emptiness undermines correspondence while preserving conventional truth.",
        "continental→daoist": "Heideggerian aletheia (unconcealment) resonates with Daoist unnamed dao beyond discursive truth.",
    },
}


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
                matched = False
                for cross_key, note_text in trad_notes.items():
                    if any(t in cross_key for t in traditions):
                        matched = True
                        src, dst = cross_key.split("→")
                        notes.append({
                            "from_tradition": src,
                            "to_tradition": dst,
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
        trad_list: list[str] = list(raw_traditions) if isinstance(raw_traditions, (list, tuple)) else ["analytic"]

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
