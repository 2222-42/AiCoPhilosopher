import json
from typing import Any

import aiosqlite

CREATE_PROJECTS = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    original_question TEXT NOT NULL,
    status TEXT DEFAULT 'created' CHECK (status IN ('created','clarifying','goals_approved','active','paused','completed','archived')),
    living_document TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}',
    external_layer_config_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

CREATE_WORKSTREAMS = """
CREATE TABLE IF NOT EXISTS workstreams (
    workstream_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('literature_search','concept_analysis','cross_traditional_comparison','argumentation','critical_review','phenomenological_description','ethical_analysis','synthesis')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','running','paused','completed','failed','stalled')),
    goal_statement_json TEXT NOT NULL,
    assigned_coordinator TEXT NOT NULL,
    assigned_sub_agents_json TEXT DEFAULT '[]',
    results TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

CREATE_HYPOTHESES = """
CREATE TABLE IF NOT EXISTS hypotheses (
    hypothesis_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    statement TEXT NOT NULL,
    strength TEXT CHECK (strength IN ('strong','moderate','weak','refuted','underdetermined')),
    origin TEXT CHECK (origin IN ('user','ai','joint','cross_tradition_synthesis')),
    status TEXT CHECK (status IN ('active','abandoned','refined','refuted')),
    epistemic_tradition TEXT,
    confidence_score REAL CHECK (confidence_score>=0.0 AND confidence_score<=1.0),
    supporting_evidence_json TEXT DEFAULT '[]',
    counter_arguments_json TEXT DEFAULT '[]',
    dialectical_children_json TEXT DEFAULT '[]',
    abandonment_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    abandoned_at TIMESTAMP
)"""

CREATE_UNCERTAINTY = """
CREATE TABLE IF NOT EXISTS uncertainty_registry (
    claim_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    confidence_score REAL NOT NULL CHECK (confidence_score>=0.0 AND confidence_score<=1.0),
    counter_argument_strength REAL DEFAULT 0.0 CHECK (counter_argument_strength>=0.0 AND counter_argument_strength<=1.0),
    tradition_validity_json TEXT DEFAULT '{}',
    review_status TEXT DEFAULT 'unreviewed' CHECK (review_status IN ('unreviewed','under_review','contested','accepted_with_reservations','rejected')),
    stalled_sections_json TEXT DEFAULT '[]',
    source_workstream TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    sender_id TEXT NOT NULL,
    recipient_id TEXT NOT NULL,
    message_type TEXT NOT NULL CHECK (message_type IN ('status_update','delegation_request','delegation_response','steering_command','steering_ack','help_request','help_response','review_request','review_response','result_delivery','error_notification','user_notification')),
    payload_json TEXT DEFAULT '{}',
    epistemic_status_json TEXT DEFAULT '{}',
    correlation_id TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered INTEGER DEFAULT 0,
    archived INTEGER DEFAULT 0
)"""

CREATE_REVIEW_ROUNDS = """
CREATE TABLE IF NOT EXISTS review_rounds (
    round_id TEXT PRIMARY KEY,
    workstream_id TEXT NOT NULL REFERENCES workstreams(workstream_id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL CHECK (round_number>=1),
    verdicts_json TEXT DEFAULT '[]',
    revision_request TEXT,
    status TEXT CHECK (status IN ('in_progress','completed','escalated')),
    escalated_to_coordinator INTEGER DEFAULT 0,
    escalation_reason TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
)"""

CREATE_ARTIFACTS = """
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    artifact_type TEXT CHECK (artifact_type IN ('uploaded_pdf','generated_latex','generated_markdown','code_script','data_file','simulation_result')),
    uploaded_by TEXT NOT NULL,
    description TEXT,
    mime_type TEXT,
    size_bytes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

CREATE_NOTES = """
CREATE TABLE IF NOT EXISTS notes (
    note_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    attach_to TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

# ── 002-console-agent session tables ─────────────────────────────────────

CREATE_SESSIONS = """\
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'closed')),
    pid INTEGER,
    heartbeat_at TIMESTAMP,
    focus_json TEXT DEFAULT '{}',
    active_workstreams_json TEXT DEFAULT '[]',
    exit_reason TEXT,
    config_snapshot_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

