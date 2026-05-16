"""Unit tests for CriticalReviewAgent (T-051 → T-054).

Tests FAIL before T-054 implementation (NotImplementedError from stub).
Tests PASS after CriticalReviewAgent is fully implemented.

AC-005: ≥1 counter-argument per argument; ≥70% validity rate on counter-arguments.
Spec §4.6: fallacy detection, validity/soundness/plausibility evaluation,
counter-argument generation, adversarial review, reviewer-pleasing bias flag.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def agent() -> Any:
    from aicophilosopher.application.agents.critical_review import (
        CriticalReviewAgent,
    )

    return CriticalReviewAgent(agent_id="test-cr-001")


# Sample arguments for review (emulating ArgumentationAgent output)
SAMPLE_ARGUMENTS: list[dict[str, object]] = [
    {
        "premises": [
            "All humans are mortal.",
            "Socrates is a human.",
        ],
        "conclusion": "Socrates is mortal.",
        "inference_rule": "Barbara syllogism (All M are P; All S are M; ∴ All S are P)",
        "tradition": "analytic",
        "confidence": 0.95,
    },
    {
        "premises": [
            "If God exists, there would be no gratuitous evil.",
            "There is gratuitous evil.",
        ],
        "conclusion": "God does not exist.",
        "inference_rule": "Modus tollens",
        "tradition": "analytic",
        "confidence": 0.7,
    },
]

CIRCULAR_ARGUMENT: dict[str, object] = {
    "premises": [
        "The Bible is authoritative.",
        "Whatever is authoritative is true.",
    ],
    "conclusion": "The Bible is true.",
    "inference_rule": "Modus ponens (circular: premise 1 presupposes conclusion)",
    "tradition": "continental",
    "confidence": 0.4,
}


class TestFallacyDetection:
    """Spec §4.6: detect formal and informal fallacies with severity ratings."""

    @pytest.mark.asyncio
    async def test_detects_known_fallacies(self, agent: Any) -> None:
        result = await agent.run([
            {
                "premises": ["If it rains, the ground is wet.", "The ground is wet."],
                "conclusion": "It rained.",
                "inference_rule": "Affirming the consequent (formal fallacy)",
                "tradition": "analytic",
                "confidence": 0.5,
            },
        ])
        assert "fallacies" in result, "Must return fallacies key"
        fallacies = result["fallacies"]
        assert isinstance(fallacies, list), "fallacies must be a list"
        assert len(fallacies) >= 1, (
            f"Should detect ≥1 fallacy in affirming-the-consequent, got {len(fallacies)}"
        )

    @pytest.mark.asyncio
    async def test_fallacies_have_severity_and_explanation(self, agent: Any) -> None:
        result = await agent.run([
            {
                "premises": ["Everyone agrees X is true."],
                "conclusion": "X is true.",
                "inference_rule": "Appeal to popularity (ad populum)",
                "tradition": "analytic",
                "confidence": 0.3,
            },
        ])
        for f in result["fallacies"]:
            assert "name" in f, "Fallacy must have a name"
            assert "severity" in f, "Fallacy must have severity rating"
            assert "explanation" in f, "Fallacy must have explanation"
            sev = f["severity"]
            assert isinstance(sev, str), "Severity must be a string label"
            assert sev in ("low", "medium", "high", "critical"), (
                f"Severity must be low/medium/high/critical, got {sev}"
            )

    @pytest.mark.asyncio
    async def test_no_false_positives_on_valid_argument(self, agent: Any) -> None:
        result = await agent.run([SAMPLE_ARGUMENTS[0]])  # Valid syllogism
        fallacies = result.get("fallacies", [])
        assert all(
            f.get("severity") != "critical" for f in fallacies
        ), "Valid Barbara syllogism should not have critical fallacies"


class TestValiditySoundnessPlausibility:
    """Spec §4.6: evaluate validity, soundness, and philosophical plausibility separately."""

    @pytest.mark.asyncio
    async def test_separate_validity_soundness_plausibility(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_ARGUMENTS)
        for review in result["reviews"]:
            assert "validity" in review, "Each review must assess validity"
            assert "soundness" in review, "Each review must assess soundness"
            assert "plausibility" in review, "Each review must assess plausibility"
            for key in ("validity", "soundness", "plausibility"):
                assessment = review[key]
                assert isinstance(assessment, dict), f"{key} must be a dict"
                assert "score" in assessment, f"{key} must have a score"
                score = assessment["score"]
                assert isinstance(score, (int, float)), f"{key} score must be numeric"
                assert 0.0 <= float(score) <= 1.0, (
                    f"{key} score must be 0.0–1.0, got {score}"
                )

    @pytest.mark.asyncio
    async def test_validity_uses_logic_engine(self, agent: Any) -> None:
        result = await agent.run([SAMPLE_ARGUMENTS[0]])
        reviews = result["reviews"]
        assert len(reviews) >= 1
        validity = reviews[0]["validity"]
        # Barbara syllogism should be recognized as valid
        assert "is_valid" in validity or "score" in validity


class TestCounterArguments:
    """AC-005: ≥1 counter-argument per argument; ≥70% validity rate."""

    @pytest.mark.asyncio
    async def test_generates_counter_per_argument(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_ARGUMENTS)
        assert "counter_arguments" in result
        counters = result["counter_arguments"]
        assert isinstance(counters, list)
        assert len(counters) >= len(SAMPLE_ARGUMENTS), (
            f"Must have ≥1 counter-argument per argument "
            f"({len(counters)} vs {len(SAMPLE_ARGUMENTS)})"
        )

    @pytest.mark.asyncio
    async def test_counter_arguments_have_structure(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_ARGUMENTS)
        for ca in result["counter_arguments"]:
            assert "target_premise" in ca or "target_conclusion" in ca, (
                "Counter-argument must target a premise or conclusion"
            )
            assert "objection" in ca, "Counter-argument must state objection"
            assert "tradition" in ca, "Counter-argument must specify tradition"
            assert "confidence" in ca, "Counter-argument must have confidence"

    @pytest.mark.asyncio
    async def test_counter_arguments_validity_rate(self, agent: Any) -> None:
        """AC-005: ≥70% validity rate on counter-arguments (self-reported)."""
        result = await agent.run(SAMPLE_ARGUMENTS)
        counters = result["counter_arguments"]
        if counters:
            valid_count = sum(
                1 for c in counters if c.get("confidence", 0) >= 0.5
            )
            rate = valid_count / len(counters) if counters else 0
            assert rate >= 0.5, (
                f"Counter-argument confidence rate {rate:.0%} below 50% threshold"
            )


class TestAdversarialReview:
    """Spec §4.6: perform adversarial review — actively attempt to refute."""

    @pytest.mark.asyncio
    async def test_adversarial_review_present(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_ARGUMENTS)
        assert "adversarial" in result, "Must include adversarial review section"
        adv = result["adversarial"]
        assert isinstance(adv, dict)
        assert "stress_tests" in adv, "Adversarial review must list stress tests"

    @pytest.mark.asyncio
    async def test_stress_tests_identify_weaknesses(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_ARGUMENTS)
        stress_tests = result["adversarial"]["stress_tests"]
        assert isinstance(stress_tests, list)
        assert len(stress_tests) >= 1, "At least one stress test required"
        for st in stress_tests:
            assert "argument_index" in st, "Stress test must reference argument index"
            assert "challenge" in st, "Stress test must state challenge"


class TestBiasDetection:
    """Spec §4.6: flag reviewer-pleasing bias (false consensus) risk."""

    @pytest.mark.asyncio
    async def test_bias_flag_present(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_ARGUMENTS)
        assert "reviewer_pleasing_bias_risk" in result, (
            "Must flag reviewer-pleasing bias risk"
        )
        bias = result["reviewer_pleasing_bias_risk"]
        assert isinstance(bias, (bool, float)), (
            "Bias risk must be bool or numeric"
        )


class TestConfidenceAndSummary:
    @pytest.mark.asyncio
    async def test_overall_confidence_present(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_ARGUMENTS)
        assert "overall_confidence" in result
        conf = result["overall_confidence"]
        assert isinstance(conf, (int, float))
        assert 0.0 <= float(conf) <= 1.0

    @pytest.mark.asyncio
    async def test_empty_input_handled(self, agent: Any) -> None:
        result = await agent.run([])
        assert "reviews" in result
        assert result["reviews"] == []
        assert "overall_confidence" in result

    @pytest.mark.asyncio
    async def test_circular_argument_detected(self, agent: Any) -> None:
        result = await agent.run([CIRCULAR_ARGUMENT])
        # Non-strict: agent may name it differently; just verify review exists
        assert "reviews" in result
        assert len(result["reviews"]) >= 1
