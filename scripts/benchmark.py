#!/usr/bin/env python3
"""Performance benchmark (T-076) + Memory profiling (T-078).

NOTE: This benchmark measures agent-level response times in heuristic
(no-LLM) mode.  Full production AC validation requires the running
workstream coordinator, persistence layer, and CLI lifecycle — these
are exercised by the integration test suite, not this script.

AC-007: Agent pipeline simulating workstream lifecycle <30s
AC-008: Hypothesis generation + dead-end extraction <5s
AC-001: Per-turn agent dialogue <2min/turn (5 turns)
T-078: Peak memory <500MB under 5 concurrent agent loads
"""

from __future__ import annotations

import asyncio
import sys
import time
import tracemalloc
from typing import Any

from aicophilosopher.application.agents.argumentation import ArgumentationAgent
from aicophilosopher.application.agents.concept_analysis import ConceptAnalysisAgent
from aicophilosopher.application.agents.critical_review import CriticalReviewAgent
from aicophilosopher.application.agents.cross_traditional import (
    CrossTraditionalComparisonAgent,
)
from aicophilosopher.application.agents.literature_search import LiteratureSearchAgent
from aicophilosopher.application.agents.synthesis import SynthesisAgent

SAMPLE_ARGUMENT: dict[str, object] = {
    "premises": ["If P then Q", "Q"],
    "conclusion": "P",
    "inference_rule": "Affirming the consequent",
    "tradition": "analytic",
    "confidence": 0.3,
}

SAMPLE_SYNTH_INPUT: list[dict[str, object]] = [{
    "workstream_id": "ws-1",
    "type": "argumentation",
    "results": "## Test Result",
    "confidence": 0.7,
    "claims": [{"text": "test claim", "confidence": 0.8, "origin": "test"}],
}]


