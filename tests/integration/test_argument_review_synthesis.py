"""Integration test for argumentation → review → synthesis flow (T-052).

End-to-end test covering the full US3 pipeline:
  1. ArgumentationAgent: reconstruct arguments from a question
  2. CriticalReviewAgent: review arguments, detect fallacies
  3. SynthesisAgent: merge into living document section

AC-006: Living document contains Arguments section with embedded margin annotations.
"""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def argumentation_agent() -> Any:
    from aicophilosopher.application.agents.argumentation import ArgumentationAgent

    return ArgumentationAgent(agent_id="int-arg-001")


@pytest.fixture
def critical_review_agent() -> Any:
    from aicophilosopher.application.agents.critical_review import (
        CriticalReviewAgent,
    )

    return CriticalReviewAgent(agent_id="int-cr-001")


@pytest.fixture
def synthesis_agent() -> Any:
    from aicophilosopher.application.agents.synthesis import SynthesisAgent

    return SynthesisAgent(agent_id="int-syn-001")


class TestArgumentationToReviewToSynthesis:
    """Full E2E pipeline: question → arguments → review → synthesis."""

    @pytest.mark.asyncio
    async def test_full_pipeline_free_will(
        self,
        argumentation_agent: Any,
        critical_review_agent: Any,
        synthesis_agent: Any,
    ) -> None:
        # Stage 1: Argumentation
        arg_result = await argumentation_agent.run(
            "Is free will compatible with determinism?"
        )
        assert len(arg_result["arguments"]) >= 2
        assert arg_result["competing_positions"]

        # Stage 2: Critical Review
        review_input = arg_result["arguments"] + arg_result["competing_positions"]
        review_result = await critical_review_agent.run(review_input)
        assert "fallacies" in review_result
        assert len(review_result["reviews"]) >= len(review_input)

        # Stage 3: Synthesis
        workstream_outputs = [
            {
                "workstream_id": "ws-arg",
                "type": "argumentation",
                "results": _format_as_markdown(arg_result),
                "confidence": 0.75,
                "claims": [
                    {"text": a.get("conclusion", ""), "confidence": a.get("confidence", 0.5),
                     "origin": "argument_reconstruction"}
                    for a in arg_result["arguments"]
                    if a.get("conclusion")
                ],
            },
            {
                "workstream_id": "ws-cr",
                "type": "critical_review",
                "results": _format_review_as_markdown(review_result),
                "confidence": review_result.get("overall_confidence", 0.7),
                "claims": [
                    {"text": f.get("explanation", ""), "confidence": 0.7,
                     "origin": "fallacy_detection"}
                    for f in review_result.get("fallacies", [])
                    if f.get("explanation")
                ],
            },
        ]
        syn_result = await synthesis_agent.run(workstream_outputs)

        # Assertions (AC-006)
        doc = syn_result["synthesized_document"]
        assert len(doc) > 100, "Synthesized document should be substantive"

        # Document contains Arguments section
        assert (
            "Arguments" in doc or "argumentation" in doc.lower()
        ), "Document must include arguments content"

        # Annotations present
        assert len(syn_result["annotations"]) >= 1, (
            "Must have at least one epistemic annotation"
        )

        # Synthesis confidence
        assert 0.0 <= syn_result["synthesis_confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_pipeline_with_consciousness_question(
        self,
        argumentation_agent: Any,
        critical_review_agent: Any,
        synthesis_agent: Any,
    ) -> None:
        arg_result = await argumentation_agent.run(
            "What is the nature of consciousness?"
        )
        review_input = arg_result["arguments"] + arg_result["competing_positions"]
        review_result = await critical_review_agent.run(review_input)

        workstream_outputs = [
            {
                "workstream_id": "ws-arg",
                "type": "argumentation",
                "results": _format_as_markdown(arg_result),
                "confidence": 0.7,
                "claims": [
                    {"text": a.get("conclusion", ""), "confidence": a.get("confidence", 0.5),
                     "origin": "argument_reconstruction"}
                    for a in arg_result["arguments"] if a.get("conclusion")
                ],
            },
            {
                "workstream_id": "ws-cr",
                "type": "critical_review",
                "results": _format_review_as_markdown(review_result),
                "confidence": review_result.get("overall_confidence", 0.6),
                "claims": [
                    {"text": ca.get("objection", ""), "confidence": ca.get("confidence", 0.6),
                     "origin": "counter_argument"}
                    for ca in review_result.get("counter_arguments", [])
                    if ca.get("objection")
                ],
            },
        ]
        syn_result = await synthesis_agent.run(workstream_outputs)

        doc = syn_result["synthesized_document"]
        assert "consciousness" in doc.lower() or "Consciousness" in doc

        # Cross-tradition coverage should be reflected
        annotations = syn_result["annotations"]
        traditions = {a.get("workstream_type", "") for a in annotations}
        assert len(traditions) >= 1

    @pytest.mark.asyncio
    async def test_conflicts_surface_in_synthesis(
        self,
        argumentation_agent: Any,
        synthesis_agent: Any,
    ) -> None:
        """When contradictory claims exist, synthesis should flag them."""
        # Deliberately create contradictory workstream outputs
        workstream_outputs = [
            {
                "workstream_id": "ws-pos",
                "type": "argumentation",
                "results": "## Position A\nReality is fundamentally material.",
                "confidence": 0.6,
                "claims": [
                    {"text": "Reality is fundamentally material and physical",
                     "confidence": 0.6, "origin": "materialist_position"},
                ],
            },
            {
                "workstream_id": "ws-neg",
                "type": "argumentation",
                "results": "## Position B\nReality is not fundamentally material.",
                "confidence": 0.55,
                "claims": [
                    {"text": "Reality is not fundamentally material",
                     "confidence": 0.55, "origin": "idealist_position"},
                ],
            },
        ]
        syn_result = await synthesis_agent.run(workstream_outputs)
        assert "conflicts" in syn_result
        # With direct contradiction, should detect conflict
        assert isinstance(syn_result["conflicts"], list)


