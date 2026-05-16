"""CrossTraditionalComparisonAgent (T-062) — US4 core.

Compares philosophical positions across traditions, identifies bridge concepts
and incommensurabilities, evaluates within native frameworks, and avoids
category colonization.

Conforms to spec §4.4 and Clean Architecture (depends on domain/ + ports/).
"""

from __future__ import annotations

from typing import cast

from aicophilosopher.domain.data.bridge_notes import BRIDGE_NOTES
from aicophilosopher.domain.services.tradition_manager import (
    DEFAULT_DOMAINS,
    TraditionManager,
)
from aicophilosopher.ports.llm_port import LLMPort

# Incommensurability patterns: concept pairs that resist reduction
_INCOMMENSURABILITY_PATTERNS: dict[str, list[dict[str, object]]] = {
    "truth": [
        {
            "tradition_a": "analytic",
            "tradition_b": "continental",
            "explanation": (
                "Analytic truth (Tarskian correspondence) and continental truth "
                "(Heideggerian aletheia/unconcealment) are not merely different "
                "theories of the same thing — they presuppose incompatible "
                "accounts of what it means for something to be true."
            ),
            "severity": "high",
        },
    ],
    "being": [
        {
            "tradition_a": "analytic",
            "tradition_b": "continental",
            "explanation": (
                "Analytic ontology typically treats 'being' as a quantifier "
                "(∃x), while continental ontology (Heidegger) treats Being "
                "(Sein) as the fundamental horizon within which entities appear. "
                "These are not commensurable: the analytic quantifier approach "
                "presupposes the very ontic attitude that phenomenology suspends."
            ),
            "severity": "high",
        },
    ],
    "consciousness": [
        {
            "tradition_a": "analytic",
            "tradition_b": "continental",
            "explanation": (
                "Analytic treatments of consciousness focus on qualia and the "
                "hard problem (Chalmers), while phenomenological treatments "
                "(Husserl, Merleau-Ponty) treat consciousness as intentionality "
                "— always consciousness-of-something. These frameworks ask "
                "different questions and resist reduction to each other."
            ),
            "severity": "medium",
        },
    ],
    "abstraction": [
        {
            "tradition_a": "philosophy_of_mathematics",
            "tradition_b": "software_architecture",
            "explanation": (
                "Mathematical abstraction discovers formal structure; software "
                "abstraction designs interfaces. Conflating the two risks "
                "treating design choices as mathematical necessities — a form "
                "of category colonization."
            ),
            "severity": "medium",
        },
    ],
}

# Colonization warnings: when a concept from tradition A is imposed on B
_COLONIZATION_WARNINGS: dict[str, str] = {
    "abstraction:software_architecture→philosophy_of_mathematics": (
        "Software abstraction layers (interfaces, encapsulation) are design "
        "artifacts with engineering trade-offs. Treating them as instances of "
        "mathematical abstraction imposes formal purity criteria that are "
        "inappropriate for engineered systems."
    ),
    "abstraction:philosophy_of_mathematics→software_architecture": (
        "Mathematical abstraction (structural extraction) is a discovery/"
        "description relation. Applying it to software interfaces conflates "
        "ontological discovery with design decision."
    ),
    "model:philosophy_of_science→software_architecture": (
        "Scientific models aim at empirical adequacy (isomorphism with target "
        "systems). Software models aim at executable specification (behavioural "
        "correctness). The normative criteria differ fundamentally."
    ),
    "model:software_architecture→philosophy_of_science": (
        "Software models are prescriptive specifications, not descriptive "
        "representations. Treating them as scientific models ignores the "
        "engineering constraints and evaluative criteria specific to software."
    ),
}


