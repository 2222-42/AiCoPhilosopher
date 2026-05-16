"""Constitution verification suite (T-073, T-074).

Verifies:
  - T-073 (Principle I): Core features operational without LLM/network.
  - T-074 (Principle II): Mandatory confidence scores, dead-end preservation,
    cross-tradition coverage, hypothesis history.
"""

from __future__ import annotations

import pytest

from aicophilosopher.application.agents.argumentation import ArgumentationAgent
from aicophilosopher.application.agents.critical_review import CriticalReviewAgent
from aicophilosopher.application.agents.cross_traditional import (
    CrossTraditionalComparisonAgent,
)
from aicophilosopher.application.agents.synthesis import SynthesisAgent

# ---------------------------------------------------------------------------
# T-073 — Constitution Principle I: Core Independence & Offline Operation
# ---------------------------------------------------------------------------


class TestConstitutionIOfflineOperation:
    """All core agents must work without LLM, network, or external layers."""

    @pytest.mark.asyncio
    async def test_argumentation_offline(self) -> None:
        agent = ArgumentationAgent(agent_id="test", llm=None)
        result = await agent.run("Is free will compatible with determinism?")
        assert result["arguments"]
        assert result["competing_positions"]
        assert result["argument_count"] >= 2

    @pytest.mark.asyncio
    async def test_critical_review_offline(self) -> None:
        agent = CriticalReviewAgent(agent_id="test", llm=None)
        result = await agent.run([
            {
                "premises": ["If P then Q", "Q"],
                "conclusion": "P",
                "inference_rule": "Affirming the consequent",
                "tradition": "analytic",
                "confidence": 0.3,
            },
        ])
        assert result["reviews"]
        assert result["fallacies"]

    @pytest.mark.asyncio
    async def test_cross_traditional_offline(self) -> None:
        agent = CrossTraditionalComparisonAgent(agent_id="test", llm=None)
        result = await agent.run("abstraction")
        assert result["bridge_map"]
        assert result["tradition_profiles"]

    @pytest.mark.asyncio
    async def test_synthesis_offline(self) -> None:
        agent = SynthesisAgent(agent_id="test", llm=None)
        result = await agent.run([
            {
                "workstream_id": "ws-1",
                "type": "argumentation",
                "results": "## Argument\nFree will is compatible with determinism.",
                "confidence": 0.7,
                "claims": [{"text": "Compatibilism is viable", "confidence": 0.8,
                            "origin": "argument_reconstruction"}],
            },
        ])
        assert result["synthesized_document"]
        assert result["synthesis_confidence"] is not None


# ---------------------------------------------------------------------------
# T-074 — Constitution Principle II: Intellectual Honesty
# ---------------------------------------------------------------------------


class TestConstitutionIIIntellectualHonesty:
    """Every claim must carry confidence, dead ends preserved, cross-tradition."""

    @pytest.mark.asyncio
    async def test_all_arguments_have_confidence(self) -> None:
        agent = ArgumentationAgent(agent_id="test")
        result = await agent.run("Does God exist?")
        for arg in result["arguments"]:
            assert "confidence" in arg, f"Argument missing confidence: {arg.get('conclusion', '?')}"
            assert 0.0 <= float(arg["confidence"]) <= 1.0
        for pos in result["competing_positions"]:
            assert "confidence" in pos
            assert 0.0 <= float(pos["confidence"]) <= 1.0

    @pytest.mark.asyncio
    async def test_fallacies_have_severity(self) -> None:
        agent = CriticalReviewAgent(agent_id="test")
        result = await agent.run([
            {
                "premises": ["Everyone agrees X is true."],
                "conclusion": "X is true.",
                "inference_rule": "ad populum",
                "tradition": "analytic",
                "confidence": 0.3,
            },
        ])
        for f in result["fallacies"]:
            assert "severity" in f
            assert f["severity"] in ("low", "medium", "high", "critical")

    @pytest.mark.asyncio
    async def test_cross_tradition_coverage(self) -> None:
        agent = ArgumentationAgent(agent_id="test")
        result = await agent.run("What is abstraction?")
        traditions: set[str] = set()
        for arg in result["arguments"]:
            traditions.add(str(arg.get("tradition", "")))
        for pos in result["competing_positions"]:
            traditions.add(str(pos.get("tradition", "")))
        traditions.discard("")
        assert len(traditions) >= 2, (
            f"Must cover ≥2 traditions (constitution II cross-tradition mandate), "
            f"got {sorted(traditions)}"
        )

    @pytest.mark.asyncio
    async def test_incommensurability_preserved(self) -> None:
        """Failed bridges and incommensurabilities must be preserved (Constitution II)."""
        agent = CrossTraditionalComparisonAgent(agent_id="test")
        result = await agent.run("being")
        register = result["incommensurability_register"]
        assert len(register) >= 1, (
            "Incommensurability register must preserve dead ends"
        )

    @pytest.mark.asyncio
    async def test_synthesis_has_confidence(self) -> None:
        agent = SynthesisAgent(agent_id="test")
        result = await agent.run([
            {
                "workstream_id": "ws-1",
                "type": "argumentation",
                "results": "Some results",
                "confidence": 0.6,
                "claims": [],
            },
        ])
        assert "synthesis_confidence" in result
        conf = result["synthesis_confidence"]
        assert 0.0 <= float(conf) <= 1.0