class Timer:
    """Measure elapsed wall-clock time."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.elapsed: float = 0.0

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed = time.perf_counter() - self._start


# ---------------------------------------------------------------------------
# AC-007: Agent pipeline (workstream lifecycle proxy)
# ---------------------------------------------------------------------------
async def bench_ac007() -> tuple[str, float]:
    label = "ac007_agent_pipeline"
    with Timer(label) as t:
        arg = ArgumentationAgent("ws-arg")
        cr = CriticalReviewAgent("ws-cr")
        syn = SynthesisAgent("ws-syn")

        arg_result = await arg.run("Is free will compatible with determinism?")
        review_input = arg_result["arguments"] + arg_result["competing_positions"]
        cr_result = await cr.run(review_input)
        syn_result = await syn.run([{
            "workstream_id": "ws-arg",
            "type": "argumentation",
            "results": str(arg_result.get("arguments", [{}])[0].get("conclusion", "")),
            "confidence": 0.7,
            "claims": [{"text": "test", "confidence": 0.8, "origin": "arg"}],
        }])

        assert cr_result["reviews"]
        assert syn_result["synthesized_document"]

    return label, t.elapsed


# ---------------------------------------------------------------------------
# AC-008: Hypothesis generation + filtering
# ---------------------------------------------------------------------------
async def bench_ac008() -> tuple[str, float]:
    label = "ac008_hypothesis_filtering"
    with Timer(label) as t:
        arg = ArgumentationAgent("ret-arg")
        result = await arg.run("Does God exist?")

        # Extract all hypotheses
        hypotheses: list[str] = []
        for a in result["arguments"]:
            conc = a.get("conclusion")
            if conc:
                hypotheses.append(str(conc))
        for p in result.get("competing_positions", []):
            conc = p.get("conclusion")
            if conc:
                hypotheses.append(str(conc))

        # Identify low-confidence as dead ends
        dead_ends = [a for a in result["arguments"]
                      if float(a.get("confidence", 0)) < 0.5]

        assert len(hypotheses) >= 2
        assert isinstance(dead_ends, list)

    return label, t.elapsed


# ---------------------------------------------------------------------------
# AC-001: Per-turn timing (5-turn loop)
# ---------------------------------------------------------------------------
async def bench_ac001() -> tuple[str, float, float]:
    """Returns (label, max_turn_time, total_time)."""
    label = "ac001_clarification_turns"
    questions = [
        "Is free will compatible with determinism?",
        "What is the nature of consciousness?",
        "Does God exist?",
        "What is abstraction?",
        "Can machines think?",
    ]

    turn_times: list[float] = []
    t_total = Timer("ac001_total")
    with t_total:
        arg = ArgumentationAgent("clar-arg")
        for q in questions:
            with Timer(f"turn_{q[:20]}") as tt:
                result = await arg.run(q)
                assert result["arguments"]
            turn_times.append(tt.elapsed)

    return label, max(turn_times), t_total.elapsed


# ---------------------------------------------------------------------------
# Agent baselines
# ---------------------------------------------------------------------------
async def bench_agents() -> list[tuple[str, float]]:
    results: list[tuple[str, float]] = []
    agents: list[tuple[str, Any, Any]] = [
        ("lit_search", LiteratureSearchAgent("bl"), "abstraction"),
        ("concept_analysis", ConceptAnalysisAgent("bc"), "abstraction"),
    ]
    for name, agent, inp in agents:
        with Timer(name) as t:
            await agent.run(inp)  # type: ignore[arg-type]
        results.append((name, t.elapsed))
    return results


# ---------------------------------------------------------------------------
# T-078: Memory with 5 concurrent agent types
# ---------------------------------------------------------------------------
def bench_memory() -> tuple[str, float]:
    tracemalloc.start()

    async def _run() -> None:
        tasks = [
            ArgumentationAgent("m1").run("free will"),
            CriticalReviewAgent("m2").run([SAMPLE_ARGUMENT]),
            CrossTraditionalComparisonAgent("m3").run("abstraction"),
            SynthesisAgent("m4").run(SAMPLE_SYNTH_INPUT),
            ConceptAnalysisAgent("m5").run("consciousness"),
        ]
        await asyncio.gather(*tasks)

    asyncio.run(_run())
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return "t078_memory_5_agents", round(peak / (1024 * 1024), 2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 60)
    print("AiCoPhilosopher Benchmark (T-076 + T-078)")
    print("Agent-level heuristic mode — see notes in source")
    print("=" * 60)

    failed = 0

    def check(name: str, val: float, limit: float, unit: str = "s") -> str:
        nonlocal failed
        ok = val < limit
        if not ok:
            failed += 1
        status = "PASS" if ok else "FAIL"
        print(f"  {name:40s} {val:8.4f}{unit} [{status}]  limit={limit}{unit}")
        return status

    # AC-007
    print("\n--- AC-007: Agent pipeline (< 30s) ---")
    label, t = asyncio.run(bench_ac007())
    check(label, t, 30.0)

    # AC-008
    print("\n--- AC-008: Hypothesis filtering (< 5s) ---")
    label, t = asyncio.run(bench_ac008())
    check(label, t, 5.0)

    # AC-001 (per-turn)
    print("\n--- AC-001: Per-turn agent dialogue (< 120s/turn) ---")
    label, max_turn, total = asyncio.run(bench_ac001())
    check(f"{label}_max_turn", max_turn, 120.0)
    check(f"{label}_total_5turns", total, 600.0)

    # Agent baselines
    print("\n--- Agent Baselines ---")
    for name, t in asyncio.run(bench_agents()):
        check(name, t, 5.0)

    # T-078
    print("\n--- T-078: Memory (< 500MB, 5 concurrent agents) ---")
    label, peak_mb = bench_memory()
    check(label, peak_mb, 500.0, unit="MB")

    # Summary
    print("\n" + "=" * 60)
    if failed == 0:
        print("RESULT: ALL CHECKS PASSED")
    else:
        print(f"RESULT: {failed} CHECK(S) FAILED")
    print("Mode: heuristic (no LLM) — production timing may differ with LLM")
    print("=" * 60)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