class CrossTraditionalComparisonAgent:
    """Compares philosophical concepts across traditions (spec §4.4).

    Operates in two modes:
    - Heuristic: Uses BRIDGE_NOTES, TraditionManager profiles, and built-in
      incommensurability/colonization patterns.
    - LLM-augmented: When an LLMPort is provided, enriches the comparison.
    """

    def __init__(
        self,
        agent_id: str,
        llm: LLMPort | None = None,
        tradition_manager: TraditionManager | None = None,
        **kwargs: object,
    ) -> None:
        self.agent_id = agent_id
        self._llm = llm
        self._traditions = tradition_manager or TraditionManager()

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------
    async def run(self, topic: str, **kwargs: object) -> dict[str, object]:
        """Compare a concept across philosophical traditions.

        Args:
            topic: The concept to compare (e.g., 'abstraction', 'truth').
            **kwargs: Optional traditions list, use_llm flag.

        Returns:
            Dict with bridge_map, incommensurability_register,
            tradition_profiles, colonization_warnings, overall_confidence.
        """
        raw_traditions = kwargs.get("traditions")
        traditions: list[str] = (
            list(raw_traditions)
            if isinstance(raw_traditions, (list, tuple))
            else DEFAULT_DOMAINS
        )

        # 1. Build bridge map from BRIDGE_NOTES + TraditionManager
        bridge_map = self._build_bridge_map(topic, traditions)

        # 2. Incommensurability register
        incomm_register = self._build_incommensurability_register(topic, traditions)

        # 3. Tradition profiles
        profiles = self._build_tradition_profiles(traditions)

        # 4. Colonization warnings
        warnings = self._build_colonization_warnings(topic, traditions)

        # 5. Overall confidence (initial; may be recomputed after LLM)
        confidence = self._compute_overall_confidence(
            bridge_map, incomm_register, warnings
        )

        # 6. LLM augmentation (best-effort, with output validation)
        llm_used = False
        if self._llm is not None and kwargs.get("use_llm", True):
            try:
                llm_result = await self._llm_compare(topic, traditions, bridge_map)
                if llm_result:
                    raw_bridges = llm_result.get("bridge_map")
                    raw_incomm = llm_result.get("incommensurability_register")
                    # Validate shape before accepting
                    if isinstance(raw_bridges, list) and all(
                        isinstance(b, dict) and "source_tradition" in b
                        for b in raw_bridges
                    ):
                        bridge_map = cast(
                            "list[dict[str, object]]", raw_bridges
                        )
                    if isinstance(raw_incomm, list) and all(
                        isinstance(e, dict) and "explanation" in e
                        for e in raw_incomm
                    ):
                        incomm_register = cast(
                            "list[dict[str, object]]", raw_incomm
                        )
                    llm_used = True
                    # Recompute confidence with potentially updated data
                    confidence = self._compute_overall_confidence(
                        bridge_map, incomm_register, warnings
                    )
            except (OSError, ConnectionError, RuntimeError):
                pass

        return {
            "topic": topic,
            "bridge_map": bridge_map,
            "incommensurability_register": incomm_register,
            "tradition_profiles": profiles,
            "colonization_warnings": warnings,
            "overall_confidence": confidence,
            "traditions_compared": len(traditions),
            "llm_augmented": llm_used,
        }

    # ------------------------------------------------------------------
    # Bridge map
    # ------------------------------------------------------------------
    @staticmethod
    def _build_bridge_map(
        topic: str, traditions: list[str]
    ) -> list[dict[str, object]]:
        bridges: list[dict[str, object]] = []
        lower_topic = topic.lower().strip()

        # Look up in BRIDGE_NOTES
        concept_notes = BRIDGE_NOTES.get(lower_topic, {})
        for cross_key, note_text in concept_notes.items():
            parts = cross_key.split("→")
            if len(parts) == 2:
                src, tgt = parts[0], parts[1]
                if src in traditions and tgt in traditions:
                    bridges.append({
                        "source_tradition": src,
                        "target_tradition": tgt,
                        "concept": topic,
                        "note": note_text,
                        "confidence": 0.7,
                        "contested": False,
                    })

        # Also check TraditionManager for bridge_warnings (negative bridges)
        # These become low-confidence or contested entries
        if not bridges:
            # Generate generic bridges for all tradition pairs
            for i in range(len(traditions)):
                for j in range(i + 1, len(traditions)):
                    bridges.append({
                        "source_tradition": traditions[i],
                        "target_tradition": traditions[j],
                        "concept": topic,
                        "note": (
                            f"Comparing '{topic}' between "
                            f"{traditions[i].replace('_', ' ')} and "
                            f"{traditions[j].replace('_', ' ')} requires "
                            f"careful methodological alignment."
                        ),
                        "confidence": 0.5,
                        "contested": True,
                    })

        return bridges

    # ------------------------------------------------------------------
    # Incommensurability register
    # ------------------------------------------------------------------
    @staticmethod
    def _build_incommensurability_register(
        topic: str, traditions: list[str]
    ) -> list[dict[str, object]]:
        register: list[dict[str, object]] = []
        lower_topic = topic.lower().strip()

        patterns = _INCOMMENSURABILITY_PATTERNS.get(lower_topic, [])
        for pat in patterns:
            if pat["tradition_a"] in traditions and pat["tradition_b"] in traditions:
                register.append(dict(pat))

        if not register and len(traditions) >= 2:
            # Generic incommensurability for any multi-tradition comparison
            register.append({
                "tradition_a": traditions[0] if traditions else "analytic",
                "tradition_b": (
                    traditions[1] if len(traditions) > 1 else "continental"
                ),
                "explanation": (
                    f"The concept '{topic}' may carry different meanings "
                    f"across traditions. Direct comparison without "
                    f"methodological translation risks equivocation."
                ),
                "severity": "low",
            })

        return register

    # ------------------------------------------------------------------
    # Tradition profiles
    # ------------------------------------------------------------------
    def _build_tradition_profiles(
        self, traditions: list[str]
    ) -> list[dict[str, object]]:
        profiles: list[dict[str, object]] = []
        for trad in traditions:
            profile = self._traditions.get_tradition_profile(trad)
            if profile:
                profiles.append({
                    "tradition": trad,
                    "key_assumptions": profile.get("assumptions", []),
                    "methodological_norms": profile.get("norms", []),
                    "evaluative_criteria": profile.get("criteria", []),
                })
            else:
                # Fallback: minimal profile
                profiles.append({
                    "tradition": trad,
                    "key_assumptions": [
                        f"{trad.replace('_', ' ').title()} has its own "
                        f"methodological commitments and norms."
                    ],
                    "methodological_norms": [
                        "Arguments evaluated within native framework."
                    ],
                    "evaluative_criteria": [
                        "Internal coherence and explanatory power."
                    ],
                })
        return profiles

    # ------------------------------------------------------------------
    # Colonization warnings
    # ------------------------------------------------------------------
    @staticmethod
    def _build_colonization_warnings(
        topic: str, traditions: list[str]
    ) -> list[dict[str, object]]:
        warnings: list[dict[str, object]] = []
        lower_topic = topic.lower().strip()

        for i in range(len(traditions)):
            for j in range(len(traditions)):
                if i == j:
                    continue
                key = f"{lower_topic}:{traditions[i]}→{traditions[j]}"
                if key in _COLONIZATION_WARNINGS:
                    warnings.append({
                        "source_tradition": traditions[i],
                        "target_tradition": traditions[j],
                        "concept": topic,
                        "warning": _COLONIZATION_WARNINGS[key],
                        "severity": "medium",
                    })

        if not warnings and len(traditions) >= 2:
            warnings.append({
                "source_tradition": traditions[0],
                "target_tradition": traditions[1],
                "concept": topic,
                "warning": (
                    f"When comparing '{topic}' across traditions, ensure "
                    f"categories from {traditions[0].replace('_', ' ')} "
                    f"are not imposed on {traditions[1].replace('_', ' ')} "
                    f"without explicit methodological justification."
                ),
                "severity": "low",
            })

        return warnings

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_overall_confidence(
        bridges: list[dict[str, object]],
        incomm: list[dict[str, object]],
        warnings: list[dict[str, object]],
    ) -> float:
        base = 0.6
        if bridges:
            avg_bridge_conf = sum(
                float(cast("float", b.get("confidence", 0.5)))
                for b in bridges
            ) / len(bridges)
            base = avg_bridge_conf
        # High-severity incommensurabilities reduce confidence
        high_incomm = sum(
            1 for i in incomm if i.get("severity") == "high"
        )
        base -= high_incomm * 0.1
        # Warnings also reduce
        base -= len(warnings) * 0.03
        return round(max(0.0, min(1.0, base)), 4)

    # ------------------------------------------------------------------
    # LLM augmentation
    # ------------------------------------------------------------------
    async def _llm_compare(
        self,
        topic: str,
        traditions: list[str],
        heuristic_bridges: list[dict[str, object]],
    ) -> dict[str, object] | None:
        if self._llm is None:
            return None
        import json

        prompt = (
            f"Compare the concept '{topic}' across these philosophical "
            f"traditions: {', '.join(traditions)}.\n\n"
            "Heuristic analysis already found:\n"
            + json.dumps(heuristic_bridges[:3], indent=2)
            + "\n\nReturn JSON with 'bridge_map' (list of bridges with "
            "source_tradition, target_tradition, concept, note, confidence) "
            "and 'incommensurability_register' (list with tradition_a, "
            "tradition_b, explanation, severity).\n"
            "Return ONLY valid JSON, no markdown fences."
        )
        try:
            result = await self._llm.generate(prompt)
            text = result.text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:]) if len(lines) > 1 else text
                if text.endswith("```"):
                    text = text[:-3].strip()
            data = json.loads(text)
            if isinstance(data, dict):
                return cast("dict[str, object]", data)
        except (json.JSONDecodeError, OSError, ConnectionError, RuntimeError):
            pass
        return None
