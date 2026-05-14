"""Unit tests for ProjectCoordinatorAgent dialogue state machine (T-030).

Exercises the public run(command=...) API exclusively.
Tests FAIL before implementation and PASS after T-033 implementation.
"""

import pytest

from aicophilosopher.application.orchestration.coordinator import ProjectCoordinatorAgent


@pytest.fixture
def coordinator() -> ProjectCoordinatorAgent:
    return ProjectCoordinatorAgent(project_id="test-proj-1")


@pytest.mark.asyncio
async def test_clarification_turns_under_five(coordinator: ProjectCoordinatorAgent) -> None:
    """AC-001: ≤5 clarification turns before goal approval."""
    result = await coordinator.run("What is consciousness?")
    assert result["dialogue_state"] == "clarifying"
    assert result["turn"] == 1

    for i in range(4):
        result = await coordinator.run(f"Response number {i + 2}")
        if result["dialogue_state"] == "goal_proposed":
            break

    assert result["dialogue_state"] == "goal_proposed", (
        f"Should reach goal_proposed within 5 turns, got state={result['dialogue_state']} at turn={result['turn']}"
    )
    assert result["turn"] <= 5, f"Exceeded 5 turns: {result['turn']}"


@pytest.mark.asyncio
async def test_goal_approval_transition(coordinator: ProjectCoordinatorAgent) -> None:
    """After user approves, goal_approved state is set."""
    for _ in range(5):
        result = await coordinator.run("test")
        if result["dialogue_state"] == "goal_proposed":
            break

    result = await coordinator.run(command="approve_goal")
    assert result["dialogue_state"] == "goal_approved"
    assert result.get("approved_goal") is not None
    assert coordinator.get_dialogue_state() == "goal_approved"


@pytest.mark.asyncio
async def test_workstream_proposal_after_goal_approved(coordinator: ProjectCoordinatorAgent) -> None:
    """start_workstream returns structured proposal."""
    for _ in range(5):
        result = await coordinator.run("test")
        if result["dialogue_state"] == "goal_proposed":
            break
    await coordinator.run(command="approve_goal")

    result = await coordinator.run(command="propose_workstream", workstream_type="literature_search")
    assert "proposal" in result
    assert result["proposal"]["type"] == "literature_search"
    assert result["proposal"]["goal"] is not None


@pytest.mark.asyncio
async def test_workstream_proposal_before_goal_approved_raises(coordinator: ProjectCoordinatorAgent) -> None:
    """start_workstream before goal approval returns error."""
    result = await coordinator.run(command="propose_workstream", workstream_type="literature_search")
    assert "error" in result
    assert "no approved goals" in result["error"].lower()


@pytest.mark.asyncio
async def test_steer_command(coordinator: ProjectCoordinatorAgent) -> None:
    """Steer command is acknowledged."""
    result = await coordinator.run(command="steer", workstream_id="ws-001", instruction="Focus on X")
    assert result.get("acknowledged") is True
    assert "ws-001" in result.get("message", "")


@pytest.mark.asyncio
async def test_status_before_any_goal(coordinator: ProjectCoordinatorAgent) -> None:
    """Status summary returns defaults for fresh coordinator."""
    result = await coordinator.run(command="status")
    assert result.get("goal_approved") is False
    assert result.get("active_hypotheses") == 0
    assert result.get("refuted_hypotheses") == 0
