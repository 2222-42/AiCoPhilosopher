"""Session persistence manager (T-016)."""

from __future__ import annotations

import errno
import json
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from aicophilosopher.domain.entities.session import (
    FocusContext,
    SessionState,
    SessionStatus,
)

if TYPE_CHECKING:
    from aicophilosopher.domain.entities.session import (
        ApprovalRequest,
        DialogueTurn,
    )


class SessionManager:
    """Manages REPL session persistence via StoragePort."""

    def __init__(self, storage: Any = None) -> None:
        self._storage = storage

    async def create_session(self, project_id: str) -> SessionState:
        session = SessionState(project_id=project_id)
        if self._storage:
            await self._storage.save_session(self.session_to_storage(session))
        return session

    async def save_session(self, session: SessionState) -> None:
        """Persist full session state (upsert)."""
        if self._storage:
            await self._storage.save_session(self.session_to_storage(session))

    async def persist_turn(self, turn: DialogueTurn, session_id: str) -> None:
        if self._storage:
            await self._storage.save_dialogue_turn(self._to_dict(turn), session_id)

    async def finalize_session(self, session_id: str, reason: str) -> None:
        if self._storage:
            await self._storage.finalize_session(session_id, reason)

    async def load_session(self, project_id: str) -> SessionState | None:
        if not self._storage:
            return None
        data = await self._storage.load_session(project_id)
        if data is None:
            return None
        return self._from_dict(data)

    async def list_projects(self) -> list[dict[str, Any]]:
        if not self._storage:
            return []
        return await self._storage.list_projects_with_sessions()  # type: ignore[no-any-return]

    async def reclaim_stale_sessions(self) -> int:
        if not self._storage:
            return 0
        return await self._storage.reclaim_stale_sessions()  # type: ignore[no-any-return]

    async def update_heartbeat(self, session_id: str) -> None:
        if self._storage:
            await self._storage.update_session_heartbeat(session_id)

    async def save_approval_request(self, request: ApprovalRequest, session_id: str) -> None:
        if self._storage:
            await self._storage.save_approval_request(self._to_dict(request), session_id)

    async def load_pending_approvals(self, session_id: str) -> list[dict[str, Any]]:
        if not self._storage:
            return []
        return await self._storage.load_pending_approvals(session_id)  # type: ignore[no-any-return]

    async def is_active_session_live(self, pid: int) -> bool:
        """Check if a process with given PID is currently running."""
        try:
            os.kill(pid, 0)
        except OSError as e:
            if e.errno == errno.ESRCH:
                return False
            if e.errno == errno.EPERM:
                return True
        else:
            return True
        return False

    # ── Serialization helpers ─────────────────────────────────────────────

    @staticmethod
    def _to_dict(obj: Any) -> dict[str, object]:
        """Convert Pydantic model to dict for storage."""
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")  # type: ignore[no-any-return]
        return dict(obj)

    @classmethod
    def session_to_storage(cls, session: SessionState) -> dict[str, object]:
        """Serialize SessionState into StoragePort session dict layout.

        Includes both SQLite column-style ``*_json`` fields and native
        Python objects so FileSystemAdapter can round-trip full state
        (dialogue history, focus, config_snapshot) across process restarts.
        """
        dump = session.model_dump(mode="json")
        return {
            "session_id": dump["session_id"],
            "project_id": dump["project_id"],
            "status": dump["status"],
            "pid": dump["pid"],
            "heartbeat_at": dump["heartbeat_at"],
            "created_at": dump["created_at"],
            "last_active_at": dump["last_active_at"],
            "exit_reason": dump["exit_reason"],
            # SQLite / StoragePort column layout
            "focus_json": json.dumps(dump["current_focus"]),
            "active_workstreams_json": json.dumps(dump["active_workstreams"]),
            "config_snapshot_json": json.dumps(dump["config_snapshot"]),
            # Full-fidelity extras for FS resume
            "current_focus": dump["current_focus"],
            "active_workstreams": dump["active_workstreams"],
            "config_snapshot": dump["config_snapshot"],
            "dialogue_history": dump["dialogue_history"],
            "context_blocks": dump["context_blocks"],
            "approval_requests": dump["approval_requests"],
        }

    @staticmethod
    def _parse_ts(val: Any) -> datetime | None:
        if val is None:
            return None
        try:
            return datetime.fromisoformat(str(val))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _json_field(data: dict[str, Any], key_json: str, key_plain: str, default: Any) -> Any:
        for key in (key_json, key_plain):
            if key not in data or data[key] is None:
                continue
            val = data[key]
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except json.JSONDecodeError:
                    return default
            return val
        return default

    @staticmethod
    def _as_typed_list(raw: Any) -> list[Any]:
        return raw if isinstance(raw, list) else []

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> SessionState:
        """Reconstruct SessionState from storage dict (FS or SQLite layout)."""
        sid = data.get("session_id")
        focus_raw = cls._json_field(data, "focus_json", "current_focus", {})
        try:
            focus = FocusContext.model_validate(focus_raw) if focus_raw else FocusContext()
        except Exception:
            focus = FocusContext()

        workstreams = cls._json_field(data, "active_workstreams_json", "active_workstreams", [])
        config = cls._json_field(data, "config_snapshot_json", "config_snapshot", {})

        kwargs: dict[str, Any] = {
            "session_id": UUID(str(sid)) if sid else UUID("00000000-0000-0000-0000-000000000000"),
            "project_id": data.get("project_id", ""),
            "status": SessionStatus(data.get("status", "active")),
            "pid": int(data.get("pid", 0) or 0),
            "heartbeat_at": cls._parse_ts(data.get("heartbeat_at")) or datetime.now(UTC),
            "created_at": cls._parse_ts(data.get("created_at")) or datetime.now(UTC),
            "last_active_at": cls._parse_ts(data.get("last_active_at")) or datetime.now(UTC),
            "exit_reason": data.get("exit_reason"),
            "active_workstreams": workstreams if isinstance(workstreams, list) else [],
            "config_snapshot": config if isinstance(config, dict) else {},
            "current_focus": focus,
        }
        cls._restore_nested(kwargs, data)
        return SessionState(**kwargs)

    @staticmethod
    def _restore_nested(kwargs: dict[str, Any], data: dict[str, Any]) -> None:
        """Best-effort nested entity restore — invalid rows are dropped per item."""
        from aicophilosopher.domain.entities.session import (
            ApprovalRequest,
            ContextBlock,
            DialogueTurn,
        )

        def _validate_many(raw: object, model: type[Any]) -> list[Any]:
            items: list[Any] = []
            for row in SessionManager._as_typed_list(raw):
                if not isinstance(row, dict):
                    continue
                try:
                    items.append(model.model_validate(row))
                except Exception:
                    # Skip only the bad row; keep restoring the rest.
                    continue
            return items

        kwargs["dialogue_history"] = _validate_many(
            data.get("dialogue_history"), DialogueTurn
        )
        kwargs["context_blocks"] = _validate_many(
            data.get("context_blocks"), ContextBlock
        )
        kwargs["approval_requests"] = _validate_many(
            data.get("approval_requests"), ApprovalRequest
        )
