"""Integration tests for session persistence and resume (T-018)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aicophilosopher.domain.entities.session import SessionState, SessionStatus


@pytest.fixture
def mock_storage() -> MagicMock:
    storage = MagicMock()
    storage.save_session = AsyncMock()
    storage.load_session = AsyncMock()
    storage.list_projects_with_sessions = AsyncMock(return_value=[])
    storage.reclaim_stale_sessions = AsyncMock(return_value=0)
    storage.save_dialogue_turn = AsyncMock()
    storage.finalize_session = AsyncMock()
    storage.update_session_heartbeat = AsyncMock()
    return storage


@pytest.fixture
def test_session() -> SessionState:
    return SessionState(project_id="proj-001")


@pytest.mark.asyncio
async def test_create_and_finalize_session(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager(storage=mock_storage)
    session = await sm.create_session("proj-001")
    assert session.status == SessionStatus.ACTIVE
    await sm.finalize_session(str(session.session_id), "user_exit")
    mock_storage.finalize_session.assert_called_once()


@pytest.mark.asyncio
async def test_session_workstream_survival() -> None:
    """Workstreams continue running after session exit."""
    session = SessionState(project_id="proj-001", active_workstreams=["ws-001"])
    session.status = SessionStatus.PAUSED
    assert "ws-001" in session.active_workstreams
    assert session.status == SessionStatus.PAUSED


@pytest.mark.asyncio
async def test_pending_approval_survival() -> None:
    """Pending approvals survive session restart."""
    from aicophilosopher.domain.entities.session import (
        ApprovalOption,
        ApprovalRequest,
        ApprovalRequestType,
    )

    req = ApprovalRequest(
        request_type=ApprovalRequestType.WORKSTREAM_PROPOSAL,
        description="Propose literature search on compatibilism",
        options=[ApprovalOption(index=0, label="Accept")],
    )
    session = SessionState(project_id="p1", approval_requests=[req])
    assert len(session.approval_requests) == 1


@pytest.mark.asyncio
async def test_stale_reclaim_on_startup(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    mock_storage.reclaim_stale_sessions.return_value = 2
    sm = SessionManager(storage=mock_storage)
    count = await sm.reclaim_stale_sessions()
    assert count == 2


@pytest.mark.asyncio
async def test_heartbeat_updated(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager(storage=mock_storage)
    await sm.update_heartbeat("s1")
    mock_storage.update_session_heartbeat.assert_called_once_with("s1")
