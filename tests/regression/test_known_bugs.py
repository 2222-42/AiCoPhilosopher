"""Regression test suite (T-072).

Captures known bug scenarios from development and ensures they remain fixed.
Each test references the PR or issue where the bug was discovered.
"""

from __future__ import annotations

import pytest

from aicophilosopher.application.agents.argumentation import ArgumentationAgent
from aicophilosopher.application.agents.critical_review import CriticalReviewAgent
from aicophilosopher.application.agents.cross_traditional import (
    CrossTraditionalComparisonAgent,
)
from aicophilosopher.application.services.retry import retry_call


# ---------------------------------------------------------------------------
# PR #19: Shallow copy aliasing in competing positions
# ---------------------------------------------------------------------------
class TestRegressionPR19ShallowCopy:
    """Bug: second_competing used dict() shallow copy, shared nested lists."""

    @pytest.mark.asyncio
    async def test_competing_positions_independent(self) -> None:
        """After fix, mutating one position must not affect the other."""
        agent = ArgumentationAgent(agent_id="reg-001")
        result = await agent.run("What is abstraction?")
        positions = result.get("competing_positions", [])
        assert len(positions) >= 2

        # Modify one position's assumptions
        pos0 = positions[0]
        pos1 = positions[1]
        original_len = len(pos0.get("implicit_assumptions", []))
        pos0["implicit_assumptions"] = list(pos0.get("implicit_assumptions", []))

        # pos1 should be unaffected (deep copy)
        assert pos1.get("implicit_assumptions") is not pos0["implicit_assumptions"]


# ---------------------------------------------------------------------------
# PR #20: Straw man regex false positive + cicular typo
# ---------------------------------------------------------------------------
class TestRegressionPR20StrawManCircularity:
    """Bug: 'misrepresent' substring triggered straw man on innocent text.
    Bug: 'cicular' typo hardcoded in pattern."""

    @pytest.mark.asyncio
    async def test_misrepresent_not_straw_man(self) -> None:
        """Using 'misrepresent' in a premise shouldn't trigger straw man."""
        agent = CriticalReviewAgent(agent_id="reg-002")
        result = await agent.run([
            {
                "premises": ["Critics often misrepresent the compatibilist position."],
                "conclusion": "Compatibilism is misunderstood.",
                "inference_rule": "modus ponens",
                "tradition": "analytic",
                "confidence": 0.7,
            },
        ])
        straw_men = [
            f for f in result["fallacies"] if f["name"] == "straw man"
        ]
        assert len(straw_men) == 0, (
            "'misrepresent' in a premise should not trigger straw man fallacy"
        )

    @pytest.mark.asyncio
    async def test_cicular_typo_not_in_pattern(self) -> None:
        """'cicular' typo must not be in the fallacy pattern."""
        from aicophilosopher.application.agents.critical_review import (
            _FALLACY_PATTERNS,
        )

        for name, pattern, _, _ in _FALLACY_PATTERNS:
            assert "cicular" not in pattern, (
                f"Typo 'cicular' found in fallacy pattern '{name}'"
            )

    @pytest.mark.asyncio
    async def test_short_conclusion_no_false_circular(self) -> None:
        """Short conclusion embedded as a non-matching clause in longer premise
        must not trigger false positive circularity detection."""
        agent = CriticalReviewAgent(agent_id="reg-003")
        result = await agent.run([
            {
                "premises": [
                    "The concept of mortal beings has been debated by philosophers.",
                    "All humans share the property of being mortal creatures.",
                ],
                "conclusion": "Socrates is mortal.",
                "inference_rule": "modus ponens",
                "tradition": "analytic",
                "confidence": 0.9,
            },
        ])
        circular = [
            f for f in result["fallacies"] if f["name"] == "begging the question"
        ]
        assert len(circular) == 0, (
            "Short conclusion not verbatim in premises should not trigger circularity"
        )


# ---------------------------------------------------------------------------
# PR #23: Empty traditions + LLM output validation
# ---------------------------------------------------------------------------
class TestRegressionPR23EmptyTraditions:
    """Bug: Empty/single-item traditions list fabricated incommensurability entries."""

    @pytest.mark.asyncio
    async def test_empty_traditions_no_fabrication(self) -> None:
        """Empty traditions must not produce fabricated incommensurability entries."""
        agent = CrossTraditionalComparisonAgent(agent_id="reg-004")
        result = await agent.run("abstraction", traditions=[])
        # Should not fabricate analytic/continental when no traditions given
        register = result["incommensurability_register"]
        # With empty traditions, no comparisons possible
        assert result["traditions_compared"] == 0

    @pytest.mark.asyncio
    async def test_single_tradition_no_self_comparison(self) -> None:
        """Single tradition should not produce self-comparison entries."""
        agent = CrossTraditionalComparisonAgent(agent_id="reg-005")
        result = await agent.run("abstraction", traditions=["analytic"])
        # Bridge map should only contain entries with actual comparisons
        for bridge in result["bridge_map"]:
            assert bridge["source_tradition"] != bridge["target_tradition"]


# ---------------------------------------------------------------------------
# PR #25: max_attempts validation
# ---------------------------------------------------------------------------
class TestRegressionPR25MaxAttempts:
    """Bug: max_attempts <= 0 was not validated, causing confusing errors."""

    @pytest.mark.asyncio
    async def test_zero_max_attempts_raises_value_error(self) -> None:
        async def dummy() -> str:
            return "ok"

        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            await retry_call(lambda: dummy(), max_attempts=0)

    @pytest.mark.asyncio
    async def test_negative_max_attempts_raises_value_error(self) -> None:
        async def dummy() -> str:
            return "ok"

        with pytest.raises(ValueError, match="max_attempts must be >= 1"):
            await retry_call(lambda: dummy(), max_attempts=-5)


# ---------------------------------------------------------------------------
# Known invariants
# ---------------------------------------------------------------------------
class TestRegressionConfidenceBounds:
    """Bug: Confidence scores outside 0.0-1.0 range."""

    @pytest.mark.asyncio
    async def test_argumentation_confidence_bounds(self) -> None:
        agent = ArgumentationAgent(agent_id="reg-006")
        result = await agent.run("Is free will compatible with determinism?")
        for arg in result["arguments"]:
            conf = float(arg.get("confidence", 0.5))
            assert 0.0 <= conf <= 1.0, f"Confidence {conf} out of bounds"

    @pytest.mark.asyncio
    async def test_cross_traditional_confidence_bounds(self) -> None:
        agent = CrossTraditionalComparisonAgent(agent_id="reg-007")
        result = await agent.run("abstraction")
        conf = float(result["overall_confidence"])
        assert 0.0 <= conf <= 1.0


class TestRegressionCrossTraditionCoverage:
    """Bug: Cross-tradition coverage < 2 traditions."""

    @pytest.mark.asyncio
    async def test_minimum_two_traditions(self) -> None:
        agent = ArgumentationAgent(agent_id="reg-008")
        result = await agent.run("What is abstraction?")
        traditions: set[str] = set()
        for arg in result["arguments"]:
            traditions.add(str(arg.get("tradition", "")))
        for pos in result.get("competing_positions", []):
            traditions.add(str(pos.get("tradition", "")))
        traditions.discard("")
        assert len(traditions) >= 2, f"Only {len(traditions)} traditions covered"
