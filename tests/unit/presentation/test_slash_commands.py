"""Unit tests for slash command parser and router (T-019)."""

import pytest

from aicophilosopher.domain.entities.session import SessionState


@pytest.fixture
def session() -> SessionState:
    return SessionState(project_id="proj-001")


# ── Help ────────────────────────────────────────────────────────────────


def test_help(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/help", session)
    assert "commands" in result["message"].lower()


# ── Exit ────────────────────────────────────────────────────────────────


def test_exit(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/exit", session)
    assert result["action"] == "exit"


def test_quit_alias(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/quit", session)
    assert result["action"] == "exit"


# ── Status ──────────────────────────────────────────────────────────────


def test_status(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/status", session)
    assert session.project_id in result.get("summary", "")


# ── Toggle commands ─────────────────────────────────────────────────────


def test_details_toggle(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    dispatch("/details", session)
    assert session.current_focus.toggle_state.show_details is True


def test_hide_details(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    session.current_focus.toggle_state.show_details = True
    dispatch("/hide-details", session)
    assert session.current_focus.toggle_state.show_details is False


def test_suggestions_toggle(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    dispatch("/suggestions", session)
    assert session.current_focus.toggle_state.show_suggestions is True


def test_hide_suggestions(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    session.current_focus.toggle_state.show_suggestions = True
    dispatch("/hide-suggestions", session)
    assert session.current_focus.toggle_state.show_suggestions is False


# ── Unknown command ─────────────────────────────────────────────────────


def test_unknown_command(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/xyz", session)
    assert "unknown" in result["message"].lower()


# ── Missing args ────────────────────────────────────────────────────────


def test_search_requires_arg(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/search", session)
    assert "requires" in result["message"].lower()


def test_steer_requires_arg(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/steer", session)
    assert "requires" in result["message"].lower()


# ── Commands with args ──────────────────────────────────────────────────


def test_search_with_arg(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/search compatibilism", session)
    assert "acknowledged" in result["message"].lower()


def test_steer_with_arg(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/steer ws-001 focus on post-1980", session)
    assert "acknowledged" in result["message"].lower()


# ── All 28 commands registered ──────────────────────────────────────────


def test_all_commands_registered(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import COMMANDS

    assert len(COMMANDS) >= 28


def test_all_commands_dispatch_without_error(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import COMMANDS, dispatch

    for cmd in COMMANDS:
        result = dispatch(cmd, session)
        assert isinstance(result, dict)