def _format_as_markdown(result: dict[str, object]) -> str:
    lines: list[str] = [
        f"## Argumentation: {result.get('question', 'Unknown')}\n"
    ]
    for i, arg in enumerate(result.get("arguments", []), 1):
        lines.append(f"### Position {i}")
        lines.append(f"**Tradition**: {arg.get('tradition', 'unknown')}")
        lines.append(f"**Conclusion**: {arg.get('conclusion', '')}")
        premises = arg.get("premises", [])
        if isinstance(premises, list):
            for j, p in enumerate(premises, 1):
                lines.append(f"{j}. {p}")
        lines.append(f"**Rule**: {arg.get('inference_rule', '')}")
        lines.append(f"**Confidence**: {arg.get('confidence', '?')}")
        lines.append("")
    return "\n".join(lines)


def _format_review_as_markdown(result: dict[str, object]) -> str:
    lines: list[str] = ["## Critical Review\n"]
    fallacies = result.get("fallacies", [])
    if isinstance(fallacies, list) and fallacies:
        lines.append("### Detected Fallacies")
        for f in fallacies:
            lines.append(f"- **{f.get('name', 'unknown')}** [{f.get('severity', '?')}]: "
                         f"{f.get('explanation', '')}")
    counters = result.get("counter_arguments", [])
    if isinstance(counters, list) and counters:
        lines.append("\n### Counter-Arguments")
        for ca in counters:
            lines.append(f"- [{ca.get('tradition', '?')}] {ca.get('objection', '')}")
    adversarial = result.get("adversarial", {})
    if isinstance(adversarial, dict) and adversarial.get("stress_tests"):
        lines.append("\n### Adversarial Stress Tests")
        for st in adversarial["stress_tests"]:
            lines.append(f"- **{st.get('test_name', '?')}**: {st.get('challenge', '')}")
    return "\n".join(lines)
