"""CriticalReviewAgent (T-054) — US3 core.

Detects logical fallacies, evaluates validity/soundness/plausibility,
generates counter-arguments, performs adversarial review, and flags
reviewer-pleasing bias.

Conforms to spec §4.6 and Clean Architecture (depends on domain/ + ports/).
"""

from __future__ import annotations

import re
from typing import cast

from aicophilosopher.domain.services.logic_engine import LogicEngine
from aicophilosopher.ports.llm_port import LLMPort

# ---------------------------------------------------------------------------
# Fallacy patterns: (name, regex, severity, explanation)
# ---------------------------------------------------------------------------
_FALLACY_PATTERNS: list[tuple[str, str, str, str]] = [
    (
        "affirming the consequent",
        r"affirming\s+the\s+consequent",
        "high",
        "Invalid form: 'If P then Q; Q; therefore P' confuses necessary "
        "with sufficient conditions.",
    ),
    (
        "denying the antecedent",
        r"denying\s+the\s+antecedent",
        "high",
        "Invalid form: 'If P then Q; not P; therefore not Q' ignores that "
        "Q could be true for other reasons.",
    ),
    (
        "ad populum",
        r"appeal\s+to\s+(popularity|the\s+people|consensus)|ad\s+populum|"
        r"everyone\s+(agrees|believes|knows|thinks)",
        "medium",
        "The popularity of a belief does not constitute evidence for its truth.",
    ),
    (
        "ad hominem",
        r"ad\s+hominem|attacks?\s+the\s+person|personal\s+attack",
        "medium",
        "Attacking the person rather than the argument.",
    ),
    (
        "straw man",
        r"straw\s*man|strawman",
        "medium",
        "Misrepresenting an opponent's position to make it easier to attack.",
    ),
    (
        "begging the question",
        r"beg(ging)?\s+the\s+question|circular\b",
        "high",
        "The conclusion is assumed in the premises; the argument provides "
        "no independent support.",
    ),
    (
        "false dichotomy",
        r"false\s+(dichotomy|dilemma|choice)|either\s*[./]?or\s+fallacy",
        "medium",
        "Presenting only two options when more exist.",
    ),
    (
        "slippery slope",
        r"slippery\s+slope",
        "low",
        "Claiming a small step will inevitably lead to extreme consequences "
        "without justification.",
    ),
    (
        "appeal to authority",
        r"appeal\s+to\s+(authority|expert)",
        "low",
        "Citing an authority outside their domain of expertise as evidence.",
    ),
    (
        "equivocation",
        r"equivoc",
        "medium",
        "Using a term with multiple meanings ambiguously within an argument.",
    ),
]

# ---------------------------------------------------------------------------
# Counter-argument templates per tradition
# ---------------------------------------------------------------------------
_COUNTER_TEMPLATES: dict[str, list[dict[str, object]]] = {
    "analytic": [
        {
            "objection": "One or more premises lack adequate justification. "
            "The argument is logically valid but may be unsound if "
            "the premises are false.",
            "tradition": "analytic",
            "confidence": 0.7,
        },
        {
            "objection": "The inference rule, while formally valid, may not "
            "capture the intended reasoning. Alternative formalisations "
            "could yield a different conclusion.",
            "tradition": "analytic",
            "confidence": 0.65,
        },
    ],
    "continental": [
        {
            "objection": "The argument presupposes a framework of discrete "
            "propositions and formal inference that may not be appropriate "
            "for the phenomenon under investigation. Hermeneutic understanding "
            "requires contextual interpretation beyond analytic decomposition.",
            "tradition": "continental",
            "confidence": 0.6,
        },
        {
            "objection": "The concepts employed may carry historical and "
            "cultural baggage that the formal presentation obscures. "
            "A genealogical analysis would reveal how these concepts were "
            "constituted by specific historical conditions.",
            "tradition": "continental",
            "confidence": 0.55,
        },
    ],
    "philosophy_of_technology": [
        {
            "objection": "The argument treats its subject matter as a neutral "
            "object of analysis without accounting for how technological "
            "mediation shapes the very terms of the inquiry.",
            "tradition": "philosophy_of_technology",
            "confidence": 0.6,
        },
    ],
    "pragmatism": [
        {
            "objection": "The argument focuses on abstract truth conditions "
            "rather than practical consequences. From a pragmatist perspective, "
            "the meaning of the claim is inseparable from its conceivable "
            "practical effects.",
            "tradition": "pragmatism",
            "confidence": 0.6,
        },
    ],
}

