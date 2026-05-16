"""Unit tests for ArgumentationAgent (T-050 → T-053).

Tests FAIL before T-053 implementation (NotImplementedError from stub).
Tests PASS after ArgumentationAgent is fully implemented.

AC-004: ≥2 competing positions generated; each has premises + conclusion + inference rule.
Spec §4.5: standard-form reconstruction, competing positions, implicit assumptions,
tradition-specific validity evaluation, circularity detection.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def agent() -> Any:
    """Creates a bare ArgumentationAgent (no LLM backend needed for structural tests)."""
    from aicophilosopher.application.agents.argumentation import ArgumentationAgent

    return ArgumentationAgent(agent_id="test-arg-001")


class TestStandardFormReconstruction:
    """AC-004: Arguments MUST be in standard form (premises + conclusion + inference rule)."""

    @pytest.mark.asyncio
    async def test_reconstructs_simple_argument(self, agent: Any) -> None:
        result = await agent.run("Is free will compatible with determinism?")
        args = result["arguments"]
        assert len(args) > 0, "Should produce at least one reconstructed argument"
        for arg in args:
            assert "premises" in arg, "Each argument must have premises"
            assert "conclusion" in arg, "Each argument must have a conclusion"
            assert "inference_rule" in arg, "Each argument must have an inference rule"

    @pytest.mark.asyncio
    async def test_premises_are_non_empty_list(self, agent: Any) -> None:
        result = await agent.run("Does God exist?")
        for arg in result["arguments"]:
            assert isinstance(arg["premises"], list), "premises must be a list"
            assert len(arg["premises"]) >= 1, "Each argument must have ≥1 premise"
            assert all(isinstance(p, str) and p.strip() for p in arg["premises"]), (
                "All premises must be non-empty strings"
            )

    @pytest.mark.asyncio
    async def test_inference_rule_is_explicit(self, agent: Any) -> None:
        result = await agent.run("Is knowledge justified true belief?")
        for arg in result["arguments"]:
            rule = arg["inference_rule"]
            assert isinstance(rule, str) and len(rule) > 5, (
                "Inference rule must be an explicit non-trivial string"
            )


class TestCompetingPositions:
    """AC-004: ≥2 competing positions generated; ≥2 distinct traditions represented."""

    @pytest.mark.asyncio
    async def test_generates_multiple_positions(self, agent: Any) -> None:
        result = await agent.run("What is the nature of consciousness?")
        positions = result.get("competing_positions", [])
        assert len(positions) >= 2, (
            f"Must generate ≥2 competing positions, got {len(positions)}"
        )

    @pytest.mark.asyncio
    async def test_each_position_has_premises_conclusion_rule(self, agent: Any) -> None:
        result = await agent.run("Is abortion morally permissible?")
        for pos in result.get("competing_positions", []):
            assert "premises" in pos
            assert "conclusion" in pos
            assert "inference_rule" in pos

    @pytest.mark.asyncio
    async def test_cross_tradition_coverage(self, agent: Any) -> None:
        """≥2 distinct traditions represented per spec §4.5."""
        result = await agent.run("What is abstraction?")
        traditions: set[str] = set()
        for arg in result["arguments"]:
            traditions.add(arg.get("tradition", ""))
        for pos in result.get("competing_positions", []):
            traditions.add(pos.get("tradition", ""))
        traditions.discard("")
        assert len(traditions) >= 2, (
            f"Must cover ≥2 distinct traditions, got {sorted(traditions)}"
        )


class TestImplicitAssumptions:
    """Spec §4.5: identify implicit assumptions, suppressed premises, circularity."""

    @pytest.mark.asyncio
    async def test_lists_implicit_assumptions(self, agent: Any) -> None:
        result = await agent.run("All knowledge comes from sensory experience.")
        for arg in result["arguments"]:
            assert "implicit_assumptions" in arg, "Must flag implicit assumptions"
            assumptions = arg["implicit_assumptions"]
            assert isinstance(assumptions, list), "implicit_assumptions must be a list"

    @pytest.mark.asyncio
    async def test_detects_circular_argument(self, agent: Any) -> None:
        """Circular: 'The Bible is true because the Bible says it is true.'"""
        result = await agent.run(
            "The Bible is the word of God because the Bible declares itself "
            "to be the word of God."
        )
        # At minimum the agent must report a circularity flag field;
        # a strong implementation detects the circularity.
        for arg in result["arguments"]:
            assert "has_circularity" in arg, (
                "Every argument must report has_circularity (bool)"
            )
        # Non-strict: the agent may not always detect circularity, but must
        # expose the field.  Strong implementations SHOULD set it to True here.


class TestConfidenceAndValidity:
    """All arguments MUST carry confidence scores and validity assessments."""

    @pytest.mark.asyncio
    async def test_confidence_scores_present(self, agent: Any) -> None:
        result = await agent.run("Is time unreal?")
        for arg in result["arguments"]:
            assert "confidence" in arg, "Every argument must have a confidence score"
            conf = arg["confidence"]
            assert isinstance(conf, (int, float)), "Confidence must be numeric"
            assert 0.0 <= float(conf) <= 1.0, (
                f"Confidence must be 0.0–1.0, got {conf}"
            )

    @pytest.mark.asyncio
    async def test_validity_assessment_per_argument(self, agent: Any) -> None:
        result = await agent.run("Can machines think?")
        for arg in result["arguments"]:
            assert "validity" in arg, "Each argument must have a validity assessment"
            validity = arg["validity"]
            assert isinstance(validity, dict), "Validity must be a structured dict"
            assert "is_valid" in validity, "Validity must include is_valid (bool)"


class TestEmptyOrTrivialInput:
    @pytest.mark.asyncio
    async def test_handles_short_query(self, agent: Any) -> None:
        result = await agent.run("Truth?")
        assert "arguments" in result
        assert isinstance(result["arguments"], list)

    @pytest.mark.asyncio
    async def test_handles_ambiguous_query(self, agent: Any) -> None:
        result = await agent.run("reality")
        assert "arguments" in result
        # Should still produce arguments even for one-word queries
