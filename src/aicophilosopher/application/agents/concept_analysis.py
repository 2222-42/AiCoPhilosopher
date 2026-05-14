from typing import Any

from aicophilosopher.domain.services.tradition_manager import DEFAULT_DOMAINS, TraditionManager

THOUGHT_EXPERIMENTS: dict[str, list[dict[str, Any]]] = {
    "mind": [
        {"name": "Mary's Room", "description": "A neuroscientist raised in a black-and-white room knows all physical facts about color but has never seen color. Upon leaving, does she learn something new?", "tradition": "analytic", "epistemic_status": "widely accepted as showing qualia are non-physical"},
        {"name": "Brain in a Vat", "description": "If your brain is kept alive in a vat and fed electrical impulses identical to those a normal brain receives, how can you know your experiences correspond to reality?", "tradition": "analytic", "epistemic_status": "widely used in epistemology of perception"},
        {"name": "Chinese Room (Searle)", "description": "A person who does not understand Chinese follows English instructions to manipulate Chinese symbols, producing output indistinguishable from a native speaker. Searle argues this shows computation alone is insufficient for understanding.", "tradition": "analytic", "epistemic_status": "contested; central to philosophy of AI debate"},
    ],
    "computation": [
        {"name": "Turing Test", "description": "If a computer can converse indistinguishably from a human in a blind test, does it think? Turing proposed this as a replacement for the question 'Can machines think?'", "tradition": "analytic", "epistemic_status": "widely used benchmark; contested as sufficient condition for intelligence"},
        {"name": "Chinese Room", "description": "Searle's argument that syntactic manipulation of symbols is not sufficient for semantic understanding. Challenges strong AI and computational functionalism.", "tradition": "analytic", "epistemic_status": "contested; one of the most discussed arguments in philosophy of AI"},
        {"name": "Halting Problem Thought Experiment", "description": "Can a program determine, for any arbitrary program and input, whether that program will halt or run forever? Turing proved no such program can exist—a fundamental limit of computation.", "tradition": "philosophy_of_mathematics", "epistemic_status": "mathematically proven; philosophical implications for mechanism and mind"},
    ],
    "abstraction": [
        {"name": "Ship of Theseus (Software Edition)", "description": "If a software system is gradually refactored until every component has been replaced, is it the same system? What constitutes identity for software over time?", "tradition": "philosophy_of_technology", "epistemic_status": "classical problem applied to software identity"},
        {"name": "Borges' Map (Baudrillard)", "description": "A map so detailed it covers the entire territory becomes indistinguishable from it. In software, when does a simulation become indistinguishable from the simulated?", "tradition": "continental", "epistemic_status": "hyperreality thought experiment; relevant to digital twin and simulation discourse"},
    ],
    "model": [
        {"name": "Maxwell's Demon", "description": "A tiny demon controls a door between two gas chambers, letting only fast molecules through, decreasing entropy. Maxwell's thought experiment probes the relationship between thermodynamics and information.", "tradition": "philosophy_of_science", "epistemic_status": "resolved by Landauer's principle; illustrates information-physics connection"},
    ],
    "correctness": [
        {"name": "Boeing 737 MAX Thought Experiment", "description": "A software system passes all specified tests but causes catastrophic failure under conditions not covered by the specification. Is the software correct? If not, where does the error reside?", "tradition": "software_architecture", "epistemic_status": "real-world case; demonstrates the gap between verification and correctness"},
    ],
    "truth": [
        {"name": "Gödel Numbering", "description": "Gödel showed that any consistent formal system containing arithmetic can construct a sentence that is true but unprovable within the system. What does this imply about the relationship between truth and proof?", "tradition": "philosophy_of_mathematics", "epistemic_status": "mathematically proven; profound philosophical implications for formalism"},
    ],
}

NECESSARY_SUFFICIENT_CONDITIONS: dict[str, dict[str, Any]] = {
    "knowledge": {
        "necessary_conditions": ["belief", "truth", "justification"],
        "sufficient_conditions": ["justified true belief (JTB)", "subject achieves epistemic warrant"],
        "notes": "Gettier cases show JTB may not be sufficient; externalist and virtue-theoretic alternatives exist.",
    },
    "computation": {
        "necessary_conditions": ["finite specification of rules", "effective procedure", "symbolic representation"],
        "sufficient_conditions": ["Turing-computable function", "Church-Turing thesis holds"],
        "notes": "Church-Turing thesis is empirical/circumstantial, not mathematically provable. Hypercomputation models challenge sufficiency. Non-halting computations (OS kernels, servers, partial recursive functions) are still computations; termination is not a necessary condition.",
    },
    "abstraction": {
        "necessary_conditions": ["omission of detail", "preservation of essential structure"],
        "sufficient_conditions": ["the abstracted model preserves all properties relevant to the given purpose"],
        "notes": "What counts as 'essential' is purpose-relative. Mathematical abstraction and software abstraction have different purpose-dependencies.",
    },
}

