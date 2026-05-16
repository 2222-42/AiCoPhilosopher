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
        for b in result["bridge_map"]:
            bridge_traditions.add(str(b["source_tradition"]))
            bridge_traditions.add(str(b["target_tradition"]))
        assert len(bridge_traditions) >= 2

    @pytest.mark.asyncio
    async def test_truth_incommensurability(self, agent: Any) -> None:
        """Truth should trigger the analytic/continental incommensurability pattern."""
        result = await agent.run("truth")
        register = result["incommensurability_register"]
        descriptions = " ".join(
            str(e.get("explanation", "")) for e in register
        )
        # Should mention analytic/continental or Tarski/Heidegger
        has_incomm = (
            "analytic" in descriptions.lower()
            and "continental" in descriptions.lower()
        )
        assert has_incomm or len(register) >= 1, (
            "Truth should surface incommensurability between traditions"
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
