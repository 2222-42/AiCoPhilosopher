"""Unit tests for CrossTraditionalComparisonAgent (T-060 → T-062).

Spec §4.4: identify functional analogues, flag incommensurabilities,
evaluate within native frameworks, avoid category colonization.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def agent() -> Any:
    from aicophilosopher.application.agents.cross_traditional import (
        CrossTraditionalComparisonAgent,
    )

    return CrossTraditionalComparisonAgent(agent_id="test-ct-001")


class TestBridgeIdentification:
    """Identify functional analogues of concepts across traditions."""

    @pytest.mark.asyncio
    async def test_bridge_map_present(self, agent: Any) -> None:
        result = await agent.run("abstraction")
        assert "bridge_map" in result
        bridges = result["bridge_map"]
        assert isinstance(bridges, list)

    @pytest.mark.asyncio
    async def test_bridge_has_valid_edges(self, agent: Any) -> None:
        """Each bridge entry has source, target, and concept."""
        result = await agent.run("model")
        for bridge in result["bridge_map"]:
            assert "source_tradition" in bridge, "Bridge must name source tradition"
            assert "target_tradition" in bridge, "Bridge must name target tradition"
            assert "concept" in bridge, "Bridge must name the bridging concept"
            assert bridge["source_tradition"] != bridge["target_tradition"], (
                "Bridge must connect distinct traditions"
            )

    @pytest.mark.asyncio
    async def test_bridges_have_confidence(self, agent: Any) -> None:
        result = await agent.run("abstraction")
        for bridge in result["bridge_map"]:
            assert "confidence" in bridge
            conf = bridge["confidence"]
            assert 0.0 <= float(conf) <= 1.0


class TestIncommensurability:
    """Flag where no satisfactory bridge exists."""

    @pytest.mark.asyncio
    async def test_incommensurability_register_present(self, agent: Any) -> None:
        result = await agent.run("truth")
        assert "incommensurability_register" in result
        reg = result["incommensurability_register"]
        assert isinstance(reg, list)

    @pytest.mark.asyncio
    async def test_register_flags_contested_mappings(self, agent: Any) -> None:
        result = await agent.run("being")
        reg = result["incommensurability_register"]
        for entry in reg:
            assert "traditions" in entry or "tradition_a" in entry, (
                "Must identify which traditions are incommensurable"
            )
            assert "explanation" in entry, (
                "Must explain why incommensurability exists"
            )


class TestTraditionProfiles:
    """Tradition profiles describe assumptions, norms, and criteria."""

    @pytest.mark.asyncio
    async def test_profiles_returned(self, agent: Any) -> None:
        result = await agent.run("consciousness")
        assert "tradition_profiles" in result
        profiles = result["tradition_profiles"]
        assert isinstance(profiles, list)
        assert len(profiles) >= 2, (
            f"Must profile ≥2 traditions, got {len(profiles)}"
        )

    @pytest.mark.asyncio
    async def test_profiles_have_key_fields(self, agent: Any) -> None:
        result = await agent.run("consciousness")
        for profile in result["tradition_profiles"]:
            assert "tradition" in profile
            assert "key_assumptions" in profile or "assumptions" in profile
            assert "methodological_norms" in profile or "methods" in profile


class TestColonizationPrevention:
    """Avoid forcing one tradition's categories onto another."""

    @pytest.mark.asyncio
    async def test_colonization_warnings_present(self, agent: Any) -> None:
        result = await agent.run("abstraction")
        assert "colonization_warnings" in result
        warnings = result["colonization_warnings"]
        assert isinstance(warnings, list)

    @pytest.mark.asyncio
    async def test_no_forced_equivalence(self, agent: Any) -> None:
        """Bridge map should not claim identity where mapping is contested."""
        result = await agent.run("truth")
        for bridge in result["bridge_map"]:
            if "contested" in str(bridge.get("note", "")).lower():
                assert bridge.get("confidence", 1.0) < 0.8, (
                    "Contested bridges must have reduced confidence"
                )


class TestConfidenceAndSummary:
    @pytest.mark.asyncio
    async def test_overall_confidence_present(self, agent: Any) -> None:
        result = await agent.run("abstraction")
        assert "overall_confidence" in result
        assert 0.0 <= float(result["overall_confidence"]) <= 1.0

    @pytest.mark.asyncio
    async def test_cross_traditional_comparison_structure(self, agent: Any) -> None:
        result = await agent.run("computation")
        required_keys = {
            "bridge_map", "incommensurability_register",
            "tradition_profiles", "colonization_warnings",
        }
        missing = required_keys - set(result.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    @pytest.mark.asyncio
    async def test_single_word_query(self, agent: Any) -> None:
        result = await agent.run("proof")
        assert "bridge_map" in result
        assert isinstance(result["bridge_map"], list)
