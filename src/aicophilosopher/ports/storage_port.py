from typing import Protocol


class StoragePort(Protocol):
    async def save_project(self, project: dict[str, object]) -> str:
        ...

    async def load_project(self, project_id: str) -> dict[str, object] | None:
        ...

    async def save_workstream(self, project_id: str, workstream: dict[str, object]) -> str:
        ...

    async def load_workstream(self, project_id: str, workstream_id: str) -> dict[str, object] | None:
        ...

    async def query_uncertainty(self, project_id: str, **filters: object) -> list[dict[str, object]]:
        ...

    async def save_note(self, project_id: str, note: dict[str, object]) -> str:
        ...

    async def list_projects(self) -> list[dict[str, object]]:
        ...

    async def delete_project(self, project_id: str) -> bool:
        ...

    # ── 002-console-agent session persistence (T-007) ──────────────────

    async def save_session(self, session: dict[str, object]) -> None:
        """Persist session state (upsert). The dict must contain:
        session_id, project_id, status, pid, heartbeat_at, focus_json,
        active_workstreams_json, exit_reason, config_snapshot_json.
        created_at and last_active_at are managed by the storage backend
        and may be omitted from the input dict."""
        ...

    async def load_session(self, project_id: str) -> dict[str, object] | None:
        """Load the most recent non-closed session for a project,
        ordered by last_active_at descending. Returns None if no
        eligible sessions exist."""
        ...

    async def list_projects_with_sessions(self) -> list[dict[str, object]]:
        """Return projects with their latest session status and
        last_active_at timestamp. Used for project selection UI."""
        ...

    async def reclaim_stale_sessions(self) -> int:
        """Mark sessions as stale where status='active' and the
        heartbeat timestamp exceeds heartbeat_timeout_seconds.
        The caller is responsible for checking process liveness (PID)
        before invoking this method. Returns count of reclaimed sessions."""
        ...

    async def save_dialogue_turn(self, turn: dict[str, object], session_id: str) -> None:
        """Insert a single dialogue turn (user/coordinator/system).
        Per FR-009: persisted BEFORE the coordinator renders the
        next response."""
        ...

    async def save_approval_request(self, request: dict[str, object], session_id: str) -> None:
        """Insert or update an approval request record."""
        ...

    async def load_pending_approvals(self, session_id: str) -> list[dict[str, object]]:
        """Return all unresolved approval requests (resolved_at IS NULL)
        for a session, oldest first."""
        ...

    async def update_session_heartbeat(self, session_id: str) -> None:
        """Set heartbeat_at to the current wall-clock time for session_id.
        Time source and precision are backend-specific."""
        ...

    async def finalize_session(self, session_id: str, reason: str) -> None:
        """Set session status to 'paused' and record exit_reason.
        Must execute in a single transaction (FR-009)."""
        ...
