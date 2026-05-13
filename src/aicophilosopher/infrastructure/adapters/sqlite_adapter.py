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
    delivered INTEGER DEFAULT 0
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
              CREATE_MESSAGES, CREATE_REVIEW_ROUNDS, CREATE_ARTIFACTS, CREATE_NOTES] + INDEXES


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
                """INSERT OR REPLACE INTO projects
                   (project_id, title, original_question, status, living_document, metadata_json, external_layer_config_json, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
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
            return dict(row)
        finally:
            await conn.close()

    async def save_workstream(self, project_id: str, workstream: dict[str, object]) -> str:
        conn = await self._connect()
        try:
            await conn.execute(
                """INSERT OR REPLACE INTO workstreams
                   (workstream_id, project_id, type, status, goal_statement_json, assigned_coordinator,
                    assigned_sub_agents_json, results, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
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
            return dict(row) if row else None
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
