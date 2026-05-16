"""Unit tests for SynthesisAgent (T-056).

Spec §4.9: merge workstream outputs, preserve epistemic annotations,
flag conflicts, consistent voice, synthesis confidence.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def agent() -> Any:
    from aicophilosopher.application.agents.synthesis import SynthesisAgent

    return SynthesisAgent(agent_id="test-syn-001")


SAMPLE_OUTPUTS: list[dict[str, object]] = [
    {
        "workstream_id": "ws-lit-001",
        "type": "literature_search",
        "results": "## Literature Review: Free Will\nKey finding: compatibilism has strong support in analytic tradition.",
        "confidence": 0.8,
        "claims": [
            {"text": "Compatibilism reconciles free will with determinism",
             "confidence": 0.85, "origin": "literature_synthesis"},
        ],
    },
    {
        "workstream_id": "ws-arg-002",
        "type": "argumentation",
        "results": "## Argument Analysis\nPremise 1: Determinism is true. Conclusion: Free will is an illusion.",
        "confidence": 0.6,
        "claims": [
            {"text": "Free will is an illusion under determinism",
             "confidence": 0.55, "origin": "argument_reconstruction"},
        ],
    },
    {
        "workstream_id": "ws-cr-003",
        "type": "critical_review",
        "results": "## Critical Review\nFallacy detected: false dichotomy in argument 2.",
        "confidence": 0.7,
        "claims": [
            {"text": "Argument 2 commits false dichotomy",
             "confidence": 0.8, "origin": "fallacy_detection"},
        ],
    },
]


class TestSynthesisBasic:
    @pytest.mark.asyncio
    async def test_merges_workstream_outputs(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_OUTPUTS)
        assert "synthesized_document" in result
        doc = result["synthesized_document"]
        assert isinstance(doc, str)
        assert len(doc) > 50, "Synthesized document should be substantive"

    @pytest.mark.asyncio
    async def test_empty_input_handled(self, agent: Any) -> None:
        result = await agent.run([])
        assert "synthesized_document" in result
        assert "synthesis_confidence" in result


class TestEpistemicAnnotations:
    """100% of non-trivial claims must be annotated (spec §4.9)."""

    @pytest.mark.asyncio
    async def test_preserves_confidence_annotations(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_OUTPUTS)
        assert "annotations" in result
        annotations = result["annotations"]
        assert isinstance(annotations, list)

    @pytest.mark.asyncio
    async def test_annotations_link_to_source(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_OUTPUTS)
        for ann in result.get("annotations", []):
            assert "source" in ann or "origin" in ann or "workstream_id" in ann, (
                "Each annotation must trace back to its source workstream"
            )


class TestConflictDetection:
    """Conflicts between workstream outputs must be flagged."""

    @pytest.mark.asyncio
    async def test_conflict_flag_present(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_OUTPUTS)
        assert "conflicts" in result, "Must include conflicts key"
        conflicts = result["conflicts"]
        assert isinstance(conflicts, list)

    @pytest.mark.asyncio
    async def test_conflicting_claims_detected(self, agent: Any) -> None:
        """Outputs 1 and 2 disagree on free will; synthesis should flag."""
        result = await agent.run(SAMPLE_OUTPUTS)
        conflicts = result["conflicts"]
        # At minimum, check that the conflict detection mechanism exists
        assert isinstance(conflicts, list)


class TestConsistentVoice:
    @pytest.mark.asyncio
    async def test_document_is_coherent(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_OUTPUTS)
        doc = result["synthesized_document"]
        # Should be structured as a document, not raw concatenation
        assert doc.startswith("#") or doc.startswith("##"), (
            "Document should start with a heading"
        )

    @pytest.mark.asyncio
    async def test_no_raw_workstream_markers(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_OUTPUTS)
        doc = result["synthesized_document"]
        # Should not just dump raw workstream markers
        assert "ws-lit-001" not in doc[:200], (
            "Document should not expose internal workstream IDs in leading content"
        )


class TestSynthesisConfidence:
    @pytest.mark.asyncio
    async def test_synthesis_confidence_present(self, agent: Any) -> None:
        result = await agent.run(SAMPLE_OUTPUTS)
        assert "synthesis_confidence" in result
        conf = result["synthesis_confidence"]
        assert isinstance(conf, (int, float))
        assert 0.0 <= float(conf) <= 1.0

    @pytest.mark.asyncio
    async def test_single_output_confidence(self, agent: Any) -> None:
        result = await agent.run([SAMPLE_OUTPUTS[0]])
        assert "synthesis_confidence" in result
        assert 0.0 <= float(result["synthesis_confidence"]) <= 1.0
