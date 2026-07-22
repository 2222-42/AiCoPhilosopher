"""Unit tests for Config — workspace path and AICOPH_* env prefix (Issue #62)."""

from __future__ import annotations

from pathlib import Path

from aicophilosopher.domain.services.config import (
    DEFAULT_WORKSPACE_DIR,
    Config,
)


def test_default_workspace_dir(monkeypatch) -> None:
    # Hermetic: ambient AICOPH_WORKSPACE_DIR (e.g. Track A .verify-ws) must not leak in.
    monkeypatch.delenv("AICOPH_WORKSPACE_DIR", raising=False)
    cfg = Config()
    assert cfg.workspace_dir == DEFAULT_WORKSPACE_DIR
    assert cfg.workspace_dir == "~/.aicophilosopher"


def test_resolved_workspace_dir_expands_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path / "ws"))
    cfg = Config()
    resolved = cfg.resolved_workspace_dir()
    assert resolved == (tmp_path / "ws").resolve()
    assert resolved.is_absolute()


def test_projects_dir_nests_under_workspace(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path))
    cfg = Config()
    assert cfg.projects_dir() == tmp_path.resolve() / "projects"


def test_aicoph_env_prefix_llm_backend(monkeypatch) -> None:
    monkeypatch.delenv("AICOPH_WORKSPACE_DIR", raising=False)
    monkeypatch.setenv("AICOPH_LLM_BACKEND", "claude")
    cfg = Config()
    assert cfg.llm_backend == "claude"


def test_bare_env_names_are_ignored(monkeypatch) -> None:
    """Docs previously used LLM_BACKEND / WORKSPACE_DIR without AICOPH_ prefix.

    Those bare names must not affect Config (prefix is the contract).
    """
    monkeypatch.delenv("AICOPH_LLM_BACKEND", raising=False)
    monkeypatch.delenv("AICOPH_WORKSPACE_DIR", raising=False)
    monkeypatch.setenv("LLM_BACKEND", "gemini")
    monkeypatch.setenv("WORKSPACE_DIR", "/tmp/wrong")
    cfg = Config()
    assert cfg.llm_backend == "ollama"
    assert cfg.workspace_dir == DEFAULT_WORKSPACE_DIR
