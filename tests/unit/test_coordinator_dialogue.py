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


@pytest.mark.asyncio
async def test_synthesize_goal_reflects_dialogue_history(
    coordinator: ProjectCoordinatorAgent,
) -> None:
    """_synthesize_goal incorporates the research question and clarification answers."""
    turns = [
        "What is the nature of free will?",
        "Analytic philosophy and action theory",
        "agency, moral responsibility, determinism",
        "A clear map of compatibilist vs libertarian positions",
        "Frankfurt, Strawson, and van Inwagen",
    ]
    result: dict = {}
    for turn in turns:
        result = await coordinator.run(turn)

    assert result["dialogue_state"] == "goal_proposed"
    goal = result["proposed_goal"]
    assert "What is the nature of free will" in goal
    assert "Analytic philosophy and action theory" in goal
    assert "agency, moral responsibility, determinism" in goal
    assert "compatibilist vs libertarian" in goal
    assert "Frankfurt" in goal
    assert "living document" in goal


def test_synthesize_goal_empty_history_uses_default(
    coordinator: ProjectCoordinatorAgent,
) -> None:
    """Empty dialogue_history falls back to the default goal template."""
    goal = coordinator._synthesize_goal()
    assert "philosophical question" in goal
    assert "living document" in goal


def test_synthesize_goal_single_question_only(
    coordinator: ProjectCoordinatorAgent,
) -> None:
    """A lone research question is still reflected without aspect constraints."""
    coordinator.dialogue_history = [
        {"role": "user", "content": "Is knowledge justified true belief?"},
    ]
    goal = coordinator._synthesize_goal()
    assert "Is knowledge justified true belief" in goal
    assert "Constraints and context from dialogue" not in goal
    assert "living document" in goal


@pytest.mark.asyncio
async def test_refine_goal_incorporates_new_input(
    coordinator: ProjectCoordinatorAgent,
) -> None:
    """refine_goal re-synthesizes using the additional user utterance."""
    for i in range(5):
        result = await coordinator.run(f"seed turn {i}: base topic free will")
        if result.get("dialogue_state") == "goal_proposed":
            break

    refined = await coordinator.run(
        command="refine_goal",
        user_input="Prefer phenomenological method over analytic reconstruction",
    )
    assert refined["dialogue_state"] == "goal_proposed"
    assert "phenomenological method" in refined["proposed_goal"]
    assert "seed turn 0: base topic free will" in refined["proposed_goal"]
