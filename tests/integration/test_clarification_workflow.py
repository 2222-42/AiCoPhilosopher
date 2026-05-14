"""Integration test for full clarification → workstream lifecycle (T-031).

End-to-end: new project → clarify → approve → start workstream
→ pause → resume → status → complete
"""

import pytest

from aicophilosopher.application.orchestration.coordinator import ProjectCoordinatorAgent
from aicophilosopher.application.orchestration.workstream_coordinator import (
    WorkstreamCoordinatorAgent,
)


@pytest.fixture
def coordinator() -> ProjectCoordinatorAgent:
    return ProjectCoordinatorAgent(project_id="test-proj-int-001")


@pytest.mark.asyncio
async def test_full_clarification_workflow(coordinator: ProjectCoordinatorAgent) -> None:
    """Full lifecycle: start → clarify → approve → propose → pause → resume → status."""
    result = await coordinator.run("What is consciousness?")
    assert result["dialogue_state"] == "clarifying"

    for _ in range(5):
        result = await coordinator.run("I'm interested in the hard problem of consciousness.")
        if result["dialogue_state"] == "goal_proposed":
            break
    assert result["dialogue_state"] == "goal_proposed"
    assert result["proposed_goal"] is not None

    result = await coordinator.run(command="approve_goal")
    assert result["dialogue_state"] == "goal_approved"

    result = await coordinator.run(command="propose_workstream", workstream_type="literature_search")
    assert "proposal" in result

    ws = WorkstreamCoordinatorAgent.create_workstream(
        "literature_search",
        {"description": "Consciousness literature"},
    )
    assert ws.workstream_type == "literature_search"
    assert ws.status == "pending"

    await ws.start()
    assert ws.status == "running"

    await ws.pause()
    assert ws.status == "paused"

    await ws.resume()
    assert ws.status == "running"

    status = await coordinator.run(command="status")
    assert status.get("goal_approved") is True
    assert status.get("dialogue_state") == "goal_approved"

    await ws.complete("Literature review complete.")
    assert ws.status == "completed"

    progress = await ws.get_progress()
    assert progress["workstream_id"] == ws.workstream_id
    assert progress["type"] == "literature_search"


@pytest.mark.asyncio
async def test_status_within_thirty_seconds() -> None:
    """AC-007: Status reflects commands within 30s (latency check)."""
    import time
    coordinator = ProjectCoordinatorAgent(project_id="test-proj-perf")

    start = time.monotonic()
    result = await coordinator.run(command="status")
    elapsed = time.monotonic() - start

    assert elapsed < 30.0, f"Status took {elapsed:.2f}s, exceeds 30s limit"
    assert isinstance(result, dict)
    assert "goal_approved" in result
