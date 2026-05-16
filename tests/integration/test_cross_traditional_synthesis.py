"""Integration test for cross-traditional comparison (T-061).

E2E: topic → CrossTraditionalComparisonAgent → bridge map, incommensurability,
tradition profiles, colonization warnings.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def agent() -> Any:
    from aicophilosopher.application.agents.cross_traditional import (
        CrossTraditionalComparisonAgent,
    )

    return CrossTraditionalComparisonAgent(agent_id="int-ct-001")


class TestCrossTraditionalSynthesis:
    @pytest.mark.asyncio
    async def test_abstraction_across_traditions(self, agent: Any) -> None:
        """Full comparison of 'abstraction' across analytic, phil_of_math,
        software_architecture, and phil_of_technology."""
        result = await agent.run("abstraction")
        assert result["bridge_map"]
        assert result["incommensurability_register"]
        assert result["tradition_profiles"]
        assert result["colonization_warnings"]
        assert 0.0 <= result["overall_confidence"] <= 1.0

        # 'abstraction' should have bridges from BRIDGE_NOTES
        bridge_traditions: set[str] = set()
        has_high_confidence_bridge = False
        has_non_contested = False
        for b in result["bridge_map"]:
            bridge_traditions.add(str(b["source_tradition"]))
            bridge_traditions.add(str(b["target_tradition"]))
            if float(b.get("confidence", 0)) >= 0.65:
                has_high_confidence_bridge = True
            if not b.get("contested", True):
                has_non_contested = True
        assert len(bridge_traditions) >= 2, "Must span ≥2 traditions"
        assert has_high_confidence_bridge, (
            "BRIDGE_NOTES lookup should yield high-confidence bridges"
        )
        assert has_non_contested, (
            "Abstraction has well-established cross-traditional bridges"
        )

    @pytest.mark.asyncio
    async def test_truth_incommensurability(self, agent: Any) -> None:
        """Truth should trigger the analytic/continental incommensurability pattern."""
        result = await agent.run("truth")
        register = result["incommensurability_register"]
        # Must reference specific traditions, not just generic fallback
        has_analytic = any(
            "analytic" in str(e.get("explanation", "")).lower()
            for e in register
        )
        has_continental = any(
            "continental" in str(e.get("explanation", "")).lower()
            for e in register
        )
        assert has_analytic and has_continental, (
            "Truth must surface analytic/continental incommensurability "
            "(Tarski vs Heidegger), not just generic fallback"
        )

    @pytest.mark.asyncio
    async def test_unmapped_concept_gets_generic_bridges(self, agent: Any) -> None:
        """A concept not in BRIDGE_NOTES should still receive generic bridges."""
        result = await agent.run("epistemology")
        assert len(result["bridge_map"]) >= 1
        assert result["colonization_warnings"]

    @pytest.mark.asyncio
    async def test_cross_traditional_dead_ends_preserved(self, agent: Any) -> None:
        """Incommensurability register should be preserved as first-class output
        — failed bridges are as important as successful ones (Constitution II)."""
        result = await agent.run("being")
        register = result["incommensurability_register"]
        assert len(register) >= 1, (
            "Incommensurabilities must be preserved (constitution II)"
        )
        for entry in register:
            assert entry.get("explanation"), "Each incommensurability needs explanation"
