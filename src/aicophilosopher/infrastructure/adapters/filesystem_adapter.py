import asyncio
import json
from pathlib import Path
from typing import Any


class FileSystemAdapter:
    def __init__(self, base_path: str = "") -> None:
        self.base_path = Path(base_path).expanduser().resolve() if base_path else Path.home() / ".aicophilosopher"

    def _project_path(self, project_id: str) -> Path:
        return self.base_path / "projects" / project_id

    def _ensure_project_dirs(self, project_id: str) -> Path:
        p = self._project_path(project_id)
        p.mkdir(parents=True, exist_ok=True)
        (p / "workstreams").mkdir(exist_ok=True)
        (p / "margin_notes").mkdir(exist_ok=True)
        (p / "artifacts").mkdir(exist_ok=True)
        (p / "logs").mkdir(exist_ok=True)
        (p / "vector_db").mkdir(exist_ok=True)
        return p

    async def create_project(self, title: str) -> str:
        import uuid
        project_id = f"proj-{uuid.uuid4().hex[:8]}"
        base = await asyncio.to_thread(self._ensure_project_dirs, project_id)
        living_doc = base / "living_document.md"
        if not living_doc.exists():
            content = (
                f"---\ntitle: {title}\nproject_id: {project_id}\nversion: 1\n"
                f"epistemic_status: Draft\ntraditions_referenced: []\n---\n\n"
                f"# {title}\n\n"
            )
            await asyncio.to_thread(living_doc.write_text, content, encoding="utf-8")
        return project_id

    async def write_document(self, project_id: str, filename: str, content: str) -> str:
        base = await asyncio.to_thread(self._ensure_project_dirs, project_id)
        filepath = base / filename
        await asyncio.to_thread(filepath.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(filepath.write_text, content, encoding="utf-8")
        return str(filepath)

    async def read_document(self, project_id: str, filename: str) -> str | None:
        filepath = self._project_path(project_id) / filename
        if not filepath.exists():
            return None

        def _read() -> str | None:
            return filepath.read_text(encoding="utf-8")

        return await asyncio.to_thread(_read)

    async def append_jsonl(self, project_id: str, filename: str, records: list[dict[str, Any]]) -> None:
        base = await asyncio.to_thread(self._ensure_project_dirs, project_id)
        filepath = base / filename
        lines = [json.dumps(r, ensure_ascii=False) + "\n" for r in records]

        def _write() -> None:
            with open(filepath, "a", encoding="utf-8") as f:
                f.writelines(lines)

        await asyncio.to_thread(_write)

    async def write_json(self, project_id: str, filename: str, data: Any) -> str:
        base = await asyncio.to_thread(self._ensure_project_dirs, project_id)
        filepath = base / filename
        await asyncio.to_thread(
            filepath.write_text, json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return str(filepath)

    async def read_json(self, project_id: str, filename: str) -> Any:
        filepath = self._project_path(project_id) / filename
        if not filepath.exists():
            return None

        def _read() -> Any:
            return json.loads(filepath.read_text(encoding="utf-8"))

        return await asyncio.to_thread(_read)

    async def write_workstream_report(self, project_id: str, workstream_id: str, report: str) -> str:
        return await self.write_document(project_id, f"workstreams/{workstream_id}_report.md", report)

    async def read_workstream_report(self, project_id: str, workstream_id: str) -> str | None:
        return await self.read_document(project_id, f"workstreams/{workstream_id}_report.md")

    async def append_hypotheses_jsonl(self, project_id: str, hypotheses: list[dict[str, Any]]) -> None:
        await self.append_jsonl(project_id, "hypotheses.jsonl", hypotheses)

    async def append_dialectical_history_jsonl(self, project_id: str, moves: list[dict[str, Any]]) -> None:
        await self.append_jsonl(project_id, "dialectical_history.jsonl", moves)

    async def write_uncertainty_registry_json(self, project_id: str, records: list[dict[str, Any]]) -> str:
        return await self.write_json(project_id, "uncertainty_registry.json", records)

    async def read_uncertainty_registry_json(self, project_id: str) -> Any:
        return await self.read_json(project_id, "uncertainty_registry.json")

    async def write_note(self, project_id: str, note: dict[str, Any]) -> str:
        return await self.write_json(project_id, f"margin_notes/{note['note_id']}.json", note)

    async def list_workstreams(self, project_id: str) -> list[str]:
        ws_dir = self._project_path(project_id) / "workstreams"
        if not ws_dir.exists():
            return []

        def _list() -> list[str]:
            return sorted(
                f.stem.replace("_report", "")
                for f in ws_dir.glob("*_report.md")
            )

        return await asyncio.to_thread(_list)

    async def create_directory(self, path: str) -> None:
        await asyncio.to_thread(Path(path).mkdir, parents=True, exist_ok=True)

    async def ensure_project_dirs(self, project_id: str) -> str:
        p = await asyncio.to_thread(self._ensure_project_dirs, project_id)
        return str(p)

    # ── Session persistence (002-console-agent) ───────────────────────

    # Heartbeat older than this marks an active session as reclaimable.
    HEARTBEAT_TIMEOUT_SECONDS = 300

    def _sessions_dir(self) -> Path:
        p = self.base_path / "sessions"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _session_path(self, session_id: str) -> Path:
        return self._sessions_dir() / f"{session_id}.json"

    def _turns_path(self, session_id: str) -> Path:
        return self._sessions_dir() / f"{session_id}.turns.jsonl"

    def _approvals_path(self, session_id: str) -> Path:
        return self._sessions_dir() / f"{session_id}.approvals.json"

    def _read_session_file(self, path: Path) -> dict[str, Any] | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _write_session_file(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _iter_session_files(self) -> list[Path]:
        sessions_dir = self._sessions_dir()
        # Only top-level session JSON files (exclude *.turns.jsonl / *.approvals.json)
        return sorted(
            p for p in sessions_dir.glob("*.json") if not p.name.endswith(".approvals.json")
        )

    def _activity_key(self, data: dict[str, Any], path: Path) -> float:
        """Sort key: prefer last_active_at ISO timestamp, fall back to mtime."""
        from datetime import datetime

        for key in ("last_active_at", "heartbeat_at", "created_at"):
            raw = data.get(key)
            if not raw:
                continue
            try:
                return datetime.fromisoformat(str(raw)).timestamp()
            except (ValueError, TypeError):
                continue
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    async def save_session(self, session: dict[str, object]) -> None:
        """Upsert full session state under sessions/{session_id}.json."""
        from datetime import UTC, datetime

        data = dict(session)
        sid = str(data.get("session_id") or "").strip()
        project_id = str(data.get("project_id") or "").strip()
        if not sid or not project_id:
            # Do not write sessions/unknown.json or clobber unrelated files.
            raise ValueError(
                "save_session requires non-empty session_id and project_id"
            )
        data["session_id"] = sid
        data["project_id"] = project_id
        # Keep last_active_at fresh on every write unless caller set it.
        if not data.get("last_active_at"):
            data["last_active_at"] = datetime.now(UTC).isoformat()
        path = self._session_path(sid)
        await asyncio.to_thread(self._write_session_file, path, data)

    async def load_session(self, project_id: str) -> dict[str, object] | None:
        """Load the most recent non-closed session for a project."""

        def _load() -> dict[str, object] | None:
            best: tuple[float, dict[str, Any]] | None = None
            for path in self._iter_session_files():
                data = self._read_session_file(path)
                if data is None:
                    continue
                if data.get("project_id") != project_id:
                    continue
                status = str(data.get("status", "active"))
                if status == "closed":
                    continue
                key = self._activity_key(data, path)
                if best is None or key > best[0]:
                    best = (key, data)
            return best[1] if best else None

        return await asyncio.to_thread(_load)

    def _session_list_record(self, data: dict[str, Any], path: Path) -> tuple[str, float, dict[str, object]] | None:
        pid = str(data.get("project_id", ""))
        if not pid:
            return None
        status = str(data.get("status", "active"))
        if status == "closed":
            return None
        key = self._activity_key(data, path)
        rec: dict[str, object] = {
            "project_id": pid,
            "title": data.get("title") or pid,
            "last_active_at": data.get("last_active_at") or data.get("heartbeat_at"),
            "session_status": status,
            "session_id": data.get("session_id"),
            "workstream_count": len(
                _as_list(data.get("active_workstreams"), data.get("active_workstreams_json"))
            ),
        }
        return pid, key, rec

    def _merge_disk_projects(
        self, latest: dict[str, tuple[float, dict[str, object]]]
    ) -> None:
        projects_root = self.base_path / "projects"
        if not projects_root.exists():
            return
        for pdir in projects_root.iterdir():
            if not pdir.is_dir() or pdir.name in latest:
                continue
            title = pdir.name
            meta_path = pdir / "metadata.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    title = str(meta.get("title") or pdir.name)
                except (json.JSONDecodeError, OSError):
                    pass
            latest[pdir.name] = (
                0.0,
                {
                    "project_id": pdir.name,
                    "title": title,
                    "last_active_at": None,
                    "session_status": None,
                    "session_id": None,
                    "workstream_count": 0,
                },
            )

    async def list_projects_with_sessions(self) -> list[dict[str, object]]:
        """Return projects with latest session status, most recent first."""

        def _list() -> list[dict[str, object]]:
            latest: dict[str, tuple[float, dict[str, object]]] = {}
            for path in self._iter_session_files():
                data = self._read_session_file(path)
                if data is None:
                    continue
                parsed = self._session_list_record(data, path)
                if parsed is None:
                    continue
                pid, key, rec = parsed
                prev = latest.get(pid)
                if prev is None or key > prev[0]:
                    latest[pid] = (key, rec)
            self._merge_disk_projects(latest)
            ordered = sorted(latest.values(), key=lambda item: item[0], reverse=True)
            return [rec for _, rec in ordered]

        return await asyncio.to_thread(_list)

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        import errno
        import os

        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError as e:
            if e.errno == errno.ESRCH:
                return False
            if e.errno == errno.EPERM:
                return True
            return False
        return True

    def _is_session_stale(self, data: dict[str, Any], now: Any) -> bool:
        from datetime import UTC, datetime

        raw_hb = data.get("heartbeat_at")
        if not raw_hb:
            return True
        try:
            hb = datetime.fromisoformat(str(raw_hb))
            if hb.tzinfo is None:
                hb = hb.replace(tzinfo=UTC)
            if (now - hb).total_seconds() > self.HEARTBEAT_TIMEOUT_SECONDS:
                return True
        except (ValueError, TypeError):
            return True
        try:
            pid = int(data.get("pid") or 0)
        except (TypeError, ValueError):
            pid = 0
        return not self._pid_alive(pid)

    async def reclaim_stale_sessions(self) -> int:
        """Mark abandoned active sessions as paused (stale_reclaimed).

        A session is reclaimed when status='active' and either:
        - heartbeat_at is older than HEARTBEAT_TIMEOUT_SECONDS, or
        - the recorded PID is no longer running.
        """
        from datetime import UTC, datetime

        def _reclaim() -> int:
            now = datetime.now(UTC)
            count = 0
            for path in self._iter_session_files():
                data = self._read_session_file(path)
                if data is None or str(data.get("status", "")) != "active":
                    continue
                if not self._is_session_stale(data, now):
                    continue
                data["status"] = "paused"
                data["exit_reason"] = "stale_reclaimed"
                data["last_active_at"] = now.isoformat()
                self._write_session_file(path, data)
                count += 1
            return count

        return await asyncio.to_thread(_reclaim)

    async def save_dialogue_turn(self, turn: dict[str, object], session_id: str) -> None:
        """Append a dialogue turn to sessions/{session_id}.turns.jsonl."""
        path = self._turns_path(session_id)
        record = dict(turn)
        record.setdefault("session_id", session_id)
        line = json.dumps(record, ensure_ascii=False) + "\n"

        def _append() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(line)

        await asyncio.to_thread(_append)

    async def save_approval_request(self, request: dict[str, object], session_id: str) -> None:
        """Upsert an approval request in sessions/{session_id}.approvals.json."""
        path = self._approvals_path(session_id)
        record = dict(request)
        record.setdefault("session_id", session_id)
        rid = str(record.get("request_id") or record.get("id") or "")

        def _upsert() -> None:
            items: list[dict[str, Any]] = []
            if path.exists():
                try:
                    loaded = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(loaded, list):
                        items = loaded
                except (json.JSONDecodeError, OSError):
                    items = []
            if rid:
                items = [i for i in items if str(i.get("request_id") or i.get("id") or "") != rid]
            items.append(record)
            path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

        await asyncio.to_thread(_upsert)

    async def load_pending_approvals(self, session_id: str) -> list[dict[str, object]]:
        """Return unresolved approval requests (resolved_at is null), oldest first."""
        path = self._approvals_path(session_id)

        def _load() -> list[dict[str, object]]:
            if not path.exists():
                return []
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
            if not isinstance(loaded, list):
                return []
            pending = [i for i in loaded if not i.get("resolved_at")]
            # oldest first by created_at if present
            pending.sort(key=lambda i: str(i.get("created_at") or ""))
            return pending  # type: ignore[return-value]

        return await asyncio.to_thread(_load)

    async def update_session_heartbeat(self, session_id: str) -> None:
        """Set heartbeat_at (and last_active_at) to now for session_id."""
        from datetime import UTC, datetime

        path = self._session_path(session_id)
        if not path.exists():
            return

        def _update() -> None:
            data = self._read_session_file(path)
            if data is None:
                return
            now = datetime.now(UTC).isoformat()
            data["heartbeat_at"] = now
            data["last_active_at"] = now
            self._write_session_file(path, data)

        await asyncio.to_thread(_update)

    async def finalize_session(self, session_id: str, reason: str) -> None:
        """Set session status to paused and record exit_reason (single write)."""
        from datetime import UTC, datetime

        path = self._session_path(session_id)
        if not path.exists():
            return

        def _finalize() -> None:
            data = self._read_session_file(path)
            if data is None:
                return
            data["status"] = "paused"
            data["exit_reason"] = reason
            data["last_active_at"] = datetime.now(UTC).isoformat()
            self._write_session_file(path, data)

        await asyncio.to_thread(_finalize)


def _as_list(plain: Any, json_field: Any) -> list[Any]:
    """Accept either a native list or a JSON-encoded list string."""
    if isinstance(plain, list):
        return plain
    if isinstance(json_field, list):
        return json_field
    if isinstance(json_field, str) and json_field:
        try:
            val = json.loads(json_field)
            if isinstance(val, list):
                return val
        except json.JSONDecodeError:
            return []
    if isinstance(plain, str) and plain:
        try:
            val = json.loads(plain)
            if isinstance(val, list):
                return val
        except json.JSONDecodeError:
            return []
    return []
