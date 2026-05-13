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
        (p / "workstreams").mkdir(parents=True, exist_ok=True)
        (p / "margin_notes").mkdir(parents=True, exist_ok=True)
        (p / "artifacts").mkdir(parents=True, exist_ok=True)
        (p / "logs").mkdir(parents=True, exist_ok=True)
        (p / "vector_db").mkdir(parents=True, exist_ok=True)
        return p

    async def create_project(self, title: str) -> str:
        import uuid
        project_id = f"proj-{uuid.uuid4().hex[:8]}"
        base = self._ensure_project_dirs(project_id)
        living_doc = base / "living_document.md"
        if not living_doc.exists():
            living_doc.write_text(
                f"---\ntitle: {title}\nproject_id: {project_id}\nversion: 1\n"
                f"epistemic_status: Draft\ntraditions_referenced: []\n---\n\n"
                f"# {title}\n\n"
            )
        return project_id

    async def write_document(self, project_id: str, filename: str, content: str) -> str:
        base = self._ensure_project_dirs(project_id)
        filepath = base / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    async def read_document(self, project_id: str, filename: str) -> str | None:
        base = self._ensure_project_dirs(project_id)
        filepath = base / filename
        if not filepath.exists():
            return None
        return filepath.read_text(encoding="utf-8")

    async def append_jsonl(self, project_id: str, filename: str, records: list[dict[str, Any]]) -> None:
        base = self._ensure_project_dirs(project_id)
        filepath = base / filename
        with open(filepath, "a") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def write_json(self, project_id: str, filename: str, data: Any) -> str:
        base = self._ensure_project_dirs(project_id)
        filepath = base / filename
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(filepath)

    async def read_json(self, project_id: str, filename: str) -> Any:
        base = self._ensure_project_dirs(project_id)
        filepath = base / filename
        if not filepath.exists():
            return None
        return json.loads(filepath.read_text(encoding="utf-8"))

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
        base = self._ensure_project_dirs(project_id)
        ws_dir = base / "workstreams"
        if not ws_dir.exists():
            return []
        return sorted(
            f.stem.replace("_report", "")
            for f in ws_dir.glob("*_report.md")
        )

    async def create_directory(self, path: str) -> None:
        Path(path).mkdir(parents=True, exist_ok=True)

    async def ensure_project_dirs(self, project_id: str) -> str:
        p = self._ensure_project_dirs(project_id)
        return str(p)
