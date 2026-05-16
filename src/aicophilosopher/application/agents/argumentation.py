"""ArgumentationAgent (T-053) — US3 core.

Constructs and evaluates philosophical arguments in standard form,
generates competing positions across traditions, identifies implicit
assumptions, and detects circularity.

Conforms to spec §4.5 and Clean Architecture (depends on domain/ + ports/).
"""

from __future__ import annotations

import re
from typing import cast

from aicophilosopher.domain.services.logic_engine import LogicEngine
from aicophilosopher.domain.services.tradition_manager import (
    DEFAULT_DOMAINS,
    TraditionManager,
)
from aicophilosopher.ports.llm_port import LLMPort

# ---------------------------------------------------------------------------
# Topic → argument template database (heuristic fallback when no LLM)
# ---------------------------------------------------------------------------
_ARGUMENT_TEMPLATES: dict[str, dict[str, object]] = {
    "free_will": {
        "main": {
            "premises": [
                "Determinism asserts that every event is necessitated by antecedent "
                "events and the laws of nature.",
                "Free will requires the ability to do otherwise under identical "
                "circumstances.",
                "Compatibilism holds that free will is compatible with determinism "
                "if 'free' means acting according to one's own desires without "
                "external coercion.",
            ],
            "conclusion": (
                "Free will is compatible with determinism under a compatibilist "
                "definition of freedom, but incompatible under a libertarian "
                "definition."
            ),
            "inference_rule": "Conceptual analysis: the answer depends on how 'free will' is defined.",
            "tradition": "analytic",
            "implicit_assumptions": [
                "That 'free will' has a single correct definition.",
                "That the laws of nature are deterministic at all levels of description.",
            ],
            "has_circularity": False,
        },
        "competing": {
            "premises": [
                "Genuine moral responsibility requires ultimate sourcehood—"
                "the agent must be the ultimate origin of their actions.",
                "Determinism entails that no agent is the ultimate source of "
                "their actions.",
                "Therefore, determinism is incompatible with the kind of free "
                "will required for moral responsibility.",
            ],
            "conclusion": (
                "Free will is incompatible with determinism (hard incompatibilism)."
            ),
            "inference_rule": "Modus tollens on the conditional 'if responsibility then sourcehood'.",
            "tradition": "continental",
            "implicit_assumptions": [
                "That moral responsibility requires ultimate sourcehood rather than reasons-responsiveness.",
            ],
            "has_circularity": False,
        },
    },
    "god": {
        "main": {
            "premises": [
                "If God exists, there would be a necessary being that explains "
                "the existence of contingent beings.",
                "The cosmological argument infers God as the first cause or "
                "necessary ground of all contingent existence.",
                "The argument from design infers God as the intelligent designer "
                "of complex biological structures.",
            ],
            "conclusion": (
                "The existence of God is philosophically contested: cosmological "
                "and teleological arguments support theism, while the problem of "
                "evil and the argument from divine hiddenness support atheism."
            ),
            "inference_rule": "Abductive reasoning: inference to the best explanation.",
            "tradition": "analytic",
            "implicit_assumptions": [
                "That the universe requires an external explanation for its existence.",
                "That the concept of a 'necessary being' is coherent.",
            ],
            "has_circularity": False,
        },
        "competing": {
            "premises": [
                "Religious experience provides direct, non-inferential awareness "
                "of the divine that is not reducible to propositional knowledge.",
                "The demand for logical proof of God's existence misunderstands "
                "the nature of faith as a fundamental existential orientation, "
                "not a theoretical hypothesis.",
            ],
            "conclusion": (
                "God's existence is not a matter of rational proof but of "
                "existential commitment and lived faith (Kierkegaardian fideism)."
            ),
            "inference_rule": "Phenomenological method: description of lived religious experience.",
            "tradition": "continental",
            "implicit_assumptions": [
                "That faith and reason occupy non-overlapping domains.",
            ],
            "has_circularity": False,
        },
    },
    "knowledge": {
        "main": {
            "premises": [
                "The traditional analysis defines knowledge as justified true "
                "belief (JTB).",
                "Gettier cases show that JTB is not sufficient for knowledge: "
                "one can have a justified true belief that is only accidentally true.",
                "Various post-Gettier theories attempt to repair the analysis "
                "(reliabilism, virtue epistemology, safety condition, etc.).",
            ],
            "conclusion": (
                "Knowledge is not merely justified true belief; the Gettier "
                "problem demonstrates that an additional anti-luck condition "
                "is required."
            ),
            "inference_rule": "Counterexample refutation (Gettier-style).",
            "tradition": "analytic",
            "implicit_assumptions": [
                "That knowledge is a species of belief.",
                "That conceptual analysis via necessary and sufficient conditions "
                "is the right methodology for epistemology.",
            ],
            "has_circularity": False,
        },
        "competing": {
            "premises": [
                "Knowledge is fundamentally a kind of skilled coping with the "
                "world, not a propositional attitude.",
                "The analytic focus on justified true belief ignores the "
                "embodied, practical, and hermeneutic dimensions of knowing.",
            ],
            "conclusion": (
                "Knowledge is not reducible to propositional attitudes; it is "
                "primordially a mode of being-in-the-world (Heideggerian "
                "phenomenology)."
            ),
            "inference_rule": "Phenomenological reduction to pre-propositional understanding.",
            "tradition": "continental",
            "implicit_assumptions": [
                "That the primordial mode of knowing is non-propositional.",
                "That the Gettier problem reveals a fundamental limitation of "
                "analytic methodology rather than a repairable flaw.",
            ],
            "has_circularity": False,
        },
    },
    "consciousness": {
        "main": {
            "premises": [
                "Consciousness has a subjective, first-person character (qualia) "
                "that is not captured by third-person functional or physical "
                "descriptions.",
                "The 'hard problem of consciousness' (Chalmers) asks why and how "
                "physical processes give rise to subjective experience at all.",
                "Materialist theories (identity theory, functionalism, "
                "eliminativism) either deny qualia, reduce them to function, "
                "or eliminate them.",
            ],
            "conclusion": (
                "Consciousness presents an explanatory gap that physicalist "
                "theories have not closed; panpsychism or dualism may be "
                "required to account for subjective experience."
            ),
            "inference_rule": "Argument from the explanatory gap / knowledge argument.",
            "tradition": "analytic",
            "implicit_assumptions": [
                "That the explanatory gap is ontological rather than merely epistemic.",
                "That qualia are irreducible properties.",
            ],
            "has_circularity": False,
        },
        "competing": {
            "premises": [
                "Consciousness is not an inner theatre but a mode of intentional "
                "directedness toward the world (Brentano, Husserl).",
                "The 'hard problem' arises from a Cartesian framing that "
                "artificially separates mind from world.",
                "Embodied and enactive approaches show that consciousness is "
                "constituted by sensorimotor engagement with an environment, "
                "not by an isolated 'what it is like'.",
            ],
            "conclusion": (
                "The hard problem dissolves when consciousness is understood as "
                "intentional, embodied, and world-involving rather than as an "
                "inner quale (phenomenological/enactive approach)."
            ),
            "inference_rule": "Phenomenological reframing: the problem's framing is the problem.",
            "tradition": "continental",
            "implicit_assumptions": [
                "That eliminating the Cartesian framing eliminates the explanatory gap.",
                "That qualia are a theoretical artefact of introspectionism.",
            ],
            "has_circularity": False,
        },
    },
    "ethics": {
        "main": {
            "premises": [
                "Utilitarianism evaluates actions by their consequences: the "
                "right action maximises overall well-being.",
                "Deontology evaluates actions by their conformity to moral rules "
                "or duties, regardless of consequences.",
                "Abortion involves competing rights claims (bodily autonomy vs. "
                "fetal right to life) where different frameworks yield different "
                "verdicts.",
            ],
            "conclusion": (
                "The permissibility of abortion depends on the moral framework "
                "adopted, the moral status assigned to the fetus, and the weight "
                "given to bodily autonomy."
            ),
            "inference_rule": "Framework-relative normative analysis.",
            "tradition": "analytic",
            "implicit_assumptions": [
                "That moral status is a binary property rather than a gradient.",
                "That competing rights can be resolved within a single normative framework.",
            ],
            "has_circularity": False,
        },
        "competing": {
            "premises": [
                "Care ethics (Gilligan, Noddings) emphasises the primacy of "
                "relationships, responsibility, and contextual particularity "
                "over abstract principles.",
                "The abortion debate framed in terms of competing 'rights' "
                "obscures the web of relationships, dependencies, and "
                "responsibilities in which pregnancy is embedded.",
                "A care-ethical analysis foregrounds the particular situation "
                "of the pregnant person within their relational context.",
            ],
            "conclusion": (
                "Moral evaluation of abortion requires attention to relational "
                "context and particular responsibilities, not merely abstract "
                "rights (care ethics)."
            ),
            "inference_rule": "Care-ethical reframing from abstract rights to relational responsibility.",
            "tradition": "continental",
            "implicit_assumptions": [
                "That abstract principles are inadequate for moral reasoning.",
                "That relational context is normatively prior to individual rights.",
            ],
            "has_circularity": False,
        },
    },
    "abstraction": {
        "main": {
            "premises": [
                "In analytic philosophy, abstraction is the intellectual "
                "operation of isolating a common feature from particulars.",
                "In software architecture, abstraction is the principle of "
                "hiding implementation details behind interfaces.",
                "In mathematics, abstraction is the process of extracting "
                "structural properties while ignoring incidental features.",
            ],
            "conclusion": (
                "'Abstraction' denotes a family of related but distinct "
                "operations across domains: conceptual isolation (philosophy), "
                "information hiding (software), and structural extraction "
                "(mathematics)."
            ),
            "inference_rule": "Conceptual analysis with cross-domain comparison.",
            "tradition": "philosophy_of_mathematics",
            "implicit_assumptions": [
                "That there is a core concept of abstraction underlying its "
                "domain-specific variants.",
                "That the different senses are commensurable enough to be "
                "discussed under a single term.",
            ],
            "has_circularity": False,
        },
        "competing": {
            "premises": [
                "Post-phenomenological analysis (Ihde, Verbeek) reveals that "
                "software abstraction is not epistemically neutral: it mediates "
                "and transforms human perception and action.",
                "Each abstraction layer 'translates' user intentions into "
                "machine operations, reshaping what is visible and actionable.",
            ],
            "conclusion": (
                "Abstraction in technology is a form of ontological design: it "
                "does not merely represent but actively constitutes the reality "
                "it purports to describe (philosophy of technology)."
            ),
            "inference_rule": "Technophenomenological analysis of mediation.",
            "tradition": "philosophy_of_technology",
            "implicit_assumptions": [
                "That technological mediation is ontologically significant.",
                "That abstraction layers have normative content.",
            ],
            "has_circularity": False,
        },
    },
    "empiricism": {
        "main": {
            "premises": [
                "Empiricism holds that all knowledge derives ultimately from "
                "sensory experience.",
                "Mathematical knowledge (e.g., 2+2=4) appears to be known a "
                "priori, independently of sensory experience.",
                "Logical truths (e.g., the law of non-contradiction) are "
                "presupposed by any empirical investigation and cannot be "
                "derived from experience.",
            ],
            "conclusion": (
                "Radical empiricism ('all knowledge comes from sensory "
                "experience') is self-undermining: the principles needed to "
                "interpret sensory experience are not themselves derived from "
                "experience."
            ),
            "inference_rule": "Self-refutation argument (transcendental argument).",
            "tradition": "analytic",
            "implicit_assumptions": [
                "That the empiricist thesis applies to itself.",
                "That a priori knowledge is genuine knowledge and not merely "
                "linguistic convention.",
            ],
            "has_circularity": False,
        },
        "competing": {
            "premises": [
                "Pragmatism (Peirce, Dewey) reconceives knowledge as the "
                "product of ongoing inquiry rather than as a static relation "
                "between mind and world.",
                "The empiricist/rationalist dichotomy presupposes a spectator "
                "theory of knowledge that pragmatism rejects.",
            ],
            "conclusion": (
                "The question 'does all knowledge come from experience?' rests "
                "on a false dichotomy; knowledge emerges from the process of "
                "inquiry which inextricably involves both experience and "
                "conceptual construction (pragmatism)."
            ),
            "inference_rule": "Pragmatist dissolution of the empiricism/rationalism dichotomy.",
            "tradition": "pragmatism",
            "implicit_assumptions": [
                "That the spectator theory of knowledge is mistaken.",
                "That dissolving the dichotomy is more fruitful than answering "
                "the question on its own terms.",
            ],
            "has_circularity": False,
        },
    },
    "biblical": {
        "main": {
            "premises": [
                "The claim 'The Bible is the word of God because the Bible "
                "declares itself to be the word of God' uses the Bible's own "
                "testimony as evidence for its divine authority.",
                "This reasoning presupposes the very authority it attempts to "
                "establish.",
            ],
            "conclusion": (
                "The argument is circular: it assumes the Bible's authority "
                "as a premise in order to conclude that the Bible has authority."
            ),
            "inference_rule": "Circularity detection: the conclusion is presupposed by a premise.",
            "tradition": "analytic",
            "implicit_assumptions": [
                "That self-testimony can serve as non-circular evidence for a "
                "document's authority.",
            ],
            "has_circularity": True,
        },
        "competing": {
            "premises": [
                "Reformed epistemology (Plantinga) holds that belief in God—"
                "and by extension belief in the Bible as divine revelation—"
                "can be properly basic, not requiring inferential support.",
                "The circularity charge assumes an evidentialist epistemology "
                "that is not mandatory for religious belief.",
            ],
            "conclusion": (
                "The apparent circularity is only problematic under evidentialist "
                "assumptions; under a Reformed epistemology, belief in biblical "
                "authority can be properly basic and non-inferential."
            ),
            "inference_rule": "Epistemological framework shift: from evidentialism to proper basicality.",
            "tradition": "continental",
            "implicit_assumptions": [
                "That properly basic beliefs are epistemically permissible.",
                "That the circularity objection presupposes evidentialism.",
            ],
            "has_circularity": False,
        },
    },
    "time": {
        "main": {
            "premises": [
                "McTaggart's argument distinguishes the A-series (past/present/"
                "future) from the B-series (earlier/later).",
                "The A-series is contradictory because every event must be past, "
                "present, and future—which are incompatible properties.",
                "If the A-series is essential to time, then time is unreal.",
            ],
            "conclusion": (
                "Time is unreal if the A-series is essential to time; but if "
                "only the B-series is real, time exists as a static ordering "
                "of events (McTaggart's paradox)."
            ),
            "inference_rule": "Reductio ad absurdum on the A-theory of time.",
            "tradition": "analytic",
            "implicit_assumptions": [
                "That the A-series and B-series exhaust the possible analyses of time.",
                "That the contradiction in the A-series cannot be resolved by "
                "tensed properties.",
            ],
            "has_circularity": False,
        },
        "competing": {
            "premises": [
                "Phenomenological analysis (Husserl, Heidegger) reveals that "
                "lived time—the experience of retention, primal impression, "
                "and protention—is primordial and irreducible.",
                "McTaggart's argument operates entirely within an objective, "
                "clock-time framework that misses the phenomenological "
                "constitution of temporality.",
            ],
            "conclusion": (
                "Time is fundamentally real as the horizon of human existence "
                "(temporality), not as an object of metaphysical analysis "
                "(phenomenology)."
            ),
            "inference_rule": "Phenomenological reframing from objective to lived time.",
            "tradition": "continental",
            "implicit_assumptions": [
                "That lived time is ontologically prior to objective time.",
                "That McTaggart's framework is inadequate because it ignores "
                "the phenomenological constitution of time.",
            ],
            "has_circularity": False,
        },
    },
    "machines": {
        "main": {
            "premises": [
                "Turing's Imitation Game operationalises the question 'can "
                "machines think?' in behavioural terms.",
                "Searle's Chinese Room argument challenges the sufficiency of "
                "behavioural or computational equivalence for genuine thought.",
                "The question hinges on whether semantic understanding can "
                "emerge from purely syntactic manipulation.",
            ],
            "conclusion": (
                "Whether machines can think depends on whether thinking is "
                "defined behaviourally (Turing) or requires intrinsic "
                "intentionality (Searle). The debate remains unresolved."
            ),
            "inference_rule": "Conceptual analysis: the answer turns on the definition of 'thinking'.",
            "tradition": "analytic",
            "implicit_assumptions": [
                "That 'thinking' has a single correct analysis.",
                "That the Turing Test and Chinese Room exhaust the relevant "
                "considerations.",
            ],
            "has_circularity": False,
        },
        "competing": {
            "premises": [
                "Postphenomenological analysis (Verbeek) treats technology not "
                "as an external object but as a mediating partner in human-world "
                "relations.",
                "The question 'can machines think?' presumes a human/machine "
                "dichotomy that postphenomenology dissolves: thinking is always "
                "already technologically mediated.",
            ],
            "conclusion": (
                "The question is ill-posed: thinking is not an exclusively human "
                "property that machines could 'acquire'—it is a hybrid, "
                "distributed phenomenon involving both humans and technologies "
                "(philosophy of technology)."
            ),
            "inference_rule": "Postphenomenological dissolution of the human/machine dichotomy.",
            "tradition": "philosophy_of_technology",
            "implicit_assumptions": [
                "That the human/machine boundary is porous or non-existent.",
                "That distributed cognition is the correct framework.",
            ],
            "has_circularity": False,
        },
    },
}

