"""CLI command tests for T-035 / Issue #58.

Exercises all Click command definitions with CliRunner.
Silent no-op success is not accepted: unimplemented commands must exit ≠ 0.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from aicophilosopher.presentation.commands import cli

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Route all CLI project I/O through a temp Config workspace (Issue #62)."""
    monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.chdir(tmp_path)


def _projects_dir() -> Path:
    from aicophilosopher.domain.services.config import Config

    return Config().projects_dir()


def _create_project(title: str = "Test") -> str:
    result = runner.invoke(cli, ["new-project", title])
    assert result.exit_code == 0, result.output
    m = re.search(r"ID: (proj-\w+)", result.output)
    assert m is not None, f"project ID not found in new-project output: {result.output!r}"
    return m.group(1)


def test_new_project() -> None:
    result = runner.invoke(cli, ["new-project", "Test Project"])
    assert result.exit_code == 0
    assert "Project created" in result.output


def test_new_project_with_question() -> None:
    result = runner.invoke(cli, ["new-project", "Free Will", "-q", "Do we have free will?"])
    assert result.exit_code == 0
    assert "Free Will" in result.output


def test_list_projects() -> None:
    result = runner.invoke(cli, ["list-projects"])
    assert result.exit_code == 0


def test_open_project() -> None:
    result = runner.invoke(cli, ["new-project", "TestOpen"])
    assert result.exit_code == 0
    m = re.search(r"ID: (proj-\w+)", result.output)
    assert m is not None, f"project ID not found in new-project output: {result.output!r}"
    result = runner.invoke(cli, ["open-project", m.group(1)])
    assert result.exit_code == 0
    assert "Opened project" in result.output


def test_archive_project() -> None:
    result = runner.invoke(cli, ["new-project", "ToArchive"])
    assert result.exit_code == 0
    m = re.search(r"ID: (proj-\w+)", result.output)
    assert m is not None, f"project ID not found in new-project output: {result.output!r}"
    result = runner.invoke(cli, ["archive-project", m.group(1)], input="y\n")
    assert result.exit_code == 0


def test_refine_goal() -> None:
    # Create a project first so refine-goal has context
    runner.invoke(cli, ["new-project", "Test"])
    result = runner.invoke(cli, ["refine-goal"], input="analytic\nepistemology\nPlato\nclear argument\n")
    assert result.exit_code == 0
    assert "refine" in result.output.lower() or "Refine" in result.output


def test_start_workstream() -> None:
    # Create a project first so start-workstream has context
    runner.invoke(cli, ["new-project", "Test"])
    result = runner.invoke(cli, ["start-workstream", "literature_search"])
    assert result.exit_code == 0
    assert "literature_search" in result.output


def test_start_workstream_invalid_type() -> None:
    result = runner.invoke(cli, ["start-workstream", "invalid_type"])
    assert result.exit_code != 0


def test_pause_resume_not_implemented() -> None:
    """pause/resume must not silent-succeed; workstream control is issue #60."""
    result = runner.invoke(cli, ["pause", "ws-001"])
    assert result.exit_code != 0
    assert "not implemented" in result.output.lower()

    result = runner.invoke(cli, ["resume", "ws-001"])
    assert result.exit_code != 0
    assert "not implemented" in result.output.lower()


def test_steer_not_implemented() -> None:
    result = runner.invoke(cli, ["steer", "ws-001", "Focus on compatibilism"])
    assert result.exit_code != 0
    assert "not implemented" in result.output.lower()
    assert "ws-001" in result.output


def test_show_hypotheses_empty_project() -> None:
    _create_project("HypEmpty")
    result = runner.invoke(cli, ["show-hypotheses"])
    assert result.exit_code == 0
    assert "No hypotheses" in result.output


def test_show_hypotheses_reads_metadata() -> None:
    proj_id = _create_project("HypData")
    meta_path = _projects_dir() / proj_id / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["hypotheses"] = [
        {
            "hypothesis_id": "hyp-001",
            "statement": "Compatibilism is viable",
            "status": "active",
            "strength": "moderate",
            "confidence_score": 0.7,
            "origin": "ai",
        },
        {
            "hypothesis_id": "hyp-002",
            "statement": "Libertarianism fails",
            "status": "refuted",
            "strength": "weak",
            "confidence_score": 0.3,
            "origin": "ai",
        },
    ]
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    result = runner.invoke(cli, ["show-hypotheses"])
    assert result.exit_code == 0
    assert "hyp-001" in result.output
    assert "Compatibilism is viable" in result.output
    assert "hyp-002" in result.output

    result = runner.invoke(cli, ["show-hypotheses", "--status", "active"])
    assert result.exit_code == 0
    assert "hyp-001" in result.output
    assert "hyp-002" not in result.output


