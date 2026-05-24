"""Unit tests for SQLite session schema creation and constraints (T-006)."""

import json
from pathlib import Path

import pytest

from aicophilosopher.infrastructure.adapters.sqlite_adapter import SQLiteAdapter


@pytest.fixture
async def adapter(tmp_path: Path) -> SQLiteAdapter:
    db = tmp_path / "test.db"
    ad = SQLiteAdapter(str(db))
    await ad.initialize()
    return ad


async def _table_exists(adapter: SQLiteAdapter, table: str) -> bool:
    conn = await adapter._connect()
    try:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        )
        row = await cursor.fetchone()
        return row is not None
    finally:
        await conn.close()


async def _execute(adapter: SQLiteAdapter, sql: str, params: tuple = ()) -> None:
    conn = await adapter._connect()
    try:
        await conn.execute(sql, params)
        await conn.commit()
    finally:
        await conn.close()


# ── Table existence ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sessions_table_exists(adapter: SQLiteAdapter) -> None:
    assert await _table_exists(adapter, "sessions")


@pytest.mark.asyncio
async def test_approval_requests_table_exists(adapter: SQLiteAdapter) -> None:
    assert await _table_exists(adapter, "approval_requests")


@pytest.mark.asyncio
async def test_dialogue_turns_table_exists(adapter: SQLiteAdapter) -> None:
    assert await _table_exists(adapter, "dialogue_turns")


@pytest.mark.asyncio
async def test_context_blocks_table_exists(adapter: SQLiteAdapter) -> None:
    assert await _table_exists(adapter, "context_blocks")


# ── One-active-session per project constraint ───────────────────────────


@pytest.mark.asyncio
async def test_one_active_session_per_project(adapter: SQLiteAdapter) -> None:
    await _execute(
        adapter,
        "INSERT INTO projects (project_id, title, original_question) VALUES (?, ?, ?)",
        ("p1", "Test", "q"),
    )
    await _execute(
        adapter,
        "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
        ("s1", "p1", "active"),
    )
    import aiosqlite

    with pytest.raises(aiosqlite.IntegrityError):
        await _execute(
            adapter,
            "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
            ("s2", "p1", "active"),
        )


@pytest.mark.asyncio
async def test_two_paused_sessions_same_project_ok(adapter: SQLiteAdapter) -> None:
    """Multiple non-active sessions for the same project are allowed."""
    await _execute(
        adapter,
        "INSERT INTO projects (project_id, title, original_question) VALUES (?, ?, ?)",
        ("p1", "Test", "q"),
    )
    await _execute(
        adapter,
        "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
        ("s1", "p1", "paused"),
    )
    await _execute(
        adapter,
        "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
        ("s2", "p1", "paused"),
    )


# ── Foreign key cascade ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_project_cascades_to_sessions(adapter: SQLiteAdapter) -> None:
    await _execute(
        adapter,
        "INSERT INTO projects (project_id, title, original_question) VALUES (?, ?, ?)",
        ("p1", "Test", "q"),
    )
    await _execute(
        adapter,
        "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
        ("s1", "p1", "active"),
    )
    await _execute(adapter, "DELETE FROM projects WHERE project_id = ?", ("p1",))
    conn = await adapter._connect()
    try:
        cursor = await conn.execute("SELECT * FROM sessions WHERE session_id = ?", ("s1",))
        row = await cursor.fetchone()
        assert row is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_delete_session_cascades_to_dialogue_turns(adapter: SQLiteAdapter) -> None:
    await _execute(
        adapter,
        "INSERT INTO projects (project_id, title, original_question) VALUES (?, ?, ?)",
        ("p1", "Test", "q"),
    )
    await _execute(
        adapter,
        "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
        ("s1", "p1", "active"),
    )
    await _execute(
        adapter,
        "INSERT INTO dialogue_turns (turn_id, session_id, speaker, content) VALUES (?, ?, ?, ?)",
        ("t1", "s1", "user", "hello"),
    )
    await _execute(adapter, "DELETE FROM sessions WHERE session_id = ?", ("s1",))
    conn = await adapter._connect()
    try:
        cursor = await conn.execute("SELECT * FROM dialogue_turns WHERE turn_id = ?", ("t1",))
        row = await cursor.fetchone()
        assert row is None
    finally:
        await conn.close()


# ── Schema idempotency ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_schema_is_idempotent(adapter: SQLiteAdapter) -> None:
    """Calling initialize() twice should not error."""
    await adapter.initialize()


# ── Timestamp ordering ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dialogue_turns_returned_in_timestamp_order(adapter: SQLiteAdapter) -> None:
    await _execute(
        adapter,
        "INSERT INTO projects (project_id, title, original_question) VALUES (?, ?, ?)",
        ("p1", "Test", "q"),
    )
    await _execute(
        adapter,
        "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
        ("s1", "p1", "active"),
    )
    await _execute(
        adapter,
        "INSERT INTO dialogue_turns (turn_id, session_id, speaker, content, timestamp) VALUES (?, ?, ?, ?, datetime('now', '-1 seconds'))",
        ("t1", "s1", "user", "first"),
    )
    await _execute(
        adapter,
        "INSERT INTO dialogue_turns (turn_id, session_id, speaker, content, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
        ("t2", "s1", "coordinator", "second"),
    )
    conn = await adapter._connect()
    try:
        cursor = await conn.execute(
            "SELECT turn_id FROM dialogue_turns WHERE session_id = ? ORDER BY timestamp ASC, turn_id ASC",
            ("s1",),
        )
        rows = await cursor.fetchall()
        assert [r["turn_id"] for r in rows] == ["t1", "t2"]
    finally:
        await conn.close()