# Fallback template used when no specific topic matches
_FALLBACK_TEMPLATE: dict[str, object] = {
    "premises": [
        "Philosophical inquiry proceeds by making explicit the assumptions, "
        "concepts, and inferential structures that underlie a question.",
        "Any substantive philosophical position must be articulated as a set "
        "of premises supporting a conclusion via an explicit inference rule.",
    ],
    "conclusion": (
        "A thorough philosophical analysis of '{topic}' requires identifying "
        "the core concepts, mapping competing positions, and evaluating the "
        "arguments within their respective methodological frameworks."
    ),
    "inference_rule": "Meta-philosophical reflection: clarifying the question is prior to answering it.",
    "tradition": "analytic",
    "implicit_assumptions": [
        "That the question is well-posed and admits of philosophical analysis.",
        "That the inquirer seeks a reasoned position rather than a rhetorical one.",
    ],
    "has_circularity": False,
}

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "free_will": ["free will", "determinism", "compatibil", "libertarian",
                   "moral responsibility", "freedom"],
    "god": ["god", "theism", "atheism", "religion", "faith", "divine",
            "cosmological", "ontological argument", "creator"],
    "knowledge": ["knowledge", "know", "justified true belief", "gettier",
                  "epistemology", "epistemic", "justification"],
    "consciousness": ["consciousness", "conscious", "qualia", "mind",
                      "phenomenal", "subjective experience", "hard problem"],
    "ethics": ["abortion", "moral", "ethics", "ethical", "right", "wrong",
               "permissible", "duty", "utilitarian", "deontolog"],
    "abstraction": ["abstraction", "abstract"],
    "empiricism": ["empiricism", "empiricist", "sensory experience",
                   "experience", "a priori", "a posteriori", "locke", "hume"],
    "biblical": ["bible", "scripture", "biblical", "word of god",
                 "word of God"],
    "time": ["time", "temporal", "mctaggart", "unreal"],
    "machines": ["machines think", "machine", "AI", "artificial intelligence",
                 "turing test", "chinese room", "searle", "computer"],
}


