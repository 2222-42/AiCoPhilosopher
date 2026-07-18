"""Dispatch workstream types to concrete agents (CLI + Coordinator shared path).

Agents operate in offline/heuristic mode when no LLM is configured and always
return a result dict. Persistence of results into living documents is out of
scope here (see Issue #63).
"""

from __future__ import annotations

from typing import Any

# REPL patterns use shorter aliases; CLI Choice uses the longer form.
_TYPE_ALIASES: dict[str, str] = {
    "cross_traditional": "cross_traditional_comparison",
}

SUPPORTED_WORKSTREAM_TYPES = frozenset(
    {
        "literature_search",
        "concept_analysis",
        "argumentation",
        "critical_review",
        "cross_traditional_comparison",
        "synthesis",
    }
)


def normalize_workstream_type(workstream_type: str) -> str:
    """Map aliases to the canonical workstream type name."""
    return _TYPE_ALIASES.get(workstream_type, workstream_type)


async def run_workstream_agent(
    workstream_type: str,
    query: str,
    *,
    agent_id: str = "workstream",
    traditions: list[str] | None = None,
    prior_outputs: list[dict[str, object]] | None = None,
) -> dict[str, Any]:
    """Run the agent for *workstream_type*; works offline without an LLM.

    Returns the agent result dict. Unknown types yield ``{"error": ...}``.
    """
    ws_type = normalize_workstream_type(workstream_type)
    kwargs: dict[str, object] = {}
    if traditions:
        kwargs["traditions"] = traditions

    if ws_type == "literature_search":
        return await _run_literature_search(agent_id, query, kwargs)
    if ws_type == "concept_analysis":
        return await _run_concept_analysis(agent_id, query, kwargs)
    if ws_type == "argumentation":
        return await _run_argumentation(agent_id, query, kwargs)
    if ws_type == "critical_review":
        return await _run_critical_review(agent_id, query, kwargs)
    if ws_type == "cross_traditional_comparison":
        return await _run_cross_traditional(agent_id, query, kwargs)
    if ws_type == "synthesis":
        return await _run_synthesis(agent_id, query, prior_outputs)
    return {"error": f"Unknown workstream type: {workstream_type}"}


async def _run_literature_search(
    agent_id: str, query: str, kwargs: dict[str, object]
) -> dict[str, Any]:
    from aicophilosopher.application.agents.literature_search import LiteratureSearchAgent

    agent = LiteratureSearchAgent(agent_id=agent_id)
    return dict(await agent.run(query, **kwargs))


async def _run_concept_analysis(
    agent_id: str, query: str, kwargs: dict[str, object]
) -> dict[str, Any]:
    from aicophilosopher.application.agents.concept_analysis import ConceptAnalysisAgent

    agent = ConceptAnalysisAgent(agent_id=agent_id)
    return dict(await agent.run(query, **kwargs))


async def _run_argumentation(
    agent_id: str, query: str, kwargs: dict[str, object]
) -> dict[str, Any]:
    from aicophilosopher.application.agents.argumentation import ArgumentationAgent

    agent = ArgumentationAgent(agent_id=agent_id)
    return dict(await agent.run(query, **kwargs))


async def _run_critical_review(
    agent_id: str, query: str, kwargs: dict[str, object]
) -> dict[str, Any]:
    from aicophilosopher.application.agents.argumentation import ArgumentationAgent
    from aicophilosopher.application.agents.critical_review import CriticalReviewAgent

    arg_agent = ArgumentationAgent(agent_id=f"{agent_id}-arg")
    arg_result = await arg_agent.run(query, **kwargs)
    review_input = list(arg_result.get("arguments", [])) + list(
        arg_result.get("competing_positions", [])
    )
    agent = CriticalReviewAgent(agent_id=agent_id)
    result = dict(await agent.run(review_input))
    result["source_arguments"] = arg_result
    return result


async def _run_cross_traditional(
    agent_id: str, query: str, kwargs: dict[str, object]
) -> dict[str, Any]:
    from aicophilosopher.application.agents.cross_traditional import (
        CrossTraditionalComparisonAgent,
    )

    agent = CrossTraditionalComparisonAgent(agent_id=agent_id)
    return dict(await agent.run(query, **kwargs))


async def _run_synthesis(
    agent_id: str,
    query: str,
    prior_outputs: list[dict[str, object]] | None,
) -> dict[str, Any]:
    from aicophilosopher.application.agents.synthesis import SynthesisAgent

    agent = SynthesisAgent(agent_id=agent_id)
    outputs: list[dict[str, object]] = prior_outputs or [
        {
            "workstream_id": "ws-seed",
            "type": "argumentation",
            "results": query,
            "confidence": 0.6,
            "claims": [{"text": query[:200], "confidence": 0.6, "origin": "goal"}],
        }
    ]
    title = query[:80] if query else "Synthesis"
    return dict(await agent.run(outputs, title=title))


def summarize_agent_result(
    workstream_type: str, result: dict[str, Any] | None
) -> str:
    """Short human-readable summary for status/logs panels."""
    if not result:
        return "(no agent output)"
    if result.get("error"):
        return f"error: {result['error']}"

    ws_type = normalize_workstream_type(workstream_type)
    if ws_type == "literature_search":
        bridges = result.get("bridge_notes") or []
        return f"results={result.get('result_count', 0)}, bridges={len(bridges)}"
    if ws_type == "concept_analysis":
        cmap = result.get("concept_map")
        n = len(cmap) if isinstance(cmap, list) else 0
        return f"concept={result.get('concept', '?')}, map_nodes={n}"
    if ws_type == "argumentation":
        args = result.get("arguments") or []
        competing = result.get("competing_positions") or []
        return f"arguments={len(args)}, competing={len(competing)}"
    if ws_type == "critical_review":
        fallacies = result.get("fallacies") or []
        counters = result.get("counter_arguments") or []
        return f"fallacies={len(fallacies)}, counters={len(counters)}"
    if ws_type == "cross_traditional_comparison":
        bridges = result.get("bridge_map") or []
        incomm = result.get("incommensurability_register") or []
        return f"bridges={len(bridges)}, incommensurabilities={len(incomm)}"
    if ws_type == "synthesis":
        conf = result.get("synthesis_confidence", result.get("confidence", "?"))
        return f"workstreams={result.get('workstream_count', 0)}, confidence={conf}"
    return "completed"
