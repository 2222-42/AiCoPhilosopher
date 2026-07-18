"""Unit tests for FileSystemAdapter session StoragePort methods (Issue #61)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aicophilosopher.infrastructure.adapters.filesystem_adapter import FileSystemAdapter


@pytest.fixture
def adapter(tmp_path: Path) -> FileSystemAdapter:
    return FileSystemAdapter(base_path=str(tmp_path))


def _session(
    sid: str = "s-001",
    project_id: str = "proj-001",
    status: str = "active",
    pid: int = 1,
    **extra: object,
) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    data: dict[str, object] = {
        "session_id": sid,
        "project_id": project_id,
        "status": status,
        "pid": pid,
        "heartbeat_at": now,
        "created_at": now,
        "last_active_at": now,
        "exit_reason": None,
        "active_workstreams_json": "[]",
        "config_snapshot_json": "{}",
        "focus_json": "{}",
    }
    data.update(extra)
    return data


@pytest.mark.asyncio
async def test_save_and_load_session(adapter: FileSystemAdapter) -> None:
    await adapter.save_session(_session(config_snapshot_json='{"k": 1}'))
    loaded = await adapter.load_session("proj-001")
    assert loaded is not None
    assert loaded["session_id"] == "s-001"
    assert loaded["config_snapshot_json"] == '{"k": 1}'


@pytest.mark.asyncio
async def test_load_session_skips_closed(adapter: FileSystemAdapter) -> None:
    await adapter.save_session(_session(status="closed"))
    assert await adapter.load_session("proj-001") is None


@pytest.mark.asyncio
async def test_load_session_prefers_most_recent(adapter: FileSystemAdapter) -> None:
    older = _session(sid="s-old", last_active_at="2020-01-01T00:00:00+00:00")
    newer = _session(sid="s-new", last_active_at="2026-01-01T00:00:00+00:00")
    await adapter.save_session(older)
    await adapter.save_session(newer)
    loaded = await adapter.load_session("proj-001")
    assert loaded is not None
    assert loaded["session_id"] == "s-new"


@pytest.mark.asyncio
async def test_finalize_session(adapter: FileSystemAdapter) -> None:
    await adapter.save_session(_session())
    await adapter.finalize_session("s-001", "user_exit")
    loaded = await adapter.load_session("proj-001")
    assert loaded is not None
    assert loaded["status"] == "paused"
    assert loaded["exit_reason"] == "user_exit"


@pytest.mark.asyncio
async def test_update_heartbeat(adapter: FileSystemAdapter) -> None:
    await adapter.save_session(
        _session(heartbeat_at="2020-01-01T00:00:00+00:00", last_active_at="2020-01-01T00:00:00+00:00")
    )
    await adapter.update_session_heartbeat("s-001")
    loaded = await adapter.load_session("proj-001")
    assert loaded is not None
    assert str(loaded["heartbeat_at"]) > "2020-01-01"


@pytest.mark.asyncio
async def test_save_dialogue_turn_appends_jsonl(adapter: FileSystemAdapter) -> None:
    await adapter.save_dialogue_turn({"turn_id": "t1", "speaker": "user", "content": "hi"}, "s-001")
    await adapter.save_dialogue_turn(
        {"turn_id": "t2", "speaker": "coordinator", "content": "hello"}, "s-001"
    )
    path = Path(adapter.base_path) / "sessions" / "s-001.turns.jsonl"
    assert path.exists()
    assert len(path.read_text(encoding="utf-8").strip().splitlines()) == 2


@pytest.mark.asyncio
async def test_approval_request_upsert_and_pending(adapter: FileSystemAdapter) -> None:
    await adapter.save_approval_request(
        {
            "request_id": "r1",
            "request_type": "workstream_proposal",
            "description": "Propose literature search on free will",
            "options": [{"index": 0, "label": "Yes"}],
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        "s-001",
    )
    await adapter.save_approval_request(
        {
            "request_id": "r2",
            "request_type": "goal_refinement",
            "description": "Refine goal statement for the inquiry",
            "options": [{"index": 0, "label": "Ok"}],
            "resolved_at": "2026-01-02T00:00:00+00:00",
            "created_at": "2026-01-01T01:00:00+00:00",
        },
        "s-001",
    )
    pending = await adapter.load_pending_approvals("s-001")
    assert len(pending) == 1
    assert pending[0]["request_id"] == "r1"

    # Upsert same id
    await adapter.save_approval_request(
        {
            "request_id": "r1",
            "request_type": "workstream_proposal",
            "description": "Updated description for the proposal",
            "options": [{"index": 0, "label": "Yes"}],
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        "s-001",
    )
    pending = await adapter.load_pending_approvals("s-001")
    assert len(pending) == 1
    assert "Updated" in str(pending[0]["description"])


@pytest.mark.asyncio
async def test_reclaim_stale_by_dead_pid(adapter: FileSystemAdapter) -> None:
    await adapter.save_session(_session(pid=999_999_999, status="active"))
    count = await adapter.reclaim_stale_sessions()
    assert count == 1
    loaded = await adapter.load_session("proj-001")
    assert loaded is not None
    assert loaded["status"] == "paused"
    assert loaded["exit_reason"] == "stale_reclaimed"


@pytest.mark.asyncio
async def test_reclaim_keeps_live_fresh_session(adapter: FileSystemAdapter) -> None:
    import os

    await adapter.save_session(
        _session(
            pid=os.getpid(),
            status="active",
            heartbeat_at=datetime.now(UTC).isoformat(),
        )
    )
    count = await adapter.reclaim_stale_sessions()
    assert count == 0
    loaded = await adapter.load_session("proj-001")
    assert loaded is not None
    assert loaded["status"] == "active"


@pytest.mark.asyncio
async def test_reclaim_stale_by_old_heartbeat(adapter: FileSystemAdapter) -> None:
    import os

    old = (datetime.now(UTC) - timedelta(seconds=600)).isoformat()
    await adapter.save_session(
        _session(pid=os.getpid(), status="active", heartbeat_at=old)
    )
    count = await adapter.reclaim_stale_sessions()
    assert count == 1


@pytest.mark.asyncio
async def test_list_projects_with_sessions(adapter: FileSystemAdapter) -> None:
    await adapter.save_session(_session(sid="s1", project_id="p1", status="paused"))
    await adapter.save_session(_session(sid="s2", project_id="p2", status="active"))
    projects = await adapter.list_projects_with_sessions()
    ids = {p["project_id"] for p in projects}
    assert "p1" in ids and "p2" in ids
