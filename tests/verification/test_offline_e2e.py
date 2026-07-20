"""Offline E2E / verification suite (Issue #66).

Guarantees (without production LLM):
  1. Silent CLI no-ops do not succeed — each unwired/partial command either
     fails honestly (exit ≠ 0 + clear failure text) or performs a real effect.
  2. `start-workstream` leaves durable results under the project workspace
     (via workstream_persistence / Issue #63).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from aicophilosopher.presentation.commands import cli

_HONEST_FAIL = re.compile(
    r"not implemented|not persisted|refused|failed|cannot|no active",
    re.IGNORECASE,
)
_PROJECT_ID = re.compile(r"ID:\s*(proj-\w+)")


def _combined_output(result: object) -> str:
    output = getattr(result, "output", "") or ""
    exc = getattr(result, "exception", None)
    return f"{output}\n{exc}" if exc else output


def _assert_not_silent_noop(
    result: object,
    *,
    real_effect: bool = False,
) -> None:
    """CLI must not pretend success without doing work (Issue #58 / #66).

    Accepts either:
      - exit ≠ 0 with an honest failure message, or
      - exit == 0 when *real_effect* is True (caller verified side effects).
    """
    exit_code = getattr(result, "exit_code", 0)
    combined = _combined_output(result)

    if exit_code == 0:
        assert real_effect, (
            f"silent no-op succeeded (exit 0) without verified side effect: {combined!r}"
        )
        return

    assert _HONEST_FAIL.search(combined), (
        f"non-zero exit must be an honest failure message "
        f"(not implemented / refused / not persisted / …), "
        f"got exit={exit_code}: {combined!r}"
    )


class TestNoOpHonesty:
    """Issue #58 policy, enforced by offline verification (#66)."""

    @pytest.mark.parametrize(
        "args",
        [
            ["pause", "ws-001"],
            ["resume", "ws-001"],
            ["steer", "ws-001", "focus on X"],
            ["request-help"],
        ],
    )
    def test_lifecycle_stubs_fail_honestly(self, args: list[str]) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, args)
        _assert_not_silent_noop(result, real_effect=False)

    def test_export_is_honest_or_real(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """export either writes a real artifact or fails honestly."""
        monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        created = runner.invoke(cli, ["new-project", "Export Probe", "-q", "probe?"])
        assert created.exit_code == 0, created.output
        result = runner.invoke(cli, ["export", "markdown"])
        if result.exit_code == 0:
            exports = list(tmp_path.rglob("exports/**/*")) + list(
                tmp_path.rglob("living_document.*")
            )
            wrote = any(p.is_file() and p.stat().st_size > 0 for p in exports)
            wrote = wrote or bool(
                re.search(r"export|wrote|saved|written|exported", result.output, re.I)
            )
            _assert_not_silent_noop(result, real_effect=wrote)
        else:
            _assert_not_silent_noop(result, real_effect=False)

    def test_show_dead_ends_is_honest_or_real(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        created = runner.invoke(cli, ["new-project", "DeadEnd Probe"])
        assert created.exit_code == 0, created.output
        result = runner.invoke(cli, ["show-dead-ends"])
        if result.exit_code == 0:
            honest_empty = bool(
                re.search(r"no dead end|0 dead|none|empty", result.output, re.I)
            )
            _assert_not_silent_noop(
                result, real_effect=honest_empty or bool(result.output.strip())
            )
        else:
            _assert_not_silent_noop(result, real_effect=False)

    def test_config_set_is_honest_or_persisted(self) -> None:
        """Setting config must not silent-succeed without persistence."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "llm.backend", "claude"])
        _assert_not_silent_noop(result, real_effect=False)


class TestWorkstreamResultsPersist:
    """start-workstream must leave results that survive the process (#66 / #63)."""

    def test_argumentation_workstream_leaves_artifacts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        created = runner.invoke(
            cli,
            [
                "new-project",
                "Free Will Study",
                "-q",
                "Is free will compatible with determinism?",
            ],
        )
        assert created.exit_code == 0, created.output
        match = _PROJECT_ID.search(created.output)
        assert match is not None, f"project id missing from: {created.output!r}"
        project_id = match.group(1)

        started = runner.invoke(cli, ["start-workstream", "argumentation"])
        assert started.exit_code == 0, started.output
        assert "Argumentation Results" in started.output or "argumentation" in started.output.lower()
        assert "completed" in started.output.lower() or "Persisted" in started.output

        # Config.projects_dir: <workspace>/projects/<id>
        proj = tmp_path / "projects" / project_id
        assert proj.is_dir(), f"project dir missing: {proj}"

        ws_dir = proj / "workstreams"
        assert ws_dir.is_dir(), "workstreams/ directory must exist"
        report_files = list(ws_dir.glob("*_report.md"))
        assert report_files, "expected at least one *_report.md artifact"

        meta = json.loads((proj / "metadata.json").read_text(encoding="utf-8"))
        workstreams = meta.get("workstreams") or {}
        assert workstreams, "metadata.workstreams must record the completed workstream"
        assert any(
            isinstance(entry, dict)
            and entry.get("type") == "argumentation"
            and entry.get("status") == "completed"
            for entry in workstreams.values()
        )
        hypotheses = meta.get("hypotheses") or []
        assert hypotheses, "metadata.hypotheses must be populated from the workstream"

        # living document updated
        doc = proj / "living_document.md"
        assert doc.is_file() and doc.stat().st_size > 0
        doc_text = doc.read_text(encoding="utf-8")
        assert "argumentation" in doc_text.lower() or "Workstream" in doc_text

        # status command should reflect non-zero workstream/hypothesis counts
        status = runner.invoke(cli, ["status"])
        assert status.exit_code == 0, status.output
        m = re.search(r"Workstreams:\s*(\d+)", status.output)
        assert m is not None and int(m.group(1)) >= 1

        show_h = runner.invoke(cli, ["show-hypotheses"])
        assert show_h.exit_code == 0, show_h.output
        assert "No hypotheses" not in show_h.output
        assert "hyp-" in show_h.output

    def test_concept_analysis_workstream_leaves_artifacts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Second workstream type — still offline, still durable."""
        monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        created = runner.invoke(
            cli,
            ["new-project", "Abstraction", "-q", "What is abstraction?"],
        )
        assert created.exit_code == 0, created.output
        match = _PROJECT_ID.search(created.output)
        assert match is not None
        project_id = match.group(1)

        started = runner.invoke(cli, ["start-workstream", "concept_analysis"])
        assert started.exit_code == 0, started.output

        proj = tmp_path / "projects" / project_id
        ws_dir = proj / "workstreams"
        report_files = list(ws_dir.glob("*_report.md"))
        assert report_files, "expected *_report.md from concept_analysis"

        meta = json.loads((proj / "metadata.json").read_text(encoding="utf-8"))
        workstreams = meta.get("workstreams") or {}
        assert any(
            isinstance(e, dict) and e.get("type") == "concept_analysis"
            for e in workstreams.values()
        )
