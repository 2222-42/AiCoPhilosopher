"""Offline E2E / verification suite (Issue #66).

Guarantees (without production LLM):
  1. Silent CLI no-ops fail honestly (exit ≠ 0 + "Not implemented").
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


def _assert_not_silent_noop(result: object) -> None:
    """CLI must not pretend success for unwired features."""
    exit_code = getattr(result, "exit_code", 0)
    output = getattr(result, "output", "") or ""
    exc = getattr(result, "exception", None)
    combined = f"{output}\n{exc}" if exc else output
    assert exit_code != 0, f"silent no-op succeeded (exit 0): {output!r}"
    assert _UNIMPLEMENTED.search(combined), (
        f"failure must mention 'Not implemented', got: {combined!r}"
    )


class TestNoOpHonesty:
    """Issue #58 policy, enforced by offline verification (#66)."""

    @pytest.mark.parametrize(
        "args",
        [
            ["pause", "ws-001"],
            ["resume", "ws-001"],
            ["steer", "ws-001", "focus on X"],
            ["export", "markdown"],
            ["request-help"],
            ["show-dead-ends"],
            ["config", "llm.backend", "claude"],
        ],
    )
    def test_unwired_commands_fail_honestly(self, args: list[str]) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, args)
        _assert_not_silent_noop(result)


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
        assert "Workstreams: 1" in status.output or "Workstreams: " in status.output
        # extract count
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