DISTINCTIONS: dict[str, list[dict[str, str]]] = {
    "mind": [
        {"concept_a": "qualia", "concept_b": "intentionality", "distinction_type": "phenomenal vs semantic", "description": "Qualia are the felt qualities of experience; intentionality is the aboutness or directedness of mental states.", "tradition": "analytic"},
        {"concept_a": "functional role", "concept_b": "phenomenal character", "distinction_type": "functionalist vs qualia", "description": "Functionalism defines mental states by their causal role; phenomenalism by their felt quality. The explanatory gap separates them.", "tradition": "analytic"},
    ],
    "computation": [
        {"concept_a": "syntax", "concept_b": "semantics", "distinction_type": "formal vs interpretive", "description": "Syntax concerns formal symbol manipulation rules; semantics concerns meaning and reference. The gap between them is central to AI philosophy.", "tradition": "analytic"},
        {"concept_a": "algorithm", "concept_b": "heuristic", "distinction_type": "guarantee vs guidance", "description": "Algorithms guarantee correctness; heuristics guide search without guarantees. Both are essential in software architecture with different epistemic status.", "tradition": "software_architecture"},
    ],
    "abstraction": [
        {"concept_a": "mathematical abstraction", "concept_b": "software abstraction", "distinction_type": "discovery vs design", "description": "Mathematical abstraction strips properties to expose formal structure (discovery); software abstraction hides implementation behind interfaces (design).", "tradition": "philosophy_of_mathematics"},
        {"concept_a": "formal specification", "concept_b": "implementation", "distinction_type": "what vs how", "description": "Formal specifications define what a system should do; implementations define how. The gap is the central problem of software correctness.", "tradition": "software_architecture"},
    ],
    "truth": [
        {"concept_a": "correspondence", "concept_b": "coherence", "distinction_type": "truth theory", "description": "Correspondence truth matches propositions to reality; coherence truth is consistency within a belief system.", "tradition": "analytic"},
        {"concept_a": "syntactic truth", "concept_b": "semantic truth", "distinction_type": "provability vs model-theoretic", "description": "Syntactic truth is derivability within a formal system; semantic truth is satisfaction in a model. Gödel's completeness theorem bridges them for first-order logic.", "tradition": "model_theory"},
    ],
    "model": [
        {"concept_a": "scientific model", "concept_b": "software model", "distinction_type": "representational vs operational", "description": "Scientific models aim at isomorphism with target systems; software models (UML, formal specs) aim at executable or analysable specifications with different success criteria.", "tradition": "philosophy_of_science"},
        {"concept_a": "structural model", "concept_b": "causal model", "distinction_type": "static vs dynamic", "description": "Structural models represent static relationships; causal models represent generative mechanisms. Software architecture uses both but must also address temporal behaviour.", "tradition": "model_theory"},
    ],
}


