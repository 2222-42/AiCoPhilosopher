"""Integration test for full clarification → workstream lifecycle (T-031).

End-to-end: new project → refine goal → approve → start workstream
→ pause → resume → status
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
    step = 0

    # Step 1: Start
    result = await coordinator.run(command="start", user_input="What is consciousness?")
    step += 1
    assert result.get("dialogue_state") == "clarifying" or result.get("dialogue_state") == "awaiting_question"

    # Step 2-6: Clarify (up to 5 turns to reach goal_proposed)
    for _ in range(5):
        result = coordinator._start_dialogue("I'm interested in the hard problem of consciousness.")
        if result["dialogue_state"] == "goal_proposed":
            break
    assert result["dialogue_state"] == "goal_proposed"
    assert result["proposed_goal"] is not None

    # Step 3: Approve goal
    result = coordinator._handle_approve_goal()
    assert result["dialogue_state"] == "goals_approved"

    # Step 4: Propose and start workstream
    result = await coordinator._handle_propose_workstream("literature_search")
    assert "proposal" in result

    # Create workstream via factory
    ws = WorkstreamCoordinatorAgent.create_workstream(
        "literature_search",
        {"description": "Consciousness literature"},
    )
    assert ws.workstream_type == "literature_search"
    assert ws.status == "pending"

    # Step 5: Start → Running
    await ws.start()
    assert ws.status == "running"

    # Step 6: Pause → Paused
    await ws.pause()
    assert ws.status == "paused"

    # Step 7: Resume → Running
    await ws.resume()
    assert ws.status == "running"

    # Step 8: Status
    status = await coordinator._get_status_summary()
    assert status.get("goal_approved") is True
    assert status.get("dialogue_state") == "goals_approved"

    # Step 9: Complete workstream
    ws.complete("Literature review complete.")
    assert ws.status == "completed"

    # Step 10: Workstream progress
    progress = await ws.get_progress()
    assert progress["workstream_id"] == ws.workstream_id
    assert progress["type"] == "literature_search"


@pytest.mark.asyncio
async def test_status_within_thirty_seconds() -> None:
    """AC-007: Status reflects commands within 30s (latency check)."""
    import time
    coordinator = ProjectCoordinatorAgent(project_id="test-proj-perf")

    start = time.monotonic()
    result = await coordinator._get_status_summary()
    elapsed = time.monotonic() - start

    assert elapsed < 30.0, f"Status took {elapsed:.2f}s, exceeds 30s limit"
    assert isinstance(result, dict)
    assert "goal_approved" in result
