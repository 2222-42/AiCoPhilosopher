from typing import Any

from aicophilosopher.domain.services.tradition_manager import TraditionManager

THOUGHT_EXPERIMENTS: dict[str, list[dict[str, Any]]] = {
    "mind": [
        {"name": "Mary's Room", "description": "A neuroscientist raised in a black-and-white room knows all physical facts about color but has never seen color. Upon leaving, does she learn something new?", "tradition": "analytic", "epistemic_status": "widely_accepted as showing qualia are non-physical"},
        {"name": "Zhuangzi's Butterfly Dream", "description": "Zhuangzi dreams he is a butterfly, but upon waking cannot be certain whether he is Zhuangzi who dreamed of being a butterfly or a butterfly dreaming of being Zhuangzi.", "tradition": "daoist", "epistemic_status": "classical; contested interpretations"},
        {"name": "Brain in a Vat", "description": "If your brain is kept alive in a vat and fed electrical impulses identical to those a normal brain receives, how can you know your experiences correspond to reality?", "tradition": "analytic", "epistemic_status": "widely used in epistemology of perception"},
        {"name": "Tibetan Dream Yoga", "description": "Tibetan Buddhist practitioners learn to recognize the dream state as illusory while dreaming, then apply this recognition to waking life to see all phenomena as mind-only.", "tradition": "buddhist", "epistemic_status": "contemplative practice; empirical status pending"},
    ],
    "self": [
        {"name": "Teletransportation Parfit", "description": "If you are destroyed and recreated molecule-for-molecule on Mars, is the resulting person you? Parfit argues psychological continuity matters more than physical continuity.", "tradition": "analytic", "epistemic_status": "widely discussed in personal identity debates"},
        {"name": "No-Self Meditation", "description": "A meditator examines each of the five aggregates (form, feeling, perception, formations, consciousness) and finds no permanent self among them. The Buddha affirms this as liberating insight.", "tradition": "buddhist", "epistemic_status": "empirical claim supported by meditative introspection"},
    ],
    "free will": [
        {"name": "Trolley Problem", "description": "A runaway trolley will kill five people unless you pull a lever diverting it to a track with one person. Is pulling the lever morally permissible?", "tradition": "analytic", "epistemic_status": "widely used in moral psychology; variations include push, footbridge, and loop versions"},
    ],
}


NECESSARY_SUFFICIENT_CONDITIONS: dict[str, dict[str, Any]] = {
    "knowledge": {
        "necessary_conditions": ["belief", "truth", "justification"],
        "sufficient_conditions": ["justified true belief (JTB)", "subject achieves epistemic warrant"],
        "notes": "Gettier cases show JTB may not be sufficient; externalist and virtue-theoretic alternatives exist.",
    },
    "free will": {
        "necessary_conditions": ["alternative possibilities", "capacity for rational deliberation", "absence of coercion"],
        "sufficient_conditions": ["agent-causal power" if "agent-causal" else "self-determined choice consistent with character"],
        "notes": "Compatibilists deny alternative possibilities requirement; libertarians require agent-causal power.",
    },
    "mind": {
        "necessary_conditions": ["consciousness", "intentionality", "subjectivity"],
        "sufficient_conditions": ["organized matter giving rise to phenomenal experience"],
        "notes": "Panpsychism denies that matter is sufficient; functionalism argues any suitably organized system suffices.",
    },
}