class ConceptAnalysisAgent:
    def __init__(self, agent_id: str, tradition_manager: TraditionManager | None = None, **kwargs: object) -> None:
        self.agent_id = agent_id
        self.tradition_manager = tradition_manager or TraditionManager()

    async def run(self, concept: str, **kwargs: object) -> dict[str, Any]:
        lower_concept = concept.strip().lower()
        trad_arg = kwargs.get("traditions")
        traditions: list[str] = list(trad_arg) if isinstance(trad_arg, (list, tuple)) else DEFAULT_DOMAINS

        concept_map = self._build_concept_map(lower_concept, traditions)
        distinction_matrix = self._build_distinction_matrix(lower_concept)
        thought_experiments = THOUGHT_EXPERIMENTS.get(lower_concept, self._generic_thought_experiments(concept))
        conditions = NECESSARY_SUFFICIENT_CONDITIONS.get(lower_concept, {})
        genealogy = self._build_genealogy(lower_concept)

        return {
            "concept": concept,
            "traditions_examined": traditions,
            "concept_map": concept_map,
            "distinction_matrix": distinction_matrix,
            "thought_experiments": thought_experiments,
            "necessary_sufficient_conditions": conditions,
            "genealogy": genealogy,
            "confidence": 0.75,
        }

    def _build_concept_map(self, concept: str, traditions: list[str]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        seen: set[str] = set()

        for trad in traditions:
            primary = f"{concept}_{trad}"
            if primary not in seen:
                seen.add(primary)
                nodes.append({
                    "concept_id": primary,
                    "name": concept,
                    "tradition": trad,
                    "definition": f"The concept of {concept} as understood within {trad}.",
                    "related_concepts": [f"{concept}_analysis", f"{concept}_critique"],
                })

        if concept in DISTINCTIONS:
            for d in DISTINCTIONS[concept]:
                for side in ("concept_a", "concept_b"):
                    sid = d.get(side, "")
                    if sid not in seen:
                        seen.add(sid)
                        nodes.append({
                            "concept_id": sid,
                            "name": sid,
                            "tradition": d.get("tradition", "analytic"),
                            "definition": d.get("description", ""),
                            "related_concepts": [],
                        })

        return nodes[:10]

    def _build_distinction_matrix(self, concept: str) -> list[dict[str, str]]:
        return DISTINCTIONS.get(concept, [])

    def _build_genealogy(self, concept: str) -> list[dict[str, Any]]:
        genealogy_map: dict[str, list[dict[str, Any]]] = {
            "mind": [
                {"philosopher": "Descartes", "text": "Meditations", "contribution": "Mind-body dualism", "approximate_date": "1641"},
                {"philosopher": "Kant", "text": "Critique of Pure Reason", "contribution": "Transcendental unity of apperception", "approximate_date": "1781"},
                {"philosopher": "Turing", "text": "Computing Machinery and Intelligence", "contribution": "Computational theory of mind; Turing Test", "approximate_date": "1950"},
                {"philosopher": "Putnam", "text": "The Nature of Mental States", "contribution": "Machine-state functionalism", "approximate_date": "1967"},
                {"philosopher": "Searle", "text": "Minds, Brains, and Programs", "contribution": "Chinese Room argument against strong AI", "approximate_date": "1980"},
            ],
            "computation": [
                {"philosopher": "Turing", "text": "On Computable Numbers", "contribution": "Formal definition of computation; universal Turing machine", "approximate_date": "1936"},
                {"philosopher": "Gödel", "text": "On Formally Undecidable Propositions", "contribution": "Incompleteness theorems; limits of formal systems", "approximate_date": "1931"},
                {"philosopher": "Church", "text": "An Unsolvable Problem of Elementary Number Theory", "contribution": "Church-Turing thesis; lambda calculus", "approximate_date": "1936"},
                {"philosopher": "Dijkstra", "text": "Go To Statement Considered Harmful", "contribution": "Structured programming; formal reasoning about programs", "approximate_date": "1968"},
            ],
            "abstraction": [
                {"philosopher": "Parnas", "text": "On the Criteria To Be Used in Decomposing Systems into Modules", "contribution": "Information hiding; modularity as abstraction principle", "approximate_date": "1972"},
                {"philosopher": "Hoare", "text": "An Axiomatic Basis for Computer Programming", "contribution": "Hoare logic; formal specification and verification", "approximate_date": "1969"},
                {"philosopher": "Liskov", "text": "Data Abstraction and Hierarchy", "contribution": "Liskov substitution principle; abstract data types", "approximate_date": "1987"},
            ],
            "model": [
                {"philosopher": "Tarski", "text": "The Concept of Truth in Formalized Languages", "contribution": "Model-theoretic semantics; formal truth definition", "approximate_date": "1933"},
                {"philosopher": "Robinson", "text": "Non-Standard Analysis", "contribution": "Non-standard models of arithmetic", "approximate_date": "1961"},
                {"philosopher": "Lee", "text": "What Are Computer Models?", "contribution": "Philosophical analysis of software models and simulation", "approximate_date": "1973"},
            ],
        }
        return genealogy_map.get(concept, [
            {"philosopher": "Various", "text": "Primary texts", "contribution": f"Historical development of {concept}", "approximate_date": "Various"},
        ])

    @staticmethod
    def _generic_thought_experiments(concept: str) -> list[dict[str, Any]]:
        return [
            {"name": f"Thought experiment about {concept}", "description": f"Consider the concept of {concept} from both analytic and technological perspectives.", "tradition": "analytic", "epistemic_status": "proposed"},
        ]
