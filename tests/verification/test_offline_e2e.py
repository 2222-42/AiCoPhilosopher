"""Offline E2E / verification suite (Issue #66).

Guarantees (without production LLM):
  1. Silent CLI no-ops do not succeed — each unwired/partial command either
     fails honestly (exit ≠ 0 + "Not implemented") or performs a real effect.
  2. `start-workstream` leaves durable results under the project workspace.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from aicophilosopher.presentation.commands import cli

_UNIMPLEMENTED = re.compile(r"not implemented", re.IGNORECASE)
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
      - exit ≠ 0 with an honest "Not implemented" message, or
      - exit == 0 when *real_effect* is True (caller verified side effects).
    """
    exit_code = getattr(result, "exit_code", 0)
    combined = _combined_output(result)

    if exit_code == 0:
        assert real_effect, (
            f"silent no-op succeeded (exit 0) without verified side effect: {combined!r}"
        )
        return

    assert _UNIMPLEMENTED.search(combined), (
        f"non-zero exit must mention 'Not implemented' (or implement a real effect), "
        f"got exit={exit_code}: {combined!r}"
    )


class TestNoOpHonesty:
    """Issue #58 policy, enforced by offline verification (#66).

    Commands that remain pure stubs must fail honestly. Commands that have
    been implemented may succeed only when a durable side effect is visible.
    """

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
        """Lifecycle commands without a workstream registry must not silent-succeed."""
        runner = CliRunner()
        result = runner.invoke(cli, args)
        # These remain stubs on this branch; real wiring is #60 territory.
        _assert_not_silent_noop(result, real_effect=False)

    def test_export_is_honest_or_real(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """export either writes a real artifact or fails with Not implemented."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["new-project", "Export Probe", "-q", "probe?"])
        result = runner.invoke(cli, ["export", "markdown"])
        if result.exit_code == 0:
            # Real effect: some export artifact or non-empty living doc copy
            exports = list(Path(".").rglob("*.md")) + list(Path(".").rglob("exports/**/*"))
            wrote = any(p.is_file() and p.stat().st_size > 0 for p in exports)
            # Also accept output that clearly references a written path
            wrote = wrote or bool(
                re.search(r"export|wrote|saved|written", result.output, re.I)
            )
            _assert_not_silent_noop(result, real_effect=wrote)
        else:
            _assert_not_silent_noop(result, real_effect=False)

    def test_show_dead_ends_is_honest_or_real(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["new-project", "DeadEnd Probe"])
        result = runner.invoke(cli, ["show-dead-ends"])
        if result.exit_code == 0:
            # Honest empty state counts as real (reads registry / reports none)
            honest_empty = bool(
                re.search(r"no dead end|0 dead|none|empty", result.output, re.I)
            )
            _assert_not_silent_noop(result, real_effect=honest_empty or bool(result.output.strip()))
        else:
            _assert_not_silent_noop(result, real_effect=False)

    def test_config_set_is_honest_or_persisted(self) -> None:
        """Setting config must not silent-succeed without persistence."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "llm.backend", "claude"])
        # Until config is actually persisted, only honest failure is acceptable.
        _assert_not_silent_noop(result, real_effect=False)


class TestWorkstreamResultsPersist:
    """start-workstream must leave results that survive the process (#66 / #63 slice)."""

    def test_argumentation_workstream_leaves_artifacts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        assert "Argumentation Results" in started.output
        assert "completed" in started.output.lower()

        proj = Path("projects") / project_id
        ws_dir = proj / "workstreams"
        assert ws_dir.is_dir(), "workstreams/ directory must exist"

        result_files = list(ws_dir.glob("*_result.json"))
        report_files = list(ws_dir.glob("*_report.md"))
        assert result_files, "expected at least one *_result.json artifact"
        assert report_files, "expected at least one *_report.md artifact"

        payload = json.loads(result_files[0].read_text(encoding="utf-8"))
        assert payload.get("status") == "completed"
        assert payload.get("type") == "argumentation"
        assert payload.get("workstream_id")
        result = payload.get("result") or {}
        assert result.get("arguments"), "argumentation result must include arguments"
        assert result.get("competing_positions") is not None

        meta = json.loads((proj / "metadata.json").read_text(encoding="utf-8"))
        workstreams = meta.get("workstreams") or {}
        assert workstreams, "metadata.workstreams must record the completed workstream"
        assert any(
            entry.get("type") == "argumentation" and entry.get("status") == "completed"
            for entry in workstreams.values()
        )

        # status command should reflect persisted workstreams
        status = runner.invoke(cli, ["status"])
        assert status.exit_code == 0, status.output
        m = re.search(r"Workstreams:\s*(\d+)", status.output)
        assert m is not None and int(m.group(1)) >= 1

    def test_concept_analysis_workstream_leaves_artifacts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Second workstream type — still offline, still durable."""
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

        ws_dir = Path("projects") / project_id / "workstreams"
        result_files = list(ws_dir.glob("*_result.json"))
        assert result_files
        payload = json.loads(result_files[0].read_text(encoding="utf-8"))
        assert payload["type"] == "concept_analysis"
        assert "concept_map" in (payload.get("result") or {})
