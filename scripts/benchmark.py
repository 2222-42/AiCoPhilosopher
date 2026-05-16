#!/usr/bin/env python3
"""Performance benchmark (T-076) + Memory profiling (T-078).

Verifies:
  AC-007: workstream lifecycle (start/pause/resume/status) <30s
  AC-008: hypothesis/argument retrieval <5s
  AC-001: multi-turn agent dialogue <2min per turn
  T-078: peak memory <500MB under 5-workstream concurrent load
"""

from __future__ import annotations

import asyncio
import time
import tracemalloc

from aicophilosopher.application.agents.argumentation import ArgumentationAgent
from aicophilosopher.application.agents.concept_analysis import ConceptAnalysisAgent
from aicophilosopher.application.agents.critical_review import CriticalReviewAgent
from aicophilosopher.application.agents.cross_traditional import (
    CrossTraditionalComparisonAgent,
)
from aicophilosopher.application.agents.literature_search import LiteratureSearchAgent
from aicophilosopher.application.agents.synthesis import SynthesisAgent

# Known-good arguments for review agent
SAMPLE_ARGUMENT = {
    "premises": ["If P then Q", "Q"],
    "conclusion": "P",
    "inference_rule": "Affirming the consequent",
    "tradition": "analytic",
    "confidence": 0.3,
}

SAMPLE_SYNTH_OUTPUT = [{
    "workstream_id": "ws-1",
    "type": "argumentation",
    "results": "## Test Result",
    "confidence": 0.7,
    "claims": [{"text": "test claim", "confidence": 0.8, "origin": "test"}],
}]

SAMPLE_ARGUMENT_OUTPUT = [{
    "workstream_id": "ws-arg",
    "type": "argumentation",
    "results": "## Argument",
    "confidence": 0.7,
    "claims": [{"text": "Compatibilism is viable", "confidence": 0.8,
                "origin": "arg"}],
}, {
    "workstream_id": "ws-cr",
    "type": "critical_review",
    "results": "## Review",
    "confidence": 0.6,
    "claims": [{"text": "Fallacy detected", "confidence": 0.7, "origin": "cr"}],
}]


