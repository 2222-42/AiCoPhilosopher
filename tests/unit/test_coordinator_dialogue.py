"""Unit tests for ProjectCoordinatorAgent dialogue state machine (T-030).

Tests MUST FAIL before implementation and PASS after T-033 implementation.
"""

import pytest

from aicophilosopher.application.orchestration.coordinator import ProjectCoordinatorAgent


@pytest.fixture
def coordinator() -> ProjectCoordinatorAgent:
    return ProjectCoordinatorAgent(project_id="test-proj-1")


@pytest.mark.asyncio
async def test_clarification_turns_under_five(coordinator: ProjectCoordinatorAgent) -> None:
    """AC-001: ≤5 clarification turns before goal approval."""
    result = await coordinator.run(command="start", user_input="")
    assert result["dialogue_state"] in ("awaiting_question", "clarifying")

    for i in range(5):
        result = coordinator._start_dialogue(f"Response number {i + 1}")
        if result["dialogue_state"] == "goal_proposed":
            break

    assert result["dialogue_state"] == "goal_proposed", (
        f"Should reach goal_proposed within 5 turns, got state={result['dialogue_state']} at turn={result['turn']}"
    )
    assert result["turn"] <= 5, f"Exceeded 5 turns: {result['turn']}"


@pytest.mark.asyncio
async def test_goal_approval_transition(coordinator: ProjectCoordinatorAgent) -> None:
    """After user approves, refined_goals contains approved goal."""
    for _ in range(5):
        result = coordinator._start_dialogue("test")
        if result["dialogue_state"] == "goal_proposed":
            break

    result = coordinator._handle_approve_goal()
    assert result["dialogue_state"] == "goals_approved"
    assert result.get("approved_goal") is not None
    assert coordinator.get_dialogue_state() == "goals_approved"


@pytest.mark.asyncio
async def test_workstream_proposal_after_goal_approved(coordinator: ProjectCoordinatorAgent) -> None:
    """start_workstream returns structured proposal."""
    for _ in range(5):
        result = coordinator._start_dialogue("test")
        if result["dialogue_state"] == "goal_proposed":
            break
    coordinator._handle_approve_goal()

    result = await coordinator._handle_propose_workstream("literature_search")
    assert "proposal" in result
    assert result["proposal"]["type"] == "literature_search"
    assert result["proposal"]["goal"] is not None


@pytest.mark.asyncio
async def test_workstream_proposal_before_goal_approved_raises(coordinator: ProjectCoordinatorAgent) -> None:
    """start_workstream before goal approval raises error."""
    result = await coordinator._handle_propose_workstream("literature_search")
    assert "error" in result
    assert "no approved goals" in result["error"].lower()
