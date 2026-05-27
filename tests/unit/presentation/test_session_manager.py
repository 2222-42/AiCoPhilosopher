"""Unit tests for SessionManager persistence (T-015)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from aicophilosopher.domain.entities.session import (
    ActionTaken,
    ActionType,
    ApprovalOption,
    ApprovalRequest,
    ApprovalRequestType,
    DialogueTurn,
    IntentType,
    SessionStatus,
    SpeakerType,
    UserIntent,
)


@pytest.fixture
def mock_storage() -> MagicMock:
    storage = MagicMock()
    storage.save_session = AsyncMock()
    storage.load_session = AsyncMock()
    storage.list_projects_with_sessions = AsyncMock()
    storage.reclaim_stale_sessions = AsyncMock()
    storage.save_dialogue_turn = AsyncMock()
    storage.save_approval_request = AsyncMock()
    storage.load_pending_approvals = AsyncMock()
    storage.update_session_heartbeat = AsyncMock()
    storage.finalize_session = AsyncMock()
    return storage


# ── Create session ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_session(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager(storage=mock_storage)
    session = await sm.create_session("proj-001")
    assert session.project_id == "proj-001"
    assert session.status == SessionStatus.ACTIVE
    assert session.pid > 0
    mock_storage.save_session.assert_called_once()


# ── Persist dialogue turn ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_persist_user_turn(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager(storage=mock_storage)
    intent = UserIntent(intent_type=IntentType.START_INQUIRY, confidence=0.9, raw_input="hello")
    turn = DialogueTurn(speaker=SpeakerType.USER, content="hello", intent=intent)
    await sm.persist_turn(turn, "s1")
    mock_storage.save_dialogue_turn.assert_called_once()


@pytest.mark.asyncio
async def test_persist_coordinator_turn(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager(storage=mock_storage)
    action = ActionTaken(action_type=ActionType.LAUNCHED_WORKSTREAM, description="started")
    turn = DialogueTurn(speaker=SpeakerType.COORDINATOR, content="launched", actions_taken=[action])
    await sm.persist_turn(turn, "s1")
    mock_storage.save_dialogue_turn.assert_called_once()


# ── Finalize session ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_finalize_session(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager(storage=mock_storage)
    await sm.finalize_session("s1", "user_exit")
    mock_storage.finalize_session.assert_called_once_with("s1", "user_exit")


# ── Load session ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_load_session(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    mock_storage.load_session.return_value = {
        "session_id": str(uuid4()),
        "project_id": "proj-001",
        "status": "paused",
        "pid": 12345,
        "heartbeat_at": datetime.now(UTC).isoformat(),
        "focus_json": "{}",
        "active_workstreams_json": "[]",
        "exit_reason": "user_exit",
        "config_snapshot_json": "{}",
        "created_at": datetime.now(UTC).isoformat(),
        "last_active_at": datetime.now(UTC).isoformat(),
    }
    sm = SessionManager(storage=mock_storage)
    session = await sm.load_session("proj-001")
    assert session is not None
    assert session.project_id == "proj-001"


@pytest.mark.asyncio
async def test_load_session_not_found(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    mock_storage.load_session.return_value = None
    sm = SessionManager(storage=mock_storage)
    session = await sm.load_session("nonexistent")
    assert session is None


# ── List projects ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_projects(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    mock_storage.list_projects_with_sessions.return_value = [
        {
            "project_id": "p1",
            "title": "Test",
            "last_active_at": "2026-01-01",
            "session_status": "paused",
        },
        {
            "project_id": "p2",
            "title": "Other",
            "last_active_at": "2026-01-02",
            "session_status": "active",
        },
    ]
    sm = SessionManager(storage=mock_storage)
    projects = await sm.list_projects()
    assert len(projects) >= 2


# ── Reclaim stale sessions ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reclaim_stale_sessions(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    mock_storage.reclaim_stale_sessions.return_value = 3
    sm = SessionManager(storage=mock_storage)
    count = await sm.reclaim_stale_sessions()
    assert count == 3


# ── Heartbeat ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_heartbeat(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager(storage=mock_storage)
    await sm.update_heartbeat("s1")
    mock_storage.update_session_heartbeat.assert_called_once_with("s1")


# ── Approval requests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_approval_request(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager(storage=mock_storage)
    req = ApprovalRequest(
        request_type=ApprovalRequestType.WORKSTREAM_PROPOSAL,
        description="Propose literature search",
        options=[ApprovalOption(index=0, label="Accept")],
    )
    await sm.save_approval_request(req, "s1")
    mock_storage.save_approval_request.assert_called_once()


@pytest.mark.asyncio
async def test_load_pending_approvals(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    mock_storage.load_pending_approvals.return_value = [
        {
            "request_id": str(uuid4()),
            "request_type": "workstream_proposal",
            "description": "test" * 3,
        }
    ]
    sm = SessionManager(storage=mock_storage)
    pending = await sm.load_pending_approvals("s1")
    assert len(pending) == 1


# ── Context blocks ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_and_load_context_block() -> None:
    """Context blocks can be persisted and loaded."""
    # This requires integrated StoragePort — skipped for now, covered in T-018
    pass


# ── Concurrent session detection ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_is_active_session_live(mock_storage: MagicMock) -> None:
    import os

    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager(storage=mock_storage)
    # Our own PID should be alive
    result = await sm.is_active_session_live(os.getpid())
    assert result is True


@pytest.mark.asyncio
async def test_is_active_session_dead(mock_storage: MagicMock) -> None:
    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager(storage=mock_storage)
    # PID 99999 is almost certainly not running
    result = await sm.is_active_session_live(99999)
    assert result is False