CREATE_APPROVAL_REQUESTS = """\
CREATE TABLE IF NOT EXISTS approval_requests (
    request_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    request_type TEXT NOT NULL CHECK (request_type IN (
        'workstream_proposal', 'normative_judgment', 'incommensurability_resolution',
        'review_escalation', 'external_search_consent', 'synthesis_conflict', 'goal_refinement'
    )),
    description TEXT NOT NULL,
    options_json TEXT NOT NULL DEFAULT '[]',
    urgency TEXT DEFAULT 'non_blocking' CHECK (urgency IN ('blocking', 'non_blocking')),
    resolved_at TIMESTAMP,
    user_choice INTEGER,
    user_comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

CREATE_DIALOGUE_TURNS = """\
CREATE TABLE IF NOT EXISTS dialogue_turns (
    turn_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    speaker TEXT NOT NULL CHECK (speaker IN ('user', 'coordinator', 'system')),
    content TEXT NOT NULL,
    intent_json TEXT,
    actions_json TEXT,
    context_id TEXT,
    approved_by_user BOOLEAN,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)"""

CREATE_CONTEXT_BLOCKS = """\
CREATE TABLE IF NOT EXISTS context_blocks (
    context_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    summary TEXT DEFAULT '',
    parent_context TEXT,
    epistemic_snapshot_json TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP
)"""

# ── 002-console-agent session indexes ────────────────────────────────────

SESSION_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_one_active ON sessions(project_id) WHERE status = 'active'",
    "CREATE INDEX IF NOT EXISTS idx_approval_requests_session ON approval_requests(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_approval_requests_pending ON approval_requests(session_id) WHERE resolved_at IS NULL",
    "CREATE INDEX IF NOT EXISTS idx_dialogue_turns_session_ts ON dialogue_turns(session_id, timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_dialogue_turns_context ON dialogue_turns(context_id)",
    "CREATE INDEX IF NOT EXISTS idx_context_blocks_session ON context_blocks(session_id)",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_workstreams_project ON workstreams(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_workstreams_status ON workstreams(status)",
    "CREATE INDEX IF NOT EXISTS idx_hypotheses_project ON hypotheses(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_hypotheses_status ON hypotheses(status)",
    "CREATE INDEX IF NOT EXISTS idx_uncertainty_project ON uncertainty_registry(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_uncertainty_review ON uncertainty_registry(review_status)",
    "CREATE INDEX IF NOT EXISTS idx_messages_project ON messages(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id)",
    "CREATE INDEX IF NOT EXISTS idx_review_rounds_ws ON review_rounds(workstream_id)",
    "CREATE INDEX IF NOT EXISTS idx_notes_project ON notes(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_notes_attach ON notes(attach_to)",
]

SQL_SCHEMA = [CREATE_PROJECTS, CREATE_WORKSTREAMS, CREATE_HYPOTHESES, CREATE_UNCERTAINTY,
              CREATE_MESSAGES, CREATE_REVIEW_ROUNDS, CREATE_ARTIFACTS, CREATE_NOTES,
              CREATE_SESSIONS, CREATE_APPROVAL_REQUESTS, CREATE_DIALOGUE_TURNS,
              CREATE_CONTEXT_BLOCKS] + INDEXES + SESSION_INDEXES


class SQLiteAdapter:
    def __init__(self, db_path: str = "") -> None:
        self.db_path = db_path

    async def _connect(self) -> aiosqlite.Connection:
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        return conn

    async def initialize(self) -> None:
        conn = await self._connect()
        try:
            for stmt in SQL_SCHEMA:
                await conn.execute(stmt)
            await conn.commit()
        finally:
            await conn.close()

    async def save_project(self, project: dict[str, object]) -> str:
        conn = await self._connect()
        try:
            await conn.execute(
                """INSERT INTO projects
                   (project_id, title, original_question, status, living_document, metadata_json, external_layer_config_json, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(project_id) DO UPDATE SET
                       title=excluded.title, original_question=excluded.original_question,
                       status=excluded.status, living_document=excluded.living_document,
                       metadata_json=excluded.metadata_json,
                       external_layer_config_json=excluded.external_layer_config_json,
                       updated_at=CURRENT_TIMESTAMP""",
                (project["project_id"], project.get("title", ""),
                 project.get("original_question", ""), project.get("status", "created"),
                 project.get("living_document", ""),
                 json.dumps(project.get("metadata", {})),
                 json.dumps(project.get("external_layer_config")) if project.get("external_layer_config") else None),
            )
            await conn.commit()
            return str(project["project_id"])
        finally:
            await conn.close()

    async def load_project(self, project_id: str) -> dict[str, Any] | None:
        conn = await self._connect()
        try:
            cursor = await conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
            row = await cursor.fetchone()
            if row is None:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
            raw = d.pop("external_layer_config_json", None)
            d["external_layer_config"] = json.loads(raw) if raw else None
            d.pop("created_at", None)
            d.pop("updated_at", None)
            return d
        finally:
            await conn.close()

    async def save_workstream(self, project_id: str, workstream: dict[str, object]) -> str:
        conn = await self._connect()
        try:
            await conn.execute(
                """INSERT INTO workstreams
                   (workstream_id, project_id, type, status, goal_statement_json, assigned_coordinator,
                    assigned_sub_agents_json, results, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(workstream_id) DO UPDATE SET
                       project_id=excluded.project_id, type=excluded.type, status=excluded.status,
                       goal_statement_json=excluded.goal_statement_json,
                       assigned_coordinator=excluded.assigned_coordinator,
                       assigned_sub_agents_json=excluded.assigned_sub_agents_json,
                       results=excluded.results, updated_at=CURRENT_TIMESTAMP""",
                (workstream["workstream_id"], project_id,
                 workstream.get("type", ""), workstream.get("status", "pending"),
                 json.dumps(workstream.get("goal_statement", {})),
                 workstream.get("assigned_coordinator", ""),
                 json.dumps(workstream.get("assigned_sub_agents", [])),
                 workstream.get("results", "")),
            )
            await conn.commit()
            return str(workstream["workstream_id"])
        finally:
            await conn.close()

    async def load_workstream(self, project_id: str, workstream_id: str) -> dict[str, Any] | None:
        conn = await self._connect()
        try:
            cursor = await conn.execute(
                "SELECT * FROM workstreams WHERE workstream_id = ? AND project_id = ?",
                (workstream_id, project_id),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            d = dict(row)
            d["goal_statement"] = json.loads(d.pop("goal_statement_json", "{}"))
            d["assigned_sub_agents"] = json.loads(d.pop("assigned_sub_agents_json", "[]"))
            d.pop("created_at", None)
            d.pop("updated_at", None)
            return d
        finally:
            await conn.close()

    async def save_hypothesis(self, project_id: str, hypothesis: dict[str, object]) -> str:
        conn = await self._connect()
        try:
            await conn.execute(
                """INSERT OR REPLACE INTO hypotheses
                   (hypothesis_id, project_id, statement, strength, origin, status,
                    epistemic_tradition, confidence_score, supporting_evidence_json,
                    counter_arguments_json, dialectical_children_json, abandonment_reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (hypothesis["hypothesis_id"], project_id,
                 hypothesis.get("statement", ""),
                 str(hypothesis.get("strength", "weak")),
                 str(hypothesis.get("origin", "ai")),
                 str(hypothesis.get("status", "active")),
                 hypothesis.get("epistemic_tradition"),
                 float(hypothesis.get("confidence_score", 0.5)),  # type: ignore[arg-type]
                 json.dumps(hypothesis.get("supporting_evidence", [])),
                 json.dumps(hypothesis.get("counter_arguments", [])),
                 json.dumps(hypothesis.get("dialectical_children", [])),
                 hypothesis.get("abandonment_reason")),
            )
            await conn.commit()
            return str(hypothesis["hypothesis_id"])
        finally:
            await conn.close()

    async def load_hypotheses(self, project_id: str, **filters: object) -> list[dict[str, Any]]:
        conn = await self._connect()
        try:
            sql = "SELECT * FROM hypotheses WHERE project_id = ?"
            params: list[Any] = [project_id]
            if "status" in filters:
                sql += " AND status = ?"
                params.append(str(filters["status"]))
            if "strength" in filters:
                sql += " AND strength = ?"
                params.append(str(filters["strength"]))
            cursor = await conn.execute(sql, params)
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await conn.close()

    async def save_uncertainty(self, project_id: str, record: dict[str, object]) -> str:
        conn = await self._connect()
        try:
            await conn.execute(
                """INSERT OR REPLACE INTO uncertainty_registry
                   (claim_id, project_id, claim_text, confidence_score, counter_argument_strength,
                    tradition_validity_json, review_status, stalled_sections_json, source_workstream)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record["claim_id"], project_id,
                 record.get("claim_text", ""),
                 float(record.get("confidence_score", 0.5)),  # type: ignore[arg-type]
                 float(record.get("counter_argument_strength", 0.0)),  # type: ignore[arg-type]
                 json.dumps(record.get("tradition_validity", {})),
                 str(record.get("review_status", "unreviewed")),
                 json.dumps(record.get("stalled_sections", [])),
                 record.get("source_workstream")),
            )
            await conn.commit()
            return str(record["claim_id"])
        finally:
            await conn.close()

    async def query_uncertainty(self, project_id: str, **filters: object) -> list[dict[str, Any]]:
        conn = await self._connect()
        try:
            sql = "SELECT * FROM uncertainty_registry WHERE project_id = ?"
            params: list[Any] = [project_id]
            if "review_status" in filters:
                sql += " AND review_status = ?"
                params.append(str(filters["review_status"]))
            cursor = await conn.execute(sql, params)
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await conn.close()

    async def save_message(self, project_id: str, message: dict[str, object]) -> str:
        conn = await self._connect()
        try:
            await conn.execute(
                """INSERT INTO messages
                   (message_id, project_id, sender_id, recipient_id, message_type,
                    payload_json, epistemic_status_json, correlation_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (message["message_id"], project_id,
                 message.get("sender_id", ""),
                 message.get("recipient_id", ""),
                 message.get("message_type", ""),
                 json.dumps(message.get("payload", {})),
                 json.dumps(message.get("epistemic_status", {})),
                 message.get("correlation_id")),
            )
            await conn.commit()
            return str(message["message_id"])
        finally:
            await conn.close()

    async def query_messages(self, project_id: str, **filters: object) -> list[dict[str, Any]]:
        conn = await self._connect()
        try:
            sql = "SELECT * FROM messages WHERE project_id = ?"
            params: list[Any] = [project_id]
            if "recipient_id" in filters:
                sql += " AND recipient_id = ?"
                params.append(str(filters["recipient_id"]))
            if "message_type" in filters:
                sql += " AND message_type = ?"
                params.append(str(filters["message_type"]))
            sql += " ORDER BY timestamp ASC"
            cursor = await conn.execute(sql, params)
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await conn.close()

    async def save_review_round(self, workstream_id: str, rround: dict[str, object]) -> str:
        conn = await self._connect()
        try:
            await conn.execute(
                """INSERT OR REPLACE INTO review_rounds
                   (round_id, workstream_id, round_number, verdicts_json, revision_request,
                    status, escalated_to_coordinator, escalation_reason, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rround["round_id"], workstream_id,
                 int(str(rround.get("round_number", "1"))),
                 json.dumps(rround.get("verdicts", [])),
                 rround.get("revision_request"),
                 str(rround.get("status", "in_progress")),
                 1 if rround.get("escalated_to_coordinator") else 0,
                 rround.get("escalation_reason"),
                 rround.get("completed_at")),
            )
            await conn.commit()
            return str(rround["round_id"])
        finally:
            await conn.close()

    async def save_note(self, project_id: str, note: dict[str, object]) -> str:
        conn = await self._connect()
        try:
            await conn.execute(
                "INSERT OR REPLACE INTO notes (note_id, project_id, content, attach_to) VALUES (?, ?, ?, ?)",
                (note["note_id"], project_id,
                 note.get("content", "") or note.get("text", ""),
                 note.get("attach_to")),
            )
            await conn.commit()
            return str(note["note_id"])
        finally:
            await conn.close()

    async def load_notes(self, project_id: str, **filters: object) -> list[dict[str, Any]]:
        conn = await self._connect()
        try:
            sql = "SELECT * FROM notes WHERE project_id = ?"
            params: list[Any] = [project_id]
            if "attach_to" in filters:
                sql += " AND attach_to = ?"
                params.append(str(filters["attach_to"]))
            sql += " ORDER BY created_at ASC"
            cursor = await conn.execute(sql, params)
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await conn.close()

    async def list_projects(self) -> list[dict[str, Any]]:
        conn = await self._connect()
        try:
            cursor = await conn.execute(
                "SELECT project_id, title, status, created_at, updated_at FROM projects ORDER BY updated_at DESC"
            )
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await conn.close()

    async def delete_project(self, project_id: str) -> bool:
        conn = await self._connect()
        try:
            cursor = await conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
            await conn.commit()
            return cursor.rowcount > 0
        finally:
            await conn.close()

    # ── 002-console-agent session persistence ─────────────────────────

    HEARTBEAT_TIMEOUT_SECONDS = 300

    async def _ensure_project_stub(self, conn: aiosqlite.Connection, project_id: str) -> None:
        """Insert a minimal projects row so session FK constraints succeed."""
        await conn.execute(
            """INSERT OR IGNORE INTO projects (project_id, title, original_question)
               VALUES (?, ?, ?)""",
            (project_id, project_id, ""),
        )

    @staticmethod
    def _json_text(value: object, default: str = "{}") -> str:
        if value is None:
            return default
        if isinstance(value, str):
            return value
        return json.dumps(value)

    async def save_session(self, session: dict[str, object]) -> None:
        """Upsert session row. Auto-creates a project stub if needed."""
        sid = str(session.get("session_id", ""))
        project_id = str(session.get("project_id", ""))
        if not sid or not project_id:
            return

        focus_json = self._json_text(
            session.get("focus_json", session.get("current_focus")), "{}"
        )
        aws_json = self._json_text(
            session.get("active_workstreams_json", session.get("active_workstreams")), "[]"
        )
        cfg_json = self._json_text(
            session.get("config_snapshot_json", session.get("config_snapshot")), "{}"
        )

        conn = await self._connect()
        try:
            await self._ensure_project_stub(conn, project_id)
            await conn.execute(
                """INSERT INTO sessions
                   (session_id, project_id, status, pid, heartbeat_at, focus_json,
                    active_workstreams_json, exit_reason, config_snapshot_json,
                    created_at, last_active_at)
                   VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?, ?, ?, ?,
                           COALESCE(?, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP)
                   ON CONFLICT(session_id) DO UPDATE SET
                       project_id=excluded.project_id,
                       status=excluded.status,
                       pid=excluded.pid,
                       heartbeat_at=excluded.heartbeat_at,
                       focus_json=excluded.focus_json,
                       active_workstreams_json=excluded.active_workstreams_json,
                       exit_reason=excluded.exit_reason,
                       config_snapshot_json=excluded.config_snapshot_json,
                       last_active_at=CURRENT_TIMESTAMP""",
                (
                    sid,
                    project_id,
                    str(session.get("status", "active")),
                    int(session.get("pid") or 0),  # type: ignore[arg-type]
                    session.get("heartbeat_at"),
                    focus_json,
                    aws_json,
                    session.get("exit_reason"),
                    cfg_json,
                    session.get("created_at"),
                ),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def load_session(self, project_id: str) -> dict[str, object] | None:
        """Load the most recent non-closed session for a project."""
        conn = await self._connect()
        try:
            cursor = await conn.execute(
                """SELECT * FROM sessions
                   WHERE project_id = ? AND status != 'closed'
                   ORDER BY last_active_at DESC
                   LIMIT 1""",
                (project_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        finally:
            await conn.close()

    async def list_projects_with_sessions(self) -> list[dict[str, object]]:
        """Return projects joined with latest non-closed session status."""
        conn = await self._connect()
        try:
            cursor = await conn.execute(
                """SELECT p.project_id,
                          p.title,
                          s.status AS session_status,
                          s.last_active_at,
                          s.session_id,
                          s.active_workstreams_json
                   FROM projects p
                   LEFT JOIN sessions s
                     ON s.session_id = (
                        SELECT s2.session_id FROM sessions s2
                        WHERE s2.project_id = p.project_id
                          AND s2.status != 'closed'
                        ORDER BY s2.last_active_at DESC
                        LIMIT 1
                     )
                   ORDER BY COALESCE(s.last_active_at, p.updated_at) DESC"""
            )
            rows = await cursor.fetchall()
            result: list[dict[str, object]] = []
            for row in rows:
                d = dict(row)
                aws = d.pop("active_workstreams_json", "[]") or "[]"
                try:
                    ws = json.loads(aws) if isinstance(aws, str) else aws
                except json.JSONDecodeError:
                    ws = []
                d["workstream_count"] = len(ws) if isinstance(ws, list) else 0
                result.append(d)
            return result
        finally:
            await conn.close()

    async def reclaim_stale_sessions(self) -> int:
        """Mark active sessions with expired heartbeat as paused/stale_reclaimed."""
        import errno
        import os
        from datetime import UTC, datetime, timedelta

        conn = await self._connect()
        try:
            cursor = await conn.execute(
                "SELECT session_id, pid, heartbeat_at FROM sessions WHERE status = 'active'"
            )
            rows = await cursor.fetchall()
            now = datetime.now(UTC)
            reclaimed = 0
            for row in rows:
                sid = row["session_id"]
                stale = False
                raw_hb = row["heartbeat_at"]
                if raw_hb:
                    try:
                        hb = datetime.fromisoformat(str(raw_hb))
                        if hb.tzinfo is None:
                            hb = hb.replace(tzinfo=UTC)
                        if now - hb > timedelta(seconds=self.HEARTBEAT_TIMEOUT_SECONDS):
                            stale = True
                    except (ValueError, TypeError):
                        stale = True
                else:
                    stale = True

                pid = int(row["pid"] or 0)
                if pid > 0:
                    try:
                        os.kill(pid, 0)
                    except OSError as e:
                        if e.errno == errno.ESRCH:
                            stale = True
                else:
                    stale = True

                if stale:
                    await conn.execute(
                        """UPDATE sessions
                           SET status = 'paused',
                               exit_reason = 'stale_reclaimed',
                               last_active_at = CURRENT_TIMESTAMP
                           WHERE session_id = ?""",
                        (sid,),
                    )
                    reclaimed += 1
            await conn.commit()
            return reclaimed
        finally:
            await conn.close()

    async def save_dialogue_turn(self, turn: dict[str, object], session_id: str) -> None:
        turn_id = str(turn.get("turn_id") or turn.get("id") or "")
        if not turn_id:
            import uuid

            turn_id = str(uuid.uuid4())
        speaker = str(turn.get("speaker", "user"))
        content = str(turn.get("content", ""))
        intent = turn.get("intent") or turn.get("intent_json")
        actions = turn.get("actions_taken") or turn.get("actions_json")
        context_id = turn.get("context_id")
        approved = turn.get("approved_by_user")
        ts = turn.get("timestamp")

        conn = await self._connect()
        try:
            await conn.execute(
                """INSERT OR REPLACE INTO dialogue_turns
                   (turn_id, session_id, speaker, content, intent_json, actions_json,
                    context_id, approved_by_user, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))""",
                (
                    turn_id,
                    session_id,
                    speaker,
                    content,
                    json.dumps(intent) if intent is not None and not isinstance(intent, str) else intent,
                    json.dumps(actions) if actions is not None and not isinstance(actions, str) else actions,
                    str(context_id) if context_id is not None else None,
                    None if approved is None else (1 if approved else 0),
                    ts,
                ),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def save_approval_request(self, request: dict[str, object], session_id: str) -> None:
        rid = str(request.get("request_id") or request.get("id") or "")
        if not rid:
            import uuid

            rid = str(uuid.uuid4())
        options = request.get("options") or request.get("options_json") or []
        options_json = options if isinstance(options, str) else json.dumps(options)

        conn = await self._connect()
        try:
            await conn.execute(
                """INSERT INTO approval_requests
                   (request_id, session_id, request_type, description, options_json,
                    urgency, resolved_at, user_choice, user_comment, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                   ON CONFLICT(request_id) DO UPDATE SET
                       request_type=excluded.request_type,
                       description=excluded.description,
                       options_json=excluded.options_json,
                       urgency=excluded.urgency,
                       resolved_at=excluded.resolved_at,
                       user_choice=excluded.user_choice,
                       user_comment=excluded.user_comment""",
                (
                    rid,
                    session_id,
                    str(request.get("request_type", "workstream_proposal")),
                    str(request.get("description", "Approval required")),
                    options_json,
                    str(request.get("urgency", "non_blocking")),
                    request.get("resolved_at"),
                    request.get("user_choice"),
                    request.get("user_comment"),
                    request.get("created_at"),
                ),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def load_pending_approvals(self, session_id: str) -> list[dict[str, object]]:
        conn = await self._connect()
        try:
            cursor = await conn.execute(
                """SELECT * FROM approval_requests
                   WHERE session_id = ? AND resolved_at IS NULL
                   ORDER BY created_at ASC""",
                (session_id,),
            )
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await conn.close()

    async def update_session_heartbeat(self, session_id: str) -> None:
        conn = await self._connect()
        try:
            await conn.execute(
                """UPDATE sessions
                   SET heartbeat_at = CURRENT_TIMESTAMP,
                       last_active_at = CURRENT_TIMESTAMP
                   WHERE session_id = ?""",
                (session_id,),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def finalize_session(self, session_id: str, reason: str) -> None:
        """Pause session and set exit_reason in a single transaction."""
        conn = await self._connect()
        try:
            await conn.execute("BEGIN")
            await conn.execute(
                """UPDATE sessions
                   SET status = 'paused',
                       exit_reason = ?,
                       last_active_at = CURRENT_TIMESTAMP
                   WHERE session_id = ?""",
                (reason, session_id),
            )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise
        finally:
            await conn.close()