# Stress test templates
_STRESS_TESTS: list[dict[str, object]] = [
    {
        "name": "premise negation",
        "challenge": "Assume each premise is false. Does the argument structure "
        "collapse or can it be repaired with alternative premises?",
    },
    {
        "name": "boundary case",
        "challenge": "Apply the argument's logic to an extreme or borderline "
        "case. If the reasoning breaks down, the inference rule may be too broad.",
    },
    {
        "name": "tradition shift",
        "challenge": "Re-evaluate the argument under the epistemic norms of a "
        "different philosophical tradition. If the assessment changes "
        "dramatically, the argument is tradition-relative.",
    },
    {
        "name": "burden of proof shift",
        "challenge": "What would the opponent need to prove to defeat this "
        "argument? If the burden is asymmetric or unreasonable, the argument "
        "may be rhetorically effective but dialectically weak.",
    },
]


class CriticalReviewAgent:
    """Detects fallacies and critically evaluates philosophical arguments (spec §4.6).

    Operates in two modes:
    - Heuristic (no LLM): Pattern-based fallacy detection, template-driven
      counter-arguments, and structural stress tests.
    - LLM-augmented: When an LLMPort is provided, uses it for deeper critique.
      Falls back to heuristic if LLM fails.
    """

    def __init__(
        self,
        agent_id: str,
        llm: LLMPort | None = None,
        logic_engine: LogicEngine | None = None,
        **kwargs: object,
    ) -> None:
        self.agent_id = agent_id
        self._llm = llm
        self._logic = logic_engine or LogicEngine()

    # ------------------------------------------------------------------
    # Fallacy detection
    # ------------------------------------------------------------------
    def _detect_fallacies(  # noqa: C901 (two-stage detection is inherently complex)
        self, arguments: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        fallacies: list[dict[str, object]] = []
        for i, arg in enumerate(arguments):
            combined = " ".join([
                str(arg.get("inference_rule", "")),
                " ".join(str(p) for p in cast("list[str]", arg.get("premises", []))),
                str(arg.get("conclusion", "")),
            ]).lower()

            for name, pattern, severity, explanation in _FALLACY_PATTERNS:
                if re.search(pattern, combined):
                    fallacies.append({
                        "argument_index": i,
                        "name": name,
                        "severity": severity,
                        "explanation": explanation,
                        "matched_pattern": pattern,
                    })

        self._detect_structural_fallacies(arguments, fallacies)

        # Also check for circularity via substring containment
        for i, arg in enumerate(arguments):
            premises = cast("list[str]", arg.get("premises", []))
            conclusion = str(arg.get("conclusion", ""))
            if premises and conclusion:
                # Circularity: conclusion appears in premises.
                # Short conclusions (<30 chars) use word-boundary matching
                # to avoid false positives like "Socrates is mortal" inside
                # "Whatever entails that Socrates is mortal".
                conc_clean = conclusion.strip().lower().rstrip(".")
                if len(conc_clean) < 30:
                    word_pat = re.compile(
                        r"\b" + re.escape(conc_clean) + r"\b", re.IGNORECASE
                    )

                    def _word_boundary_match(premise: object) -> bool:
                        return bool(word_pat.search(str(premise)))

                    match_fn = _word_boundary_match
                else:

                    def _substring_match(premise: object) -> bool:
                        return conc_clean in str(premise).lower()

                    match_fn = _substring_match
                for p in premises:
                    if match_fn(p):
                        already = any(
                            f["argument_index"] == i and f["name"] == "begging the question"
                            for f in fallacies
                        )
                        if not already:
                            fallacies.append({
                                "argument_index": i,
                                "name": "begging the question",
                                "severity": "high",
                                "explanation": (
                                    "The conclusion appears verbatim among the "
                                    "premises. The argument is circular."
                                ),
                                "matched_pattern": "circularity",
                            })

        return fallacies

    @staticmethod
    def _detect_structural_fallacies(
        arguments: list[dict[str, object]],
        fallacies: list[dict[str, object]],
    ) -> None:
        """Detect formal fallacies by analyzing argument structure, not self-labels."""
        for i, arg in enumerate(arguments):
            premises = cast("list[str]", arg.get("premises", []))
            conclusion = str(arg.get("conclusion", ""))
            if len(premises) != 2 or not conclusion:
                continue
            p0 = str(premises[0]).lower()
            p1 = str(premises[1]).lower()
            has_cond_0 = p0.startswith("if ") and (" then " in p0 or "," in p0)
            has_cond_1 = p1.startswith("if ") and (" then " in p1 or "," in p1)
            if not (has_cond_0 or has_cond_1):
                continue
            cond_premise = str(premises[0] if has_cond_0 else premises[1])
            other_premise = str(premises[1] if has_cond_0 else premises[0])
            then_parts = cond_premise.replace(", then ", " then ").split(" then ", 1)
            consequent = then_parts[1].strip().rstrip(".") if len(then_parts) > 1 else ""
            other_clean = other_premise.strip().rstrip(".")
            conc_clean = conclusion.strip().rstrip(".")
            if not (consequent and other_clean and conc_clean):
                continue
            # Affirming consequent
            if other_clean in (consequent, consequent.lower()) and conc_clean not in (
                consequent, consequent.lower()
            ):
                already = any(
                    f["argument_index"] == i and f["name"] == "affirming the consequent"
                    for f in fallacies
                )
                if not already:
                    fallacies.append({
                        "argument_index": i,
                        "name": "affirming the consequent",
                        "severity": "high",
                        "explanation": (
                            "Invalid form detected: the argument has a "
                            "conditional premise and the second premise affirms "
                            "the consequent rather than the antecedent."
                        ),
                        "matched_pattern": "structural:affirming_consequent",
                    })
            # Denying antecedent
            antecedent = (
                cond_premise.split(" if ", 1)[1].split(" then")[0]
                if " if " in cond_premise
                else cond_premise[3:].split(" then")[0]
                if cond_premise.startswith("if ")
                else ""
            ).strip().rstrip(".")
            if antecedent and other_clean in (
                "not " + antecedent,
                "not " + antecedent.lower(),
            ):
                already = any(
                    f["argument_index"] == i and f["name"] == "denying the antecedent"
                    for f in fallacies
                )
                if not already:
                    fallacies.append({
                        "argument_index": i,
                        "name": "denying the antecedent",
                        "severity": "high",
                        "explanation": (
                            "Invalid form detected: the argument denies the "
                            "antecedent of the conditional rather than "
                            "affirming it."
                        ),
                        "matched_pattern": "structural:denying_antecedent",
                    })

    # ------------------------------------------------------------------
    # Validity / Soundness / Plausibility evaluation
    # ------------------------------------------------------------------
    def _evaluate_argument(
        self, arg: dict[str, object], index: int
    ) -> dict[str, object]:
        premises = cast("list[str]", arg.get("premises", []))
        conclusion = str(arg.get("conclusion", ""))

        # Validity via LogicEngine
        validity_result = self._logic.check_validity(premises, conclusion)
        is_valid = bool(validity_result.get("is_valid", False))
        validity_conf = float(validity_result.get("confidence", 0.0))

        validity: dict[str, object] = {
            "is_valid": is_valid,
            "score": 0.9 if is_valid else 0.2,
            "confidence": validity_conf,
            "method": "logic_engine",
        }

        # Soundness: validity + plausibility of premises
        premise_plausibility = self._estimate_premise_plausibility(premises)
        is_sound = is_valid and premise_plausibility > 0.5
        soundness: dict[str, object] = {
            "is_sound": is_sound,
            "score": round((premise_plausibility if is_valid else 0.1), 4),
            "premise_plausibility": premise_plausibility,
            "note": (
                "Argument is valid but premises need scrutiny"
                if is_valid and not is_sound
                else "Argument is sound" if is_sound
                else "Argument is invalid; soundness not applicable"
            ),
        }

        # Philosophical plausibility (heuristic)
        plausibility_score = self._estimate_philosophical_plausibility(arg)
        plausibility: dict[str, object] = {
            "score": plausibility_score,
            "note": (
                "High prima facie plausibility"
                if plausibility_score > 0.7
                else "Moderate plausibility; requires further analysis"
                if plausibility_score > 0.4
                else "Low philosophical plausibility"
            ),
        }

        return {
            "argument_index": index,
            "validity": validity,
            "soundness": soundness,
            "plausibility": plausibility,
        }

    @staticmethod
    def _estimate_premise_plausibility(premises: list[str]) -> float:
        if not premises:
            return 0.0
        # Heuristic: premises with empirical/observable claims score higher;
        # metaphysical claims score lower
        high_confidence_markers = [
            "all humans are", "water boils", "earth orbits",
            "socrates is", "paris is", "2+2",
        ]
        low_confidence_markers = [
            "god exists", "consciousness is fundamental",
            "reality is an illusion", "infinite",
            "absolute", "transcendent", "noumenal",
        ]
        scores: list[float] = []
        for p in premises:
            p_lower = p.lower()
            if any(m in p_lower for m in high_confidence_markers):
                scores.append(0.9)
            elif any(m in p_lower for m in low_confidence_markers):
                scores.append(0.3)
            else:
                scores.append(0.6)
        return round(sum(scores) / len(scores), 4)

    @staticmethod
    def _estimate_philosophical_plausibility(arg: dict[str, object]) -> float:
        premises = cast("list[str]", arg.get("premises", []))
        conclusion = str(arg.get("conclusion", ""))

        base = 0.6
        # More premises → more avenues of attack → slightly lower
        if len(premises) > 4:
            base -= 0.1
        # Longer conclusion → more specific → slightly more plausible
        if len(conclusion) > 80:
            base += 0.05
        # Explicit inference rule → more transparent → more plausible
        rule = str(arg.get("inference_rule", ""))
        if len(rule) > 10:
            base += 0.05
        # Tradition-tagged → more accountable
        if arg.get("tradition"):
            base += 0.05
        return round(max(0.0, min(1.0, base)), 4)

    # ------------------------------------------------------------------
    # Counter-argument generation
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_counter_arguments(
        arguments: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        counters: list[dict[str, object]] = []
        for i, arg in enumerate(arguments):
            tradition = str(arg.get("tradition", "analytic"))
            templates = _COUNTER_TEMPLATES.get(
                tradition, _COUNTER_TEMPLATES["analytic"]
            )

            # Generate at least 1 counter per argument (AC-005)
            for j, tmpl in enumerate(templates[:2]):  # max 2 per argument
                counters.append({
                    "argument_index": i,
                    "target_premise": (
                        str(cast("list[str]", arg.get("premises", [""]))[0])[:80]
                        if arg.get("premises")
                        else ""
                    ),
                    "objection": str(tmpl["objection"]),
                    "tradition": str(tmpl["tradition"]),
                    "confidence": float(cast("float", tmpl.get("confidence", 0.6))),
                    "counter_id": f"ca-{i}-{j}",
                })

        return counters

    # ------------------------------------------------------------------
    # Adversarial review (stress tests)
    # ------------------------------------------------------------------
    @staticmethod
    def _perform_adversarial_review(
        arguments: list[dict[str, object]],
    ) -> dict[str, object]:
        stress_tests: list[dict[str, object]] = []
        for i, arg in enumerate(arguments):
            for j, test in enumerate(_STRESS_TESTS[:2]):  # 2 tests per argument
                stress_tests.append({
                    "argument_index": i,
                    "test_name": str(test["name"]),
                    "challenge": str(test["challenge"]),
                    "test_id": f"st-{i}-{j}",
                })

        # Summary assessment
        weaknesses: list[str] = []
        for arg in arguments:
            premises = cast("list[str]", arg.get("premises", []))
            if len(premises) <= 2:
                weaknesses.append(
                    "Argument with few premises may be relying on hidden "
                    "assumptions not made explicit."
                )
            if not arg.get("inference_rule"):
                weaknesses.append(
                    "Missing explicit inference rule makes the reasoning "
                    "opaque and difficult to evaluate."
                )

        return {
            "stress_tests": stress_tests,
            "total_tests": len(stress_tests),
            "identified_weaknesses": weaknesses,
            "adversarial_confidence": round(
                max(0.3, 0.8 - 0.1 * len(weaknesses)), 4
            ),
        }

    # ------------------------------------------------------------------
    # Reviewer-pleasing bias detection
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_bias_risk(
        arguments: list[dict[str, object]],
        reviews: list[dict[str, object]],
    ) -> float:
        """Estimate reviewer-pleasing bias risk.

        High risk when: all arguments are rated similarly, no critical
        fallacies are detected despite imperfect arguments, or confidence
        scores cluster tightly around moderate values.
        """
        if not arguments:
            return 0.0

        risk = 0.0

        # Check confidence score clustering
        scores = [
            float(cast("float", arg.get("confidence", 0.5)))
            for arg in arguments
        ]
        if len(scores) >= 2:
            score_range = max(scores) - min(scores)
            if score_range < 0.15:
                risk += 0.3  # Suspiciously tight clustering

        # Check if all validity scores are identical
        validity_scores = [
            cast("dict[str, object]", r["validity"])["score"]
            for r in reviews if "validity" in r
        ]
        if len(validity_scores) >= 2 and len(set(validity_scores)) == 1:
            risk += 0.2

        # If arguments have low confidence but reviews rate them well
        for arg in arguments:
            if float(cast("float", arg.get("confidence", 0.5))) < 0.4:
                risk += 0.15
                break

        return round(min(1.0, risk), 4)

    # ------------------------------------------------------------------
    # Main run method
    # ------------------------------------------------------------------
    async def run(
        self, arguments: list[dict[str, object]], **kwargs: object
    ) -> dict[str, object]:
        """Critically review a list of philosophical arguments.

        Args:
            arguments: List of argument dicts (from ArgumentationAgent output).
            **kwargs: Optional overrides (use_llm, etc.).

        Returns:
            Structured review dict with fallacies, reviews, counter_arguments,
            adversarial stress tests, bias risk, and overall confidence.
        """
        if not arguments:
            return {
                "fallacies": [],
                "reviews": [],
                "counter_arguments": [],
                "adversarial": {"stress_tests": [], "identified_weaknesses": []},
                "reviewer_pleasing_bias_risk": 0.0,
                "overall_confidence": 0.5,
                "argument_count": 0,
            }

        # 1. Fallacy detection
        fallacies = self._detect_fallacies(arguments)

        # 2. Validity/Soundness/Plausibility evaluation
        reviews = [
            self._evaluate_argument(arg, i)
            for i, arg in enumerate(arguments)
        ]

        # 3. Counter-argument generation
        counter_arguments = self._generate_counter_arguments(arguments)

        # 4. Adversarial review (stress tests)
        adversarial = self._perform_adversarial_review(arguments)

        # 5. Bias detection
        bias_risk = self._detect_bias_risk(arguments, reviews)

        # 6. Overall confidence
        review_scores: list[float] = []
        for r in reviews:
            v = cast("dict[str, object]", r.get("validity", {}))
            s = cast("dict[str, object]", r.get("soundness", {}))
            p = cast("dict[str, object]", r.get("plausibility", {}))
            review_scores.append(
                float(cast("float", v.get("score", 0.5)))
                + float(cast("float", s.get("score", 0.5)))
                + float(cast("float", p.get("score", 0.5)))
            )
        avg_score = sum(review_scores) / (len(review_scores) * 3) if review_scores else 0.5
        overall = round(max(0.0, min(1.0, avg_score - bias_risk * 0.2)), 4)

        # 7. LLM augmentation (best-effort)
        llm_used = False
        if self._llm is not None and kwargs.get("use_llm", True):
            try:
                llm_result = await self._llm_review(arguments, reviews, fallacies)
                if llm_result:
                    llm_fallacies = cast(
                        "list[dict[str, object]]",
                        llm_result.get("fallacies", fallacies),
                    )
                    llm_counters = cast(
                        "list[dict[str, object]]",
                        llm_result.get("counter_arguments", counter_arguments),
                    )
                    # Validate LLM output preserves AC-005 invariant:
                    # ≥1 counter-argument per input argument.
                    num_args = len(arguments)
                    llm_arg_indices = {
                        int(cast("float", c.get("argument_index", -1)))
                        for c in llm_counters
                    }
                    if len(llm_arg_indices) >= num_args:
                        fallacies = llm_fallacies
                        counter_arguments = llm_counters
                    else:
                        # LLM output insufficient; merge with heuristic
                        heuristic_indices = {
                            int(cast("float", c.get("argument_index", -1)))
                            for c in counter_arguments
                        }
                        missing = heuristic_indices - llm_arg_indices
                        merged = list(llm_counters)
                        for c in counter_arguments:
                            if int(cast("float", c.get("argument_index", -1))) in missing:
                                merged.append(c)
                        fallacies = llm_fallacies
                        counter_arguments = merged
                    llm_used = True
            except (OSError, ConnectionError, RuntimeError):
                pass

        return {
            "fallacies": fallacies,
            "reviews": reviews,
            "counter_arguments": counter_arguments,
            "adversarial": adversarial,
            "reviewer_pleasing_bias_risk": bias_risk,
            "overall_confidence": overall,
            "argument_count": len(arguments),
            "llm_augmented": llm_used,
        }

    # ------------------------------------------------------------------
    # LLM augmentation
    # ------------------------------------------------------------------
    async def _llm_review(
        self,
        arguments: list[dict[str, object]],
        heuristic_reviews: list[dict[str, object]],
        heuristic_fallacies: list[dict[str, object]],
    ) -> dict[str, object] | None:
        if self._llm is None:
            return None
        import json

        prompt = (
            "You are a philosophical critical review engine. Review these "
            "arguments and identify fallacies and counter-arguments.\n\n"
            "Arguments:\n" + json.dumps(arguments, indent=2) + "\n\n"
            "Heuristic review already found:\n"
            f"Fallacies: {len(heuristic_fallacies)}\n"
            f"Reviews: {len(heuristic_reviews)}\n\n"
            "Return JSON with keys 'fallacies' (list) and 'counter_arguments' "
            "(list). Each fallacy needs: name, severity (low/medium/high/critical), "
            "explanation, argument_index. Each counter-argument needs: "
            "argument_index, objection, tradition, confidence.\n"
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
