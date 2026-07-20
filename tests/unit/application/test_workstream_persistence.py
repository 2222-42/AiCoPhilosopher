"""Unit tests for workstream result persistence (Issue #63)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aicophilosopher.application.services.workstream_persistence import (
    extract_hypotheses,
    format_document_section,
    load_hypotheses,
    persist_workstream_results,
)


def _arg_result() -> dict[str, Any]:
    return {
        "question": "What is free will?",
        "arguments": [
            {
                "premises": ["P1", "P2"],
                "conclusion": "Free will is compatible with determinism.",
                "tradition": "analytic",
                "confidence": 0.7,
            }
        ],
        "competing_positions": [
            {
                "premises": ["Q1"],
                "conclusion": "Free will is incompatible with determinism.",
                "tradition": "continental",
                "confidence": 0.65,
            }
        ],
        "argument_count": 2,
    }


def _lit_result() -> dict[str, Any]:
    return {
        "query": "consciousness",
        "result_count": 1,
        "bibliography": [
            {
                "title": "What is it like to be a bat?",
                "authors": ["Nagel"],
                "year": 1974,
                "abstract": "On subjective experience.",
                "tradition_tag": "analytic",
                "relevance_score": 0.9,
            }
        ],
        "bridge_notes": [
            {
                "from_tradition": "analytic",
                "to_tradition": "continental",
                "note": "Phenomenology and analytic philosophy of mind share concerns about subjectivity.",
                "confidence_score": 0.7,
            }
        ],
        "confidence": 0.7,
    }


class TestExtractHypotheses:
    def test_argumentation_extracts_conclusions(self) -> None:
        hyps = extract_hypotheses("argumentation", _arg_result(), "ws-001")
        assert len(hyps) == 2
        statements = {h["statement"] for h in hyps}
        assert "Free will is compatible with determinism." in statements
        assert "Free will is incompatible with determinism." in statements
        for h in hyps:
            assert h["hypothesis_id"].startswith("hyp-")
            assert h["status"] == "active"
            assert h["origin"] == "ai"
            assert h["source_workstream"] == "ws-001"
            assert h["workstream_type"] == "argumentation"
            assert 0.0 <= h["confidence_score"] <= 1.0

    def test_literature_uses_bridge_notes(self) -> None:
        hyps = extract_hypotheses("literature_search", _lit_result(), "ws-lit")
        assert len(hyps) == 1
        assert "Phenomenology" in hyps[0]["statement"]
        assert hyps[0]["epistemic_tradition"] == "analytic→continental"

    def test_literature_falls_back_to_bibliography(self) -> None:
        result = _lit_result()
        result["bridge_notes"] = []
        hyps = extract_hypotheses("literature_search", result, "ws-lit")
        assert len(hyps) >= 1
        assert "What is it like to be a bat?" in hyps[0]["statement"]

    def test_concept_analysis_from_map(self) -> None:
        result = {
            "concept": "mind",
            "concept_map": [
                {
                    "name": "mind",
                    "tradition": "analytic",
                    "definition": "The locus of mental states.",
                }
            ],
            "thought_experiments": [
                {
                    "name": "Mary's Room",
                    "description": "Qualia puzzle.",
                    "tradition": "analytic",
                }
            ],
            "confidence": 0.75,
        }
        hyps = extract_hypotheses("concept_analysis", result, "ws-ca")
        assert len(hyps) >= 2
        assert any("mind" in h["statement"] for h in hyps)

    def test_deduplicates_identical_statements(self) -> None:
        result = {
            "arguments": [
                {"conclusion": "Same claim.", "confidence": 0.6, "tradition": "a"},
                {"conclusion": "Same claim.", "confidence": 0.7, "tradition": "b"},
            ],
            "competing_positions": [],
        }
        hyps = extract_hypotheses("argumentation", result, "ws-d")
        assert len(hyps) == 1

    def test_synthesis_from_annotations(self) -> None:
        result = {
            "synthesized_document": "## Synthesis\n\nBody\n",
            "annotations": [
                {"claim": "Key synthesis claim", "confidence": 0.8, "tradition": "analytic"}
            ],
            "synthesis_confidence": 0.8,
        }
        hyps = extract_hypotheses("synthesis", result, "ws-syn")
        assert len(hyps) == 1
        assert hyps[0]["statement"] == "Key synthesis claim"


class TestPersistWorkstreamResults:
    def test_writes_metadata_document_jsonl_and_report(self, tmp_path: Path) -> None:
        # Arrange a project skeleton
        (tmp_path / "metadata.json").write_text(
            json.dumps(
                {
                    "project_id": "proj-test",
                    "title": "Free Will",
                    "status": "created",
                    "workstreams": {},
                    "hypotheses": [],
                }
            )
        )
        (tmp_path / "living_document.md").write_text(
            "# Free Will\n\n## Introduction\n\nDraft.\n"
        )
        (tmp_path / "hypotheses.jsonl").touch()
        (tmp_path / "workstreams").mkdir()

        summary = persist_workstream_results(
            tmp_path, "argumentation", _arg_result(), workstream_id="ws-fixed"
        )

        assert summary["workstream_id"] == "ws-fixed"
        assert summary["hypotheses_added"] == 2
        assert summary["document_updated"] is True

        meta = json.loads((tmp_path / "metadata.json").read_text())
        assert meta["status"] == "active"
        assert len(meta["hypotheses"]) == 2
        assert "ws-fixed" in meta["workstreams"]
        assert meta["workstreams"]["ws-fixed"]["status"] == "completed"

        doc = (tmp_path / "living_document.md").read_text()
        assert "Workstream: argumentation" in doc
        assert "Free will is compatible with determinism." in doc

        jsonl = (tmp_path / "hypotheses.jsonl").read_text().strip().splitlines()
        assert len(jsonl) == 2
        assert json.loads(jsonl[0])["statement"]

        report = tmp_path / "workstreams" / "ws-fixed_report.md"
        assert report.exists()
        assert "Raw Result" in report.read_text()

    def test_appends_on_second_workstream(self, tmp_path: Path) -> None:
        (tmp_path / "metadata.json").write_text(
            json.dumps({"project_id": "p", "hypotheses": [], "workstreams": {}})
        )
        (tmp_path / "living_document.md").write_text("# Doc\n")
        (tmp_path / "workstreams").mkdir()

        persist_workstream_results(tmp_path, "argumentation", _arg_result())
        persist_workstream_results(tmp_path, "literature_search", _lit_result())

        meta = json.loads((tmp_path / "metadata.json").read_text())
        assert len(meta["workstreams"]) == 2
        assert len(meta["hypotheses"]) >= 3  # 2 arg + 1 lit bridge

        doc = (tmp_path / "living_document.md").read_text()
        assert doc.count("## Workstream:") == 2

    def test_load_hypotheses_filter(self, tmp_path: Path) -> None:
        (tmp_path / "metadata.json").write_text(
            json.dumps(
                {
                    "hypotheses": [
                        {"hypothesis_id": "h1", "statement": "A", "status": "active"},
                        {
                            "hypothesis_id": "h2",
                            "statement": "B",
                            "status": "refuted",
                        },
                    ]
                }
            )
        )
        assert len(load_hypotheses(tmp_path)) == 2
        assert len(load_hypotheses(tmp_path, filter_status="active")) == 1
        assert load_hypotheses(tmp_path, filter_status="active")[0]["hypothesis_id"] == "h1"
        assert load_hypotheses(tmp_path, filter_status="abandoned") == []

    def test_format_document_section_includes_hypotheses(self) -> None:
        hyps = extract_hypotheses("argumentation", _arg_result(), "ws-x")
        section = format_document_section("argumentation", _arg_result(), "ws-x", hyps)
        assert "## Workstream: argumentation (ws-x)" in section
        assert "Extracted Hypotheses" in section
        assert hyps[0]["hypothesis_id"] in section


class TestCliPersistenceRoundtrip:
    """CLI-level: start-workstream then show-hypotheses / show-document."""

    def test_start_workstream_then_show(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from click.testing import CliRunner

        from aicophilosopher.presentation import commands as cmd_mod

        # Point CLI workspace at tmp_path via Config (Issue #62 / AICOPH_WORKSPACE_DIR)
        monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path / "workspace"))
        monkeypatch.setattr(cmd_mod, "CURRENT_PROJECT_FILE", tmp_path / ".current_project")
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        create = runner.invoke(cmd_mod.cli, ["new-project", "Persistence Test", "-q", "What is free will?"])
        assert create.exit_code == 0, create.output

        run = runner.invoke(cmd_mod.cli, ["start-workstream", "argumentation"])
        assert run.exit_code == 0, run.output
        assert "Persisted:" in run.output
        assert "hypotheses" in run.output.lower()

        show_h = runner.invoke(cmd_mod.cli, ["show-hypotheses"])
        assert show_h.exit_code == 0, show_h.output
        assert "hyp-" in show_h.output
        assert "No hypotheses yet" not in show_h.output

        show_active = runner.invoke(cmd_mod.cli, ["show-hypotheses", "--status", "active"])
        assert show_active.exit_code == 0
        assert "hyp-" in show_active.output

        show_doc = runner.invoke(cmd_mod.cli, ["show-document"])
        assert show_doc.exit_code == 0, show_doc.output
        assert "Workstream: argumentation" in show_doc.output

        # Status should reflect non-zero counts
        status = runner.invoke(cmd_mod.cli, ["status"])
        assert status.exit_code == 0
        assert "Hypotheses: 0" not in status.output



class TestPersistSafety:
    """Copilot review: no silent metadata clobber; no hypothesis double-count."""

    def test_corrupt_metadata_fails_fast(self, tmp_path: Path) -> None:
        from aicophilosopher.application.services.workstream_persistence import (
            persist_workstream_results,
        )

        proj = tmp_path / "proj"
        proj.mkdir()
        meta = proj / "metadata.json"
        meta.write_text("{not-json", encoding="utf-8")
        with pytest.raises(ValueError, match="invalid JSON"):
            persist_workstream_results(
                project_dir=proj,
                workstream_type="argumentation",
                result={
                    "arguments": [{"conclusion": "x", "confidence": 0.5, "tradition": "analytic"}],
                    "competing_positions": [],
                },
            )
        # Original corrupt content still present (or backed up)
        assert meta.exists()
        raw = meta.read_text(encoding="utf-8")
        assert "{not-json" in raw or (proj / "metadata.json.corrupt").exists()

    def test_load_hypotheses_dedupes_metadata_and_jsonl(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same hypothesis_id in metadata + jsonl must appear once in show path."""
        import json

        from click.testing import CliRunner

        from aicophilosopher.presentation import commands as cmd_mod

        monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path / "workspace"))
        monkeypatch.setattr(cmd_mod, "CURRENT_PROJECT_FILE", tmp_path / ".current_project")
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        create = runner.invoke(cmd_mod.cli, ["new-project", "Dedupe", "-q", "Q?"])
        assert create.exit_code == 0, create.output

        # Locate project dir
        from aicophilosopher.domain.services.config import Config

        projects = Config().projects_dir()
        proj_dirs = list(projects.glob("proj-*"))
        assert proj_dirs
        proj = proj_dirs[0]
        hyp = {
            "hypothesis_id": "hyp-dup-1",
            "statement": "Only once",
            "status": "active",
            "strength": "moderate",
            "confidence_score": 0.7,
            "origin": "ai",
        }
        meta_path = proj / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["hypotheses"] = [hyp]
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        (proj / "hypotheses.jsonl").write_text(
            json.dumps(hyp) + "\n", encoding="utf-8"
        )

        shown = runner.invoke(cmd_mod.cli, ["show-hypotheses"])
        assert shown.exit_code == 0, shown.output
        assert shown.output.count("hyp-dup-1") == 1
        assert shown.output.count("Only once") == 1
