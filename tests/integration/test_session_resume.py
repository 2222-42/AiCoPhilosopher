"""Integration tests: session persistence across process restarts (Issue #61).

Simulates two successive process lifetimes by creating a fresh SessionManager
against the same FileSystemAdapter base path. Verifies that:
- session state (config_snapshot / workstreams / status) survives finalize
- _startup_flow reactivates a paused session with a new PID
- dialogue turns and pending approvals round-trip
- stale active sessions are reclaimed on next startup
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from aicophilosopher.domain.entities.session import (
    ApprovalOption,
    ApprovalRequest,
    ApprovalRequestType,
    DialogueTurn,
    IntentType,
    SessionStatus,
    SpeakerType,
    UserIntent,
)
from aicophilosopher.infrastructure.adapters.filesystem_adapter import FileSystemAdapter
from aicophilosopher.presentation.session_manager import SessionManager


@pytest.fixture
def storage(tmp_path: Path) -> FileSystemAdapter:
    return FileSystemAdapter(base_path=str(tmp_path))


# ── Full persist → "restart" → resume ────────────────────────────────────


@pytest.mark.asyncio
async def test_process_restart_resumes_session_with_config_snapshot(
    storage: FileSystemAdapter,
) -> None:
    """Create → work → finalize in "process 1"; load in "process 2"."""
    # ── Process 1 ────────────────────────────────────────────────────
    sm1 = SessionManager(storage=storage)
    session = await sm1.create_session("proj-restart-01")
    sid = str(session.session_id)

    session.config_snapshot = {
        "coordinator_state": {
            "turn_count": 5,
            "goal_proposed": "explore free will",
            "goal_approved": True,
            "dialogue_state": "goal_approved",
        }
    }
    session.active_workstreams = ["ws-lit-1", "ws-arg-2"]
    await sm1.save_session(session)

    # Simulate a few dialogue turns
    for i, content in enumerate(["What is free will?", "Compatibilist angle please"]):
        turn = DialogueTurn(
            speaker=SpeakerType.USER,
            content=content,
            intent=UserIntent(
                intent_type=IntentType.START_INQUIRY,
                confidence=0.9,
                raw_input=content,
            ),
        )
        await sm1.persist_turn(turn, sid)
        await sm1.update_heartbeat(sid)

    await sm1.finalize_session(sid, "user_exit")

    # ── Process 2 (new SessionManager, same storage root) ────────────
    sm2 = SessionManager(storage=storage)
    loaded = await sm2.load_session("proj-restart-01")

    assert loaded is not None
    assert loaded.status == SessionStatus.PAUSED
    assert loaded.exit_reason == "user_exit"
    assert loaded.active_workstreams == ["ws-lit-1", "ws-arg-2"]
    assert loaded.config_snapshot["coordinator_state"]["turn_count"] == 5
    assert loaded.config_snapshot["coordinator_state"]["goal_approved"] is True
    assert loaded.config_snapshot["coordinator_state"]["goal_proposed"] == "explore free will"

    # Turns were persisted independently
    turns_path = Path(storage.base_path) / "sessions" / f"{sid}.turns.jsonl"
    assert turns_path.exists()
    lines = turns_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


@pytest.mark.asyncio
async def test_startup_flow_reactivates_paused_session(
    storage: FileSystemAdapter,
) -> None:
    """_startup_flow after finalize must reactivate and re-bind PID."""
    from aicophilosopher.presentation.repl import _finalize, _startup_flow

    sm = SessionManager(storage=storage)
    session = await sm.create_session("proj-startup-01")
    session.config_snapshot = {
        "coordinator_state": {"turn_count": 3, "goal_proposed": "agency", "goal_approved": False}
    }
    await sm.save_session(session)

    # Graceful exit
    await _finalize(session, "user_exit", storage=storage)

    # Simulate process restart via startup flow
    resumed = await _startup_flow(project_id="proj-startup-01", storage=storage)
    assert resumed is not None
    assert resumed.status == SessionStatus.ACTIVE
    assert resumed.pid == os.getpid()
    assert resumed.config_snapshot["coordinator_state"]["turn_count"] == 3
    assert resumed.session_id == session.session_id


@pytest.mark.asyncio
async def test_pending_approvals_survive_restart(storage: FileSystemAdapter) -> None:
    sm1 = SessionManager(storage=storage)
    session = await sm1.create_session("proj-appr-01")
    sid = str(session.session_id)

    req = ApprovalRequest(
        request_type=ApprovalRequestType.WORKSTREAM_PROPOSAL,
        description="Propose literature search on compatibilism",
        options=[
            ApprovalOption(index=0, label="Accept"),
            ApprovalOption(index=1, label="Reject"),
        ],
    )
    await sm1.save_approval_request(req, sid)
    await sm1.finalize_session(sid, "user_exit")

    sm2 = SessionManager(storage=storage)
    pending = await sm2.load_pending_approvals(sid)
    assert len(pending) == 1
    assert pending[0]["request_type"] == "workstream_proposal"


@pytest.mark.asyncio
async def test_stale_session_reclaimed_on_next_startup(
    storage: FileSystemAdapter,
) -> None:
    """Active session with dead PID / old heartbeat is reclaimed."""
    sm = SessionManager(storage=storage)
    session = await sm.create_session("proj-stale-01")
    sid = str(session.session_id)

    # Force a dead PID and expired heartbeat
    old_hb = (datetime.now(UTC) - timedelta(seconds=600)).isoformat()
    raw = await storage.load_session("proj-stale-01")
    assert raw is not None
    raw["pid"] = 999_999_999  # almost certainly not running
    raw["heartbeat_at"] = old_hb
    raw["status"] = "active"
    await storage.save_session(raw)

    count = await sm.reclaim_stale_sessions()
    assert count >= 1

    loaded = await sm.load_session("proj-stale-01")
    assert loaded is not None
    assert loaded.status == SessionStatus.PAUSED
    assert loaded.exit_reason == "stale_reclaimed"
    assert str(loaded.session_id) == sid


@pytest.mark.asyncio
async def test_list_projects_with_sessions_after_work(
    storage: FileSystemAdapter,
) -> None:
    sm = SessionManager(storage=storage)
    s1 = await sm.create_session("proj-a")
    await sm.finalize_session(str(s1.session_id), "user_exit")
    await sm.create_session("proj-b")

    projects = await sm.list_projects()
    ids = {p["project_id"] for p in projects}
    assert "proj-a" in ids
    assert "proj-b" in ids

    by_id = {p["project_id"]: p for p in projects}
    assert by_id["proj-a"]["session_status"] == "paused"
    assert by_id["proj-b"]["session_status"] == "active"


@pytest.mark.asyncio
async def test_heartbeat_updates_last_active(storage: FileSystemAdapter) -> None:
    sm = SessionManager(storage=storage)
    session = await sm.create_session("proj-hb-01")
    sid = str(session.session_id)

    before = await storage.load_session("proj-hb-01")
    assert before is not None
    await sm.update_heartbeat(sid)
    after = await storage.load_session("proj-hb-01")
    assert after is not None
    assert after.get("heartbeat_at") is not None
    # last_active_at should also be refreshed
    assert after.get("last_active_at") is not None


@pytest.mark.asyncio
async def test_create_session_sets_live_pid(storage: FileSystemAdapter) -> None:
    sm = SessionManager(storage=storage)
    session = await sm.create_session("proj-pid-01")
    assert session.pid == os.getpid()
    assert session.status == SessionStatus.ACTIVE

    raw = await storage.load_session("proj-pid-01")
    assert raw is not None
    assert int(raw["pid"]) == os.getpid()  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_closed_sessions_are_not_loaded(storage: FileSystemAdapter) -> None:
    sm = SessionManager(storage=storage)
    await sm.create_session("proj-closed-01")
    raw = await storage.load_session("proj-closed-01")
    assert raw is not None
    raw["status"] = "closed"
    await storage.save_session(raw)

    loaded = await sm.load_session("proj-closed-01")
    assert loaded is None


@pytest.mark.asyncio
async def test_sqlite_adapter_session_round_trip(tmp_path: Path) -> None:
    """SQLite backend also implements StoragePort session methods."""
    from aicophilosopher.infrastructure.adapters.sqlite_adapter import SQLiteAdapter

    db = tmp_path / "sessions.db"
    adapter = SQLiteAdapter(str(db))
    await adapter.initialize()

    sm = SessionManager(storage=adapter)
    session = await sm.create_session("proj-sql-01")
    session.config_snapshot = {"coordinator_state": {"turn_count": 2}}
    session.active_workstreams = ["ws-1"]
    await sm.save_session(session)

    turn = DialogueTurn(
        turn_id=uuid4(),
        speaker=SpeakerType.USER,
        content="hello sqlite",
        intent=UserIntent(
            intent_type=IntentType.ASK_QUESTION,
            confidence=0.8,
            raw_input="hello sqlite",
        ),
    )
    await sm.persist_turn(turn, str(session.session_id))
    await sm.finalize_session(str(session.session_id), "user_exit")

    loaded = await sm.load_session("proj-sql-01")
    assert loaded is not None
    assert loaded.status == SessionStatus.PAUSED
    assert loaded.exit_reason == "user_exit"
    assert loaded.active_workstreams == ["ws-1"]
    assert loaded.config_snapshot["coordinator_state"]["turn_count"] == 2
