"""Tests: Coordinator propose_workstream runs agents and exposes results (Issue #60)."""

from __future__ import annotations

import pytest

from aicophilosopher.application.orchestration.coordinator import ProjectCoordinatorAgent
from aicophilosopher.application.services.workstream_runner import (
    SUPPORTED_WORKSTREAM_TYPES,
    normalize_workstream_type,
    run_workstream_agent,
    summarize_agent_result,
)


@pytest.fixture
def approved_coordinator() -> ProjectCoordinatorAgent:
    """Coordinator with an approved goal, ready for workstream launch."""
    coord = ProjectCoordinatorAgent(project_id="test-proj-60")
    # Drive dialogue to goal_proposed then approve
    for _ in range(5):
        # run is async; tests use pytest-asyncio
        pass
    return coord


async def _approve(coord: ProjectCoordinatorAgent) -> None:
    for _ in range(5):
        result = await coord.run("test inquiry")
        if result.get("dialogue_state") == "goal_proposed":
            break
    await coord.run(command="approve_goal")
    assert coord.get_dialogue_state() == "goal_approved"


@pytest.mark.asyncio
async def test_propose_workstream_runs_literature_search_agent() -> None:
    coord = ProjectCoordinatorAgent(project_id="test-proj-60")
    await _approve(coord)

    result = await coord.run(
        command="propose_workstream", workstream_type="literature_search"
    )

    assert "error" not in result
    assert result["status"] == "completed"
    assert "agent_result" in result
    agent = result["agent_result"]
    assert "result_count" in agent
    assert "bibliography" in agent

    ws_id = result["workstream_id"]
    assert ws_id in coord.active_workstreams
    stored = coord.active_workstreams[ws_id]
    assert stored["status"] == "completed"
    assert stored["agent_result"] is not None


@pytest.mark.asyncio
async def test_propose_workstream_all_supported_types() -> None:
    """Each supported workstream type produces a completed agent result."""
    types = [
        "literature_search",
        "concept_analysis",
        "argumentation",
        "critical_review",
        "cross_traditional",
        "cross_traditional_comparison",
        "synthesis",
    ]
    for ws_type in types:
        coord = ProjectCoordinatorAgent(project_id=f"proj-{ws_type}")
        await _approve(coord)
        result = await coord.run(command="propose_workstream", workstream_type=ws_type)
        assert "error" not in result, f"{ws_type}: {result}"
        assert result["status"] == "completed", f"{ws_type}: {result}"
        assert result.get("agent_result"), f"{ws_type}: missing agent_result"
        assert not result["agent_result"].get("error"), f"{ws_type}: {result['agent_result']}"


@pytest.mark.asyncio
async def test_status_and_logs_show_agent_results() -> None:
    coord = ProjectCoordinatorAgent(project_id="test-proj-logs")
    await _approve(coord)

    launch = await coord.run(
        command="propose_workstream", workstream_type="argumentation"
    )
    ws_id = launch["workstream_id"]

    status = await coord.run(command="status")
    assert any(ws_id in line for line in status["active_workstreams"])
    assert any("completed" in line for line in status["active_workstreams"])

    logs_all = await coord.run(command="logs", workstream_id="")
    assert ws_id in logs_all["summary"]
    assert "arguments=" in logs_all["summary"]

    logs_one = await coord.run(command="logs", workstream_id=ws_id)
    assert logs_one.get("agent_result") is not None
    assert "arguments" in logs_one["agent_result"]
    assert "Result:" in logs_one["summary"]


@pytest.mark.asyncio
async def test_unknown_workstream_type_fails_gracefully() -> None:
    coord = ProjectCoordinatorAgent(project_id="test-proj-unknown")
    await _approve(coord)

    result = await coord.run(
        command="propose_workstream", workstream_type="not_a_real_type"
    )
    assert result["status"] == "failed"
    assert result["agent_result"].get("error")


@pytest.mark.asyncio
async def test_workstream_runner_offline_literature_search() -> None:
    result = await run_workstream_agent(
        "literature_search", "What is free will?", agent_id="t-runner"
    )
    assert "error" not in result
    assert result["result_count"] >= 0
    summary = summarize_agent_result("literature_search", result)
    assert "results=" in summary


def test_normalize_cross_traditional_alias() -> None:
    assert (
        normalize_workstream_type("cross_traditional")
        == "cross_traditional_comparison"
    )
    assert "cross_traditional_comparison" in SUPPORTED_WORKSTREAM_TYPES