DISTINCTIONS: dict[str, list[dict[str, str]]] = {
    "mind": [
        {"concept_a": "qualia", "concept_b": "intentionality", "distinction_type": "phenomenal vs semantic", "description": "Qualia are the felt qualities of experience; intentionality is the aboutness or directedness of mental states.", "tradition": "analytic"},
        {"concept_a": "理 (li)", "concept_b": "氣 (qi)", "distinction_type": "principle vs matter-energy", "description": "Li is the organizing principle or pattern; qi is the vital material substance that li structures.", "tradition": "confucian"},
        {"concept_a": "citta (mind)", "concept_b": "vijnana (consciousness)", "distinction_type": "cognitive faculty vs discriminative awareness", "description": "Citta is the general mind; vijnana is the discriminating consciousness that apprehends objects.", "tradition": "buddhist"},
    ],
    "self": [
        {"concept_a": "de re", "concept_b": "de dicto", "distinction_type": "modal scope", "description": "De re modality attributes a property to a thing itself; de dicto to a proposition or description.", "tradition": "analytic"},
        {"concept_a": "a priori", "concept_b": "a posteriori", "distinction_type": "epistemic dependence", "description": "A priori knowledge is independent of experience; a posteriori depends on empirical evidence.", "tradition": "analytic"},
        {"concept_a": "junzi (君子)", "concept_b": "bodhisattva", "distinction_type": "moral ideal", "description": "Confucian junzi is the morally cultivated person who harmonizes relationships; Buddhist bodhisattva postpones nirvana to liberate all beings.", "tradition": "cross_traditional"},
    ],
    "truth": [
        {"concept_a": "correspondence", "concept_b": "coherence", "distinction_type": "truth theory", "description": "Correspondence truth matches propositions to reality; coherence truth is consistency within a belief system.", "tradition": "analytic"},
        {"concept_a": "satyadvaya (two truths)", "concept_b": "Western correspondence", "distinction_type": "buddhist vs western", "description": "Buddhist two-truths doctrine distinguishes conventional (samvrti) and ultimate (paramartha) truth; Western correspondence treats truth as a single binary relation.", "tradition": "buddhist"},
    ],
}


class ConceptAnalysisAgent:
    def __init__(self, agent_id: str, tradition_manager: TraditionManager | None = None, **kwargs: object) -> None:
        self.agent_id = agent_id
        self.tradition_manager = tradition_manager or TraditionManager()

    async def run(self, concept: str, **kwargs: object) -> dict[str, Any]:
        lower_concept = concept.strip().lower()
        trad_arg = kwargs.get("traditions")
        traditions: list[str] = list(trad_arg) if isinstance(trad_arg, (list, tuple)) else ["analytic", "continental", "buddhist", "confucian", "daoist"]

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
                    "definition": f"The concept of {concept} as understood within {trad} philosophy.",
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
                {"philosopher": "Husserl", "text": "Ideas I", "contribution": "Phenomenological reduction to pure consciousness", "approximate_date": "1913"},
                {"philosopher": "Heidegger", "text": "Being and Time", "contribution": "Dasein as being-in-the-world (rejection of subject-object split)", "approximate_date": "1927"},
                {"philosopher": "Nagarjuna", "text": "Mulamadhyamakakarika", "contribution": "Emptiness of mind and all phenomena", "approximate_date": "150 CE"},
                {"philosopher": "Zhuangzi", "text": "Zhuangzi", "contribution": "Dream argument and transformation of consciousness", "approximate_date": "300 BCE"},
            ],
            "self": [
                {"philosopher": "Locke", "text": "Essay Concerning Human Understanding", "contribution": "Personal identity as psychological continuity", "approximate_date": "1689"},
                {"philosopher": "Hume", "text": "Treatise of Human Nature", "contribution": "Bundle theory of self (no substantial self)", "approximate_date": "1739"},
                {"philosopher": "Parfit", "text": "Reasons and Persons", "contribution": "Teletransportation and psychological connectedness", "approximate_date": "1984"},
                {"philosopher": "Buddha", "text": "Anattalakkhana Sutta", "contribution": "No-self (anatta) doctrine", "approximate_date": "500 BCE"},
            ],
        }
        return genealogy_map.get(concept, [
            {"philosopher": "Various", "text": "Primary texts", "contribution": f"Historical development of {concept}", "approximate_date": "Various"},
        ])

    @staticmethod
    def _generic_thought_experiments(concept: str) -> list[dict[str, Any]]:
        return [
            {"name": f"Thought experiment about {concept}", "description": f"Consider the concept of {concept} from both analytic and phenomenological perspectives.", "tradition": "analytic", "epistemic_status": "proposed"},
        ]
