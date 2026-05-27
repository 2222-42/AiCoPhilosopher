"""Session persistence manager (T-016)."""

from __future__ import annotations

import errno
import os
from typing import TYPE_CHECKING, Any

from aicophilosopher.domain.entities.session import SessionState, SessionStatus

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
            await self._storage.save_session(self._to_dict(session))
        return session

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

    @staticmethod
    def _from_dict(data: dict[str, Any]) -> SessionState:
        """Reconstruct SessionState from storage dict, parsing JSON columns."""
        import json
        from datetime import UTC, datetime
        from uuid import UUID

        def _parse_ts(val: Any) -> datetime | None:
            if val is None:
                return None
            try:
                return datetime.fromisoformat(str(val))
            except (ValueError, TypeError):
                return None

        sid = data.get("session_id")
        return SessionState(
            session_id=UUID(str(sid)) if sid else UUID("00000000-0000-0000-0000-000000000000"),
            project_id=data.get("project_id", ""),
            status=SessionStatus(data.get("status", "active")),
            pid=int(data.get("pid", 0)),
            heartbeat_at=_parse_ts(data.get("heartbeat_at")) or datetime.now(UTC),
            created_at=_parse_ts(data.get("created_at")) or datetime.now(UTC),
            last_active_at=_parse_ts(data.get("last_active_at")) or datetime.now(UTC),
            exit_reason=data.get("exit_reason"),
            active_workstreams=json.loads(str(data.get("active_workstreams_json", "[]"))),
            config_snapshot=json.loads(str(data.get("config_snapshot_json", "{}"))),
        )