# ── Approval requests JSON round-trip ───────────────────────────────────


@pytest.mark.asyncio
async def test_approval_options_json_round_trip(adapter: SQLiteAdapter) -> None:
    await _execute(
        adapter,
        "INSERT INTO projects (project_id, title, original_question) VALUES (?, ?, ?)",
        ("p1", "Test", "q"),
    )
    await _execute(
        adapter,
        "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
        ("s1", "p1", "active"),
    )
    opts = [{"index": 0, "label": "Accept", "description": "ok"}]
    await _execute(
        adapter,
        "INSERT INTO approval_requests (request_id, session_id, request_type, description, options_json) VALUES (?, ?, ?, ?, ?)",
        ("r1", "s1", "workstream_proposal", "Propose literature search", json.dumps(opts)),
    )
    conn = await adapter._connect()
    try:
        cursor = await conn.execute(
            "SELECT options_json FROM approval_requests WHERE request_id = ?", ("r1",)
        )
        row = await cursor.fetchone()
        assert row is not None
        loaded = json.loads(row["options_json"])
        assert loaded[0]["label"] == "Accept"
    finally:
        await conn.close()


# ── Pending approval filter ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pending_approvals_queried_by_null_resolved_at(adapter: SQLiteAdapter) -> None:
    await _execute(
        adapter,
        "INSERT INTO projects (project_id, title, original_question) VALUES (?, ?, ?)",
        ("p1", "Test", "q"),
    )
    await _execute(
        adapter,
        "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
        ("s1", "p1", "active"),
    )
    await _execute(
        adapter,
        "INSERT INTO approval_requests (request_id, session_id, request_type, description, options_json) VALUES (?, ?, ?, ?, ?)",
        ("r1", "s1", "workstream_proposal", "Pending request", "[]"),
    )
    await _execute(
        adapter,
        "INSERT INTO approval_requests (request_id, session_id, request_type, description, options_json, resolved_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
        ("r2", "s1", "goal_refinement", "Resolved request", "[]"),
    )
    conn = await adapter._connect()
    try:
        cursor = await conn.execute(
            "SELECT request_id FROM approval_requests WHERE resolved_at IS NULL"
        )
        rows = await cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["request_id"] == "r1"
    finally:
        await conn.close()


# ── Session status values ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_session_status_check_constraint(adapter: SQLiteAdapter) -> None:
    await _execute(
        adapter,
        "INSERT INTO projects (project_id, title, original_question) VALUES (?, ?, ?)",
        ("p1", "Test", "q"),
    )
    import aiosqlite

    with pytest.raises(aiosqlite.IntegrityError):
        await _execute(
            adapter,
            "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
            ("s1", "p1", "invalid_status"),
        )


# ── Speaker type check ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dialogue_turn_speaker_check_constraint(adapter: SQLiteAdapter) -> None:
    await _execute(
        adapter,
        "INSERT INTO projects (project_id, title, original_question) VALUES (?, ?, ?)",
        ("p1", "Test", "q"),
    )
    await _execute(
        adapter,
        "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
        ("s1", "p1", "active"),
    )
    import aiosqlite

    with pytest.raises(aiosqlite.IntegrityError):
        await _execute(
            adapter,
            "INSERT INTO dialogue_turns (turn_id, session_id, speaker, content) VALUES (?, ?, ?, ?)",
            ("t1", "s1", "invalid_speaker", "x"),
        )


# ── Index usage (EXPLAIN QUERY PLAN) ────────────────────────────────────


@pytest.mark.asyncio
async def test_filtered_index_used_for_pending_approvals(adapter: SQLiteAdapter) -> None:
    await _execute(
        adapter,
        "INSERT INTO projects (project_id, title, original_question) VALUES (?, ?, ?)",
        ("p1", "Test", "q"),
    )
    await _execute(
        adapter,
        "INSERT INTO sessions (session_id, project_id, status) VALUES (?, ?, ?)",
        ("s1", "p1", "active"),
    )
    await _execute(
        adapter,
        "INSERT INTO approval_requests (request_id, session_id, request_type, description, options_json) VALUES (?, ?, ?, ?, ?)",
        ("r1", "s1", "workstream_proposal", "Pending request", "[]"),
    )
    await _execute(
        adapter,
        "INSERT INTO approval_requests (request_id, session_id, request_type, description, options_json, resolved_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
        ("r2", "s1", "goal_refinement", "Resolved request", "[]"),
    )
    conn = await adapter._connect()
    try:
        cursor = await conn.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM approval_requests WHERE session_id = ? AND resolved_at IS NULL",
            ("s1",),
        )
        rows = await cursor.fetchall()
        plan = "\n".join(str(dict(r)) for r in rows)
        assert "idx_approval_requests_pending" in plan
    finally:
        await conn.close()