def test_show_hypotheses_filter() -> None:
    _create_project("HypFilter")
    result = runner.invoke(cli, ["show-hypotheses", "--status", "active"])
    assert result.exit_code == 0
    assert "No hypotheses" in result.output or "active" in result.output


def test_show_hypotheses_invalid_filter() -> None:
    result = runner.invoke(cli, ["show-hypotheses", "--status", "invalid"])
    assert result.exit_code != 0


def test_show_hypotheses_requires_project() -> None:
    result = runner.invoke(cli, ["show-hypotheses"])
    assert result.exit_code != 0
    assert "No active project" in result.output


def test_show_dead_ends_empty() -> None:
    _create_project("DeadEmpty")
    result = runner.invoke(cli, ["show-dead-ends"])
    assert result.exit_code == 0
    assert "dead" in result.output.lower()
    # Must not pretend success without reading project data
    assert "No dead ends" in result.output


def test_show_dead_ends_reads_metadata() -> None:
    proj_id = _create_project("DeadData")
    meta_path = _projects_dir() / proj_id / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["failed_explorations"] = [
        {
            "exploration_id": "fe-001",
            "goal_attempted": "Prove hard determinism",
            "failure_reason": "Insufficient evidence",
            "lessons_learned": "Need empirical sources",
            "timestamp": "2026-01-01T00:00:00Z",
        }
    ]
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    result = runner.invoke(cli, ["show-dead-ends"])
    assert result.exit_code == 0
    assert "fe-001" in result.output
    assert "Prove hard determinism" in result.output
    assert "Insufficient evidence" in result.output


def test_add_note() -> None:
    # Need an active project for note persistence under workspace
    created = runner.invoke(cli, ["new-project", "NoteHost"])
    assert created.exit_code == 0, f"new-project failed: {created.output!r}"
    result = runner.invoke(cli, ["add-note", "Important insight", "--attach-to", "hyp-001"])
    assert result.exit_code == 0
    assert "hyp-001" in result.output
    assert "note-" in result.output


def test_compare_traditions() -> None:
    result = runner.invoke(cli, ["compare-traditions", "mind"])
    assert result.exit_code == 0
    assert "mind" in result.output


def test_status() -> None:
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "Project:" in result.output or "Status:" in result.output or "No active" in result.output


def test_show_document() -> None:
    result = runner.invoke(cli, ["show-document"])
    assert result.exit_code == 0


def test_export_writes_living_document() -> None:
    proj_id = _create_project("ExportMe")
    result = runner.invoke(cli, ["export", "markdown"])
    assert result.exit_code == 0
    assert "Exported" in result.output
    out = _projects_dir() / proj_id / "exports" / "living_document.md"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "ExportMe" in content or "living document" in content.lower() or "#" in content


def test_export_html() -> None:
    proj_id = _create_project("ExportHtml")
    result = runner.invoke(cli, ["export", "html"])
    assert result.exit_code == 0
    out = _projects_dir() / proj_id / "exports" / "living_document.html"
    assert out.exists()
    assert "<html" in out.read_text(encoding="utf-8")


def test_export_latex_not_implemented() -> None:
    _create_project("ExportLatex")
    result = runner.invoke(cli, ["export", "latex"])
    assert result.exit_code != 0
    assert "not implemented" in result.output.lower()


def test_export_custom_output() -> None:
    _create_project("ExportCustom")
    result = runner.invoke(cli, ["export", "markdown", "-o", "out/doc.md"])
    assert result.exit_code == 0
    assert Path("out/doc.md").exists()


def test_export_requires_project() -> None:
    result = runner.invoke(cli, ["export", "markdown"])
    assert result.exit_code != 0
    assert "No active project" in result.output


def test_config_no_args() -> None:
    result = runner.invoke(cli, ["config"])
    assert result.exit_code == 0
    assert "configuration" in result.output.lower()
    assert "llm.backend" in result.output
    # Must not claim set persistence works; #71 workspace fields present
    assert "not persist" in result.output.lower() or "AICOPH_" in result.output
    assert "projects_dir" in result.output


def test_config_set_refuses_silent_noop() -> None:
    """config <key> <value> must not pretend the write succeeded."""
    result = runner.invoke(cli, ["config", "llm.backend", "claude"])
    assert result.exit_code != 0
    assert "not persisted" in result.output.lower() or "refused" in result.output.lower()


def test_config_get_known_key() -> None:
    result = runner.invoke(cli, ["config", "llm.backend"])
    assert result.exit_code == 0
    assert "llm.backend" in result.output


def test_request_help_not_implemented() -> None:
    result = runner.invoke(cli, ["request-help"])
    assert result.exit_code != 0
    assert "not implemented" in result.output.lower()


def test_help() -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
