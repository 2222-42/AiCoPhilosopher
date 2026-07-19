"""Regression: workspace path + AICOPH_* env name dualization (Issue #62).

Before the fix:
- CLI hard-coded ``./projects`` while Config defaulted to ``~/.aicophilosopher``
- QUICKSTART documented bare ``LLM_BACKEND`` / ``WORKSPACE_DIR`` without the
  ``AICOPH_`` prefix used by pydantic Settings.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from aicophilosopher.domain.services.config import Config
from aicophilosopher.presentation import commands as commands_mod
from aicophilosopher.presentation.commands import cli

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestIssue62WorkspaceSingleSource:
    def test_cli_workspace_uses_config_not_hardcoded_projects(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path / "custom-ws"))
        ws = commands_mod._get_workspace()
        assert ws == (tmp_path / "custom-ws" / "projects").resolve()
        # Must not fall back to CWD-relative ./projects
        assert ws != Path("projects")
        assert "custom-ws" in str(ws)

    def test_cli_and_filesystem_adapter_share_layout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """CLI project dirs and FileSystemAdapter must agree on layout."""
        from aicophilosopher.infrastructure.adapters.filesystem_adapter import (
            FileSystemAdapter,
        )

        monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path))
        cfg = Config()
        fs = FileSystemAdapter(base_path=cfg.workspace_dir)
        # Adapter stores projects at base/projects/<id>
        assert fs._project_path("proj-abc") == cfg.projects_dir() / "proj-abc"
        assert commands_mod._get_workspace() == cfg.projects_dir()

    def test_new_project_writes_under_configured_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path))
        # Avoid polluting CWD with .current_project
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["new-project", "Issue62 Project"])
        assert result.exit_code == 0, result.output
        projects = list((tmp_path / "projects").glob("proj-*"))
        assert len(projects) == 1
        assert (projects[0] / "metadata.json").exists()

    def test_config_command_shows_resolved_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path))
        runner = CliRunner()
        result = runner.invoke(cli, ["config"])
        assert result.exit_code == 0, result.output
        assert "AICOPH_" in result.output
        assert str(tmp_path.resolve()) in result.output
        assert "projects" in result.output
        # Old hard-coded display must be gone
        assert "./projects/" not in result.output


class TestIssue62DocsEnvNames:
    """Docs must document AICOPH_* names that match Config.env_prefix."""

    def test_quickstart_uses_aicoph_prefix(self) -> None:
        text = (REPO_ROOT / "QUICKSTART.md").read_text(encoding="utf-8")
        # Canonical env names present
        for name in (
            "AICOPH_LLM_BACKEND",
            "AICOPH_WORKSPACE_DIR",
            "AICOPH_ALLOW_EXTERNAL_SEARCH",
            "AICOPH_LOG_LEVEL",
        ):
            assert name in text, f"QUICKSTART.md missing {name}"
        # Bare (wrong) names must not appear as env assignments
        bare = re.findall(
            r"(?m)^(?:export\s+)?(LLM_BACKEND|WORKSPACE_DIR|ALLOW_EXTERNAL_SEARCH|LOG_LEVEL)=",
            text,
        )
        assert bare == [], f"QUICKSTART still documents bare env names: {bare}"


    def test_usage_uses_aicoph_prefix(self) -> None:
        text = (REPO_ROOT / "docs" / "usage.md").read_text(encoding="utf-8")
        for name in (
            "AICOPH_WORKSPACE_DIR",
            "AICOPH_ALLOW_EXTERNAL_SEARCH",
        ):
            assert name in text, f"docs/usage.md missing {name}"
        bare = re.findall(
            r"(?m)^(?:export\s+)?(LLM_BACKEND|WORKSPACE_DIR|ALLOW_EXTERNAL_SEARCH|LOG_LEVEL)=",
            text,
        )
        assert bare == [], f"docs/usage.md still documents bare env names: {bare}"

    def test_pyproject_homepage_points_to_org(self) -> None:
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "github.com/2222-42/AiCoPhilosopher" in text
        assert "anomalyco" not in text
