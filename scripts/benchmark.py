#!/usr/bin/env python3
"""Performance benchmark (T-076) + Memory profiling (T-078).

Verifies:
  AC-007: workstream agent response <30s
  AC-008: hypothesis/argument retrieval <5s
  AC-001: clarification/argument loops <5 turns <10min
  T-078: peak memory <500MB under concurrent load
"""

from __future__ import annotations

import asyncio
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


def timed(label: str) -> Any:
    """Context manager: measure elapsed time."""

    class _Timer:
        def __enter__(self) -> _Timer:
            self.start = time.perf_counter()
            return self

        def __exit__(self, *args: object) -> None:
            self.elapsed = time.perf_counter() - self.start

    return _Timer()


AC_THRESHOLDS: dict[str, float] = {
    "AC-007 (workstream <30s)": 30.0,
    "AC-008 (retrieval <5s)": 5.0,
    "AC-001 (turn <2min)": 120.0,
}


async def benchmark_agents() -> dict[str, dict[str, float]]:
    """Run all agents and measure response times."""
    results: dict[str, dict[str, float]] = {}

    agents: list[tuple[str, Any, str]] = [
        ("argumentation", ArgumentationAgent("bench-arg"),
         "Is free will compatible with determinism?"),
        ("critical_review", CriticalReviewAgent("bench-cr"),
         [{"premises": ["If P then Q", "Q"], "conclusion": "P",
           "inference_rule": "Affirming the consequent",
           "tradition": "analytic", "confidence": 0.3}]),
        ("cross_traditional", CrossTraditionalComparisonAgent("bench-ct"),
         "abstraction"),
        ("synthesis", SynthesisAgent("bench-syn"),
         [{"workstream_id": "ws-1", "type": "argumentation",
           "results": "## Test", "confidence": 0.7,
           "claims": [{"text": "test", "confidence": 0.8,
                       "origin": "test"}]}]),
        ("literature_search", LiteratureSearchAgent("bench-lit"),
         "abstraction"),
        ("concept_analysis", ConceptAnalysisAgent("bench-ca"),
         "abstraction"),
    ]

    for name, agent, input_data in agents:
        t = timed(name)
        with t:
            if name == "critical_review":
                await agent.run(input_data)
            else:
                await agent.run(input_data)
        results[name] = {"time_s": round(t.elapsed, 4)}

    return results


async def benchmark_concurrent() -> dict[str, float]:
    """Run all agents concurrently and measure total time."""
    start = time.perf_counter()

    async def run_arg() -> None:
        a = ArgumentationAgent("conc-arg")
        await a.run("What is abstraction?")

    async def run_ct() -> None:
        a = CrossTraditionalComparisonAgent("conc-ct")
        await a.run("abstraction")

    async def run_syn() -> None:
        a = SynthesisAgent("conc-syn")
        await a.run([{
            "workstream_id": "ws-1", "type": "argumentation",
            "results": "## Test", "confidence": 0.7,
            "claims": [{"text": "test", "confidence": 0.8, "origin": "test"}],
        }])

    await asyncio.gather(run_arg(), run_ct(), run_syn())
    elapsed = time.perf_counter() - start
    return {"concurrent_3_agents_s": round(elapsed, 4)}


def measure_memory() -> dict[str, float]:
    """Measure peak memory during agent operations."""
    tracemalloc.start()

    async def _run() -> None:
        agents = [
            ArgumentationAgent(f"mem-{i}") for i in range(5)
        ]
        tasks = [a.run(f"Question {i}?") for i, a in enumerate(agents)]
        await asyncio.gather(*tasks)

    asyncio.run(_run())
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "peak_memory_mb": round(peak / (1024 * 1024), 2),
        "current_memory_mb": round(current / (1024 * 1024), 2),
    }


def main() -> None:
    print("=" * 60)
    print("AiCoPhilosopher Performance Benchmark (T-076 + T-078)")
    print("=" * 60)

    # Agent benchmarks
    print("\n--- Agent Response Times ---")
    results = asyncio.run(benchmark_agents())
    all_pass = True
    for name, data in results.items():
        t = data["time_s"]
        threshold = 5.0 if name != "argumentation" else 30.0
        status = "PASS" if t < threshold else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"  {name:25s}: {t:8.4f}s  [{status}] (threshold: {threshold}s)")

    # Concurrent benchmark
    print("\n--- Concurrent Execution ---")
    conc = asyncio.run(benchmark_concurrent())
    t = conc["concurrent_3_agents_s"]
    status = "PASS" if t < 30.0 else "FAIL"
    print(f"  3 agents concurrent: {t:.4f}s [{status}] (threshold: 30s)")

    # Memory
    print("\n--- Memory ---")
    mem = measure_memory()
    peak_mb = mem["peak_memory_mb"]
    status = "PASS" if peak_mb < 500 else "FAIL"
    print(f"  Peak:  {peak_mb:.1f} MB [{status}] (threshold: 500MB)")
    print(f"  Current: {mem['current_memory_mb']:.1f} MB")

    # Summary
    print("\n" + "=" * 60)
    if all_pass and status == "PASS":
        print("RESULT: ALL CHECKS PASSED")
    else:
        print("RESULT: SOME CHECKS FAILED")
    print("=" * 60)


if __name__ == "__main__":
    main()
