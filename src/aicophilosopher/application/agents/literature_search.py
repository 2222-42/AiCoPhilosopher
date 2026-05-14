from typing import Any

from aicophilosopher.domain.services.tradition_manager import DEFAULT_DOMAINS
from aicophilosopher.infrastructure.adapters.search_adapter import SearchTool

BRIDGE_NOTES: dict[str, dict[str, str]] = {
    "abstraction": {
        "analytic→philosophy_of_technology": "Analytic philosophy analyses abstraction as a formal operation; philosophy of technology examines how abstraction layers in software mediate human activity and embed normative commitments.",
        "analytic→philosophy_of_mathematics": "Analytic philosophy treats mathematical abstraction as removing properties to expose structure; software architecture treats abstraction as hiding implementation behind interfaces. These serve different epistemic purposes.",
        "philosophy_of_mathematics→software_architecture": "Mathematical abstraction discovers formal structure; software abstraction designs interfaces. Conflating the two risks treating design choices as mathematical necessities.",
        "philosophy_of_technology→software_architecture": "Technological mediation theory (Ihde, Verbeek) reveals how software abstraction is not neutral: each layer reshapes what users can perceive and do.",
    },
    "model": {
        "analytic→model_theory": "Analytic philosophy of science treats models as representations of target systems; model theory treats models as interpretations of formal languages. Both senses converge in scientific modelling but with different validity criteria.",
        "philosophy_of_science→software_architecture": "Scientific models aim at isomorphism with reality; software models aim at executable specification. The normative standards differ: empirical adequacy vs behavioural correctness.",
        "model_theory→software_architecture": "Model-theoretic semantics (Tarski) provides a formal framework applicable to software specification languages (algebraic specification, abstract state machines), but the engineering constraints add pragmatic criteria beyond formal satisfiability.",
    },
    "computation": {
        "analytic→philosophy_of_mathematics": "Turing's analysis of computation bridges analytic philosophy of mind (functionalism) and philosophy of mathematics (computability theory). The Church-Turing thesis has implications for both domains.",
        "philosophy_of_technology→software_architecture": "Computational thinking transforms how we understand cognition, social organisation, and agency. Software architecture embodies assumptions about what computation is and what it can formalise.",
    },
    "proof": {
        "analytic→philosophy_of_mathematics": "Mathematical proof is a social-epistemic practice involving understanding; formal proof is a syntactic derivation. Both are relevant to philosophical argumentation with different epistemic standards.",
        "philosophy_of_mathematics→software_architecture": "Formal verification in software (model checking, theorem proving) draws on proof theory but applies it to systems with state, time, and concurrency—extending classical proof concepts.",
    },
    "correctness": {
        "analytic→software_architecture": "Analytic philosophy distinguishes necessary and sufficient conditions; software correctness requires formal specification of both. The gap between specification and implementation mirrors the gap between concept and object in analytic epistemology.",
        "philosophy_of_science→software_architecture": "Scientific falsification (Popper) and software testing (falsifying hypotheses about program behaviour) share structural parallels, but the normative aims differ: scientific truth vs operational reliability.",
    },
    "truth": {
        "analytic→model_theory": "Tarski's semantic conception of truth (truth in a model) provides a formal framework for understanding correspondence and its limits. Model-theoretic truth is relative to interpretation—a lesson relevant to philosophical pluralism.",
        "continental→philosophy_of_technology": "Heideggerian aletheia (unconcealment) and technological enframing (Gestell) offer a non-correspondence account of truth-as-disclosure relevant to understanding how software systems shape what is intelligible.",
    },
    "design": {
        "analytic→philosophy_of_technology": "Analytic aesthetics and philosophy of technology converge on the concept of design: both treat artefacts as embodying intentions and values that merit philosophical analysis.",
        "philosophy_of_technology→software_architecture": "Software design embeds ontological assumptions (what entities exist in the system, how they relate) and normative commitments (what counts as good structure). These deserve philosophical scrutiny.",
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
