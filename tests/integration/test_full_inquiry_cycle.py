"""Integration tests for full inquiry cycle — US4 (T-028)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aicophilosopher.domain.entities.session import SessionState


@pytest.fixture
def mock_coordinator() -> MagicMock:
    coord = MagicMock()
    coord.run = AsyncMock(
        return_value={
            "message": "Goal refined.",
            "dialogue_state": "goal_proposed",
            "turn": 1,
        }
    )
    return coord


@pytest.fixture
def test_session() -> SessionState:
    return SessionState(project_id="proj-001")


@pytest.mark.asyncio
async def test_coordinator_adapter_start_inquiry(
    mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    from aicophilosopher.presentation.repl import _route_to_coordinator

    result = await _route_to_coordinator(
        "start_inquiry", "explore free will", mock_coordinator, test_session
    )
    mock_coordinator.run.assert_called_once()
    assert "dialogue_state" in result


@pytest.mark.asyncio
async def test_coordinator_adapter_steer(
    mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    from aicophilosopher.presentation.repl import _route_to_coordinator

    result = await _route_to_coordinator(
        "steer_workstream", "focus on compatibilism", mock_coordinator, test_session
    )
    mock_coordinator.run.assert_called_once()


@pytest.mark.asyncio
async def test_workstream_poller_flush() -> None:
    from aicophilosopher.presentation.repl import WorkstreamPoller

    poller = WorkstreamPoller("s1")
    poller.start()
    updates = poller.flush()
    assert updates == []
    poller.stop()
