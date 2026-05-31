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

    def _sessions_dir(self) -> Path:
        p = self.base_path / "sessions"
        p.mkdir(parents=True, exist_ok=True)
        return p

    async def save_session(self, session: dict[str, object]) -> None:
        sid = str(session.get("session_id", "unknown"))
        path = self._sessions_dir() / f"{sid}.json"
        await asyncio.to_thread(
            path.write_text,
            json.dumps(session, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def load_session(self, project_id: str) -> dict[str, object] | None:
        # Find the most recent session file for this project
        sessions_dir = self._sessions_dir()
        if not sessions_dir.exists():
            return None
        best: tuple[float, Path] | None = None
        for f in sessions_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if data.get("project_id") == project_id:
                    mtime = f.stat().st_mtime
                    if best is None or mtime > best[0]:
                        best = (mtime, f)
            except (json.JSONDecodeError, OSError):
                continue
        if best is None:
            return None
        return json.loads(best[1].read_text(encoding="utf-8"))

    async def finalize_session(self, session_id: str, reason: str) -> None:
        path = self._sessions_dir() / f"{session_id}.json"
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["status"] = "paused"
            data["exit_reason"] = reason
            await asyncio.to_thread(
                path.write_text,
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except (json.JSONDecodeError, OSError):
            pass