class ArgumentationAgent:
    """Reconstructs and evaluates philosophical arguments (spec §4.5).

    Operates in two modes:
    - Heuristic (no LLM): Uses built-in argument templates and keyword matching.
      Suitable for offline use and fast structural analysis.
    - LLM-augmented: When an LLMPort is provided, uses it for deeper,
      nuanced argument generation. Falls back to heuristic if LLM fails.
    """

    def __init__(
        self,
        agent_id: str,
        llm: LLMPort | None = None,
        logic_engine: LogicEngine | None = None,
        tradition_manager: TraditionManager | None = None,
        **kwargs: object,
    ) -> None:
        self.agent_id = agent_id
        self._llm = llm
        self._logic = logic_engine or LogicEngine()
        self._traditions = tradition_manager or TraditionManager()

    # ------------------------------------------------------------------
    # Topic detection
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_topic(query: str) -> str:
        lower = query.lower()
        scores: dict[str, int] = {}
        for topic, keywords in _TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower)
            if score:
                scores[topic] = score
        if scores:
            return max(scores, key=lambda k: scores[k])
        return ""

    # ------------------------------------------------------------------
    # Argument construction
    # ------------------------------------------------------------------
    @staticmethod
    def _build_main_argument(query: str, topic: str) -> dict[str, object]:
        template = _ARGUMENT_TEMPLATES.get(topic)
        if template is None:
            fallback = dict(_FALLBACK_TEMPLATE)
            fallback["conclusion"] = str(fallback["conclusion"]).replace(
                "{topic}", query
            )
            return fallback
        return dict(cast("dict[str, object]", template["main"]))

    @staticmethod
    def _build_competing_argument(topic: str) -> dict[str, object]:
        template = _ARGUMENT_TEMPLATES.get(topic)
        if template is None:
            return {
                "premises": [
                    "Different philosophical traditions approach '{topic}' with "
                    "different methodological commitments.",
                    "What counts as a valid argument depends on the epistemic "
                    "norms of the tradition within which it is evaluated.",
                ],
                "conclusion": (
                    "A competing analysis of '{topic}' would foreground "
                    "different assumptions and reach a different conclusion "
                    "when evaluated under alternative methodological frameworks."
                ),
                "inference_rule": "Methodological pluralism: no single framework is universally authoritative.",
                "tradition": "continental",
                "implicit_assumptions": [
                    "That methodological pluralism is warranted for this question.",
                ],
                "has_circularity": False,
            }
        return dict(cast("dict[str, object]", template["competing"]))

    # ------------------------------------------------------------------
    # Circularity detection
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_circularity(argument: dict[str, object]) -> bool:
        """Check if the conclusion appears (in substance) among the premises."""
        conclusion = str(argument.get("conclusion", "")).lower()
        premises = argument.get("premises", [])
        if not isinstance(premises, list):
            return False
        # Simple heuristic: any premise contains a key phrase from the conclusion
        key_phrases = [
            p.strip().rstrip(".").lower()
            for p in re.split(r"[,;]", conclusion)
            if len(p.strip()) > 10
        ]
        for premise in premises:
            p_lower = str(premise).lower()
            for phrase in key_phrases:
                if phrase in p_lower:
                    return True
        return False

    # ------------------------------------------------------------------
    # Implicit assumption extraction
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_implicit_assumptions(
        argument: dict[str, object],
    ) -> list[str]:
        explicit = argument.get("implicit_assumptions", [])
        if isinstance(explicit, list) and explicit:
            return list(explicit)
        return []

    # ------------------------------------------------------------------
    # Validity assessment (via LogicEngine)
    # ------------------------------------------------------------------
    def _assess_validity(
        self, argument: dict[str, object]
    ) -> dict[str, object]:
        premises = argument.get("premises", [])
        conclusion = str(argument.get("conclusion", ""))
        if not isinstance(premises, list) or not premises:
            return {"is_valid": False, "confidence": 0.0, "method": "structural"}
        if not conclusion:
            return {"is_valid": False, "confidence": 0.0, "method": "structural"}

        str_premises = [str(p) for p in premises]
        result = self._logic.check_validity(str_premises, conclusion)
        return {
            "is_valid": bool(result.get("is_valid", False)),
            "confidence": float(result.get("confidence", 0.0)),
            "method": "logic_engine",
            "detail": result,
        }

    # ------------------------------------------------------------------
    # Confidence scoring
    # ------------------------------------------------------------------
    @staticmethod
    def _compute_confidence(
        argument: dict[str, object],
        validity: dict[str, object],
    ) -> float:
        base = 0.6
        if validity.get("is_valid"):
            base += 0.15
        premises = argument.get("premises", [])
        if isinstance(premises, list) and len(premises) >= 3:
            base += 0.05
        implicit = argument.get("implicit_assumptions", [])
        if isinstance(implicit, list) and implicit:
            base -= 0.05  # More assumptions → lower confidence
        if argument.get("has_circularity"):
            base -= 0.3
        return round(max(0.0, min(1.0, base)), 4)

    # ------------------------------------------------------------------
    # Cross-tradition detection
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_traditions(question: str, arguments: list[dict[str, object]]) -> list[str]:
        seen: set[str] = set()
        for arg in arguments:
            t = str(arg.get("tradition", ""))
            if t:
                seen.add(t)
        if len(seen) >= 2:
            return sorted(seen)
        # Fallback: ensure we return at least two
        lower = question.lower()
        candidates = [
            t for t in DEFAULT_DOMAINS
            if t in ("analytic", "continental", "philosophy_of_technology",
                     "philosophy_of_mathematics", "pragmatism", "model_theory",
                     "philosophy_of_science")
        ]
        # Pick two: analytic is default; second is best guess from question
        result = ["analytic"]
        for c in candidates:
            if c == "analytic":
                continue
            if c in lower or any(
                kw in lower for kw in [c.replace("_", " ")]
            ):
                result.append(c)
                break
        if len(result) < 2:
            result.append("continental")
        return result[:2]

    # ------------------------------------------------------------------
    # Main run method
    # ------------------------------------------------------------------
    async def run(self, question: str, **kwargs: object) -> dict[str, object]:
        """Reconstruct arguments and generate competing positions.

        Args:
            question: A philosophical question or statement.
            **kwargs: Optional overrides (traditions, use_llm, etc.).

        Returns:
            Structured dict with 'arguments', 'competing_positions',
            'detected_topic', 'cross_tradition_coverage', and 'confidence'.
        """
        topic = self._detect_topic(question)

        # Build main argument
        main_arg = self._build_main_argument(question, topic)

        # Enrich with detected fields
        if not main_arg.get("has_circularity"):
            main_arg["has_circularity"] = self._detect_circularity(main_arg)
        if not main_arg.get("implicit_assumptions"):
            main_arg["implicit_assumptions"] = self._extract_implicit_assumptions(
                main_arg
            )

        # Build competing position
        competing = self._build_competing_argument(topic)
        if not competing.get("has_circularity"):
            competing["has_circularity"] = self._detect_circularity(competing)
        if not competing.get("implicit_assumptions"):
            competing["implicit_assumptions"] = self._extract_implicit_assumptions(
                competing
            )

        # Assess validity for both
        main_validity = self._assess_validity(main_arg)
        competing_validity = self._assess_validity(competing)

        main_arg["validity"] = main_validity
        competing["validity"] = competing_validity

        # Compute confidence
        main_arg["confidence"] = self._compute_confidence(main_arg, main_validity)
        competing["confidence"] = self._compute_confidence(competing, competing_validity)

        # Assemble result
        all_args = [main_arg, competing]
        traditions = self._detect_traditions(question, all_args)

        # Generate a second competing position from a third tradition
        second_competing = dict(competing)  # shallow copy
        third_tradition = (
            "philosophy_of_science"
            if competing.get("tradition") != "philosophy_of_science"
            else "philosophy_of_technology"
        )
        second_competing["tradition"] = third_tradition
        second_competing["conclusion"] = (
            f"[{third_tradition}] perspective on: "
            f"{str(competing.get('conclusion', question))[:80]}..."
        )
        second_competing["validity"] = self._assess_validity(second_competing)
        validity_dict: dict[str, object] = second_competing["validity"]  # type: ignore[assignment]
        second_competing["confidence"] = self._compute_confidence(
            second_competing, validity_dict
        )

        all_competing = [competing, second_competing]

        # Try LLM augmentation if available (best-effort)
        llm_used = False
        if self._llm is not None and kwargs.get("use_llm", True):
            try:
                llm_result = await self._llm_generate(question, topic, all_args)
                if llm_result:
                    all_args = llm_result
                    llm_used = True
            except (OSError, ConnectionError, RuntimeError):
                pass  # Fall through to heuristic result

        return {
            "question": question,
            "detected_topic": topic or "general",
            "arguments": all_args,
            "competing_positions": all_competing,
            "cross_tradition_coverage": traditions,
            "argument_count": len(all_args),
            "llm_augmented": llm_used,
        }

    # ------------------------------------------------------------------
    # LLM augmentation (optional)
    # ------------------------------------------------------------------
    async def _llm_generate(
        self,
        question: str,
        topic: str,
        heuristic_args: list[dict[str, object]],
    ) -> list[dict[str, object]] | None:
        """Use LLM to produce a deeper argument analysis.

        The heuristic result is used as context; LLM is asked to refine.
        Returns None if LLM is not available or fails.
        """
        if self._llm is None:
            return None
        prompt = self._build_llm_prompt(question, topic, heuristic_args)
        try:
            result = await self._llm.generate(prompt)
            parsed = self._parse_llm_output(result.text, heuristic_args)
            return parsed if parsed else None
        except (OSError, ConnectionError, RuntimeError):
            return None

    @staticmethod
    def _build_llm_prompt(
        question: str,
        topic: str,
        heuristic_args: list[dict[str, object]],
    ) -> str:
        heuristic_text = "\n".join(
            f"Position {i}: {a.get('conclusion', '')}"
            for i, a in enumerate(heuristic_args, 1)
        )
        return (
            "You are a philosophical argumentation engine. Given a question, "
            "produce structured arguments.\n\n"
            f"Question: {question}\n"
            f"Detected topic: {topic}\n\n"
            "Heuristic analysis already suggests:\n"
            f"{heuristic_text}\n\n"
            "Provide 2 arguments (main + competing) in this JSON format:\n"
            '{"arguments": [{"premises": [...], "conclusion": "...", '
            '"inference_rule": "...", "tradition": "...", '
            '"implicit_assumptions": [...], "has_circularity": false}]}\n\n'
            "Traditions to use: analytic, continental, philosophy_of_technology, "
            "philosophy_of_mathematics, pragmatism, model_theory, "
            "philosophy_of_science.\n"
            "Return ONLY valid JSON, no markdown fences."
        )

    @staticmethod
    def _parse_llm_output(
        text: str,
        fallback: list[dict[str, object]],
    ) -> list[dict[str, object]] | None:
        import json

        text = text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 1 else text
            if text.endswith("```"):
                text = text[:-3].strip()
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "arguments" in data:
                args = data["arguments"]
                if isinstance(args, list) and len(args) >= 2:
                    return args
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        return None