class Timer:
    """Context manager: measure elapsed time with label."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.elapsed: float = 0.0

    def __enter__(self) -> Timer:
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed = time.perf_counter() - self.start

    def result(self) -> dict[str, float]:
        return {"label": self.label, "time_s": round(self.elapsed, 4)}


# ---------------------------------------------------------------------------
# AC-007: Workstream lifecycle benchmark
# ---------------------------------------------------------------------------
async def benchmark_ac007_workstream_lifecycle() -> dict[str, float]:
    """Simulate workstream start→run→pause→resume→status cycle."""
    with Timer("ac007_workstream_lifecycle") as t:
        # Initialize agents
        arg = ArgumentationAgent("ws-bench-arg")
        cr = CriticalReviewAgent("ws-bench-cr")
        syn = SynthesisAgent("ws-bench-syn")

        # Run argumentation (workstream start)
        arg_result = await arg.run("Is free will compatible with determinism?")

        # Simulate pause → resume cycle: re-run with different question
        arg_result2 = await arg.run("What is the nature of consciousness?")

        # Run review on the arguments
        review_input = arg_result["arguments"] + arg_result["competing_positions"]
        cr_result = await cr.run(review_input)

        # Synthesize (status reflection)
        syn_result = await syn.run(SAMPLE_ARGUMENT_OUTPUT)

        # Verify outputs
        assert arg_result["arguments"]
        assert cr_result["reviews"]
        assert syn_result["synthesized_document"]

    return t.result()


# ---------------------------------------------------------------------------
# AC-008: Hypothesis/argument retrieval benchmark
# ---------------------------------------------------------------------------
async def benchmark_ac008_retrieval() -> dict[str, float]:
    """Simulate show-hypotheses / show-dead-ends retrieval."""
    with Timer("ac008_hypothesis_retrieval") as t:
        # Run argumentation to generate hypotheses
        arg = ArgumentationAgent("ret-bench-arg")
        result = await arg.run("Does God exist?")

        # Simulate hypothesis listing (extract all claims)
        hypotheses = []
        for a in result["arguments"]:
            if a.get("conclusion"):
                hypotheses.append(a["conclusion"])
        for p in result.get("competing_positions", []):
            if p.get("conclusion"):
                hypotheses.append(p["conclusion"])

        # Simulate dead-ends retrieval: filter by low confidence
        dead_ends = [
            a for a in result["arguments"]
            if a.get("confidence", 0) < 0.5
        ]

        assert len(hypotheses) >= 2
        assert isinstance(dead_ends, list)

    return t.result()


# ---------------------------------------------------------------------------
# AC-001: Multi-turn clarification loop benchmark
# ---------------------------------------------------------------------------
async def benchmark_ac001_clarification() -> dict[str, float]:
    """Simulate ≤5 turns of Socratic clarification dialogue."""
    with Timer("ac001_clarification_turns") as t:
        questions = [
            "Is free will compatible with determinism?",
            "What is the nature of consciousness?",
            "Does God exist?",
            "What is abstraction?",
            "Can machines think?",
        ]

        arg = ArgumentationAgent("clar-bench")
        for q in questions[:5]:  # max 5 turns
            result = await arg.run(q)
            assert result["arguments"]

    return t.result()


# ---------------------------------------------------------------------------
# Agent-level benchmarks
# ---------------------------------------------------------------------------
async def benchmark_agents() -> list[dict[str, float]]:
    """Run individual agents for baseline timing."""
    results: list[dict[str, float]] = []

    agents: list[tuple[str, object, object]] = [
        ("lit_search", LiteratureSearchAgent("bl"), "abstraction"),
        ("concept_analysis", ConceptAnalysisAgent("bc"), "abstraction"),
    ]

    for name, agent, input_data in agents:
        with Timer(name) as t:
            await agent.run(input_data)  # type: ignore[arg-type]
        results.append(t.result())

    return results


# ---------------------------------------------------------------------------
# T-078: Memory profiling with 5 concurrent workstreams
# ---------------------------------------------------------------------------
def benchmark_concurrent_memory() -> dict[str, float]:
    """Measure peak memory under 5 concurrent workstream load."""
    tracemalloc.start()

    async def _run() -> None:
        # 5 different workstream types
        tasks = [
            ArgumentationAgent("mem-arg").run("Is free will real?"),
            CriticalReviewAgent("mem-cr").run([SAMPLE_ARGUMENT]),
            CrossTraditionalComparisonAgent("mem-ct").run("abstraction"),
            SynthesisAgent("mem-syn").run(SAMPLE_SYNTH_OUTPUT),
            ConceptAnalysisAgent("mem-ca").run("consciousness"),
        ]
        await asyncio.gather(*tasks)

    asyncio.run(_run())
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "label": "t078_concurrent_5_workstreams",
        "peak_memory_mb": round(peak / (1024 * 1024), 2),
        "current_memory_mb": round(current / (1024 * 1024), 2),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 60)
    print("AiCoPhilosopher Performance Benchmark (T-076 + T-078)")
    print("=" * 60)

    all_pass = True
    results: list[dict[str, float]] = []

    # AC-007: workstream lifecycle
    print("\n--- AC-007: Workstream Lifecycle (< 30s) ---")
    r = asyncio.run(benchmark_ac007_workstream_lifecycle())
    results.append(r)
    status = "PASS" if r["time_s"] < 30.0 else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  {r['label']:35s}: {r['time_s']:8.4f}s [{status}]")

    # AC-008: hypothesis retrieval
    print("\n--- AC-008: Hypothesis Retrieval (< 5s) ---")
    r = asyncio.run(benchmark_ac008_retrieval())
    results.append(r)
    status = "PASS" if r["time_s"] < 5.0 else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  {r['label']:35s}: {r['time_s']:8.4f}s [{status}]")

    # AC-001: clarification turns
    print("\n--- AC-001: Clarification ≤5 turns (< 2min/turn) ---")
    r = asyncio.run(benchmark_ac001_clarification())
    results.append(r)
    status = "PASS" if r["time_s"] < 600.0 else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  {r['label']:35s}: {r['time_s']:8.4f}s [{status}]")

    # Agent baselines
    print("\n--- Agent Baselines ---")
    for r in asyncio.run(benchmark_agents()):
        results.append(r)
        status = "PASS" if r["time_s"] < 5.0 else "FAIL"
        print(f"  {r['label']:35s}: {r['time_s']:8.4f}s [{status}]")

    # T-078: memory
    print("\n--- T-078: Memory (< 500MB, 5 concurrent workstreams) ---")
    r = benchmark_concurrent_memory()
    results.append(r)
    status = "PASS" if r["peak_memory_mb"] < 500 else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  Peak memory:     {r['peak_memory_mb']:8.1f} MB [{status}]")
    print(f"  Current memory:  {r['current_memory_mb']:8.1f} MB")

    # Summary
    print("\n" + "=" * 60)
    if all_pass:
        print("RESULT: ALL CHECKS PASSED")
    else:
        print("RESULT: SOME CHECKS FAILED")
    print(f"Total benchmarks: {len(results)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
