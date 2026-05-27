"""Unit tests for slash command parser and router (T-019)."""

import pytest

from aicophilosopher.domain.entities.session import SessionState


@pytest.fixture
def session() -> SessionState:
    return SessionState(project_id="proj-001")


# ── Help / Exit ──────────────────────────────────────────────────────

def test_help(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/help", session)
    assert "Session" in result["message"]
    assert "Inquiry" in result["message"]


def test_exit(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/exit", session)
    assert result["action"] == "exit"


# ── Required args validation ─────────────────────────────────────────

def test_search_requires_arg(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/search", session)
    assert "Usage" in result["message"]


def test_steer_requires_two_args(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/steer ws-001", session)
    assert "Usage" in result["message"]


def test_steer_with_two_args_ok(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/steer ws-001 focus on compatibilism", session)
    assert "Steering" in result["message"]


# ── Quoted argument parsing ──────────────────────────────────────────

def test_quoted_args_preserved(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch('/new "What is truth?"', session)
    assert "What is truth?" in result["message"]


# ── Pause / Resume with workstream validation ────────────────────────

def test_pause_no_workstreams(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/pause", session)
    assert "No workstreams" in result["message"]


def test_pause_invalid_ws_id(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    session.active_workstreams = ["ws-001"]
    result = dispatch("/pause ws-999", session)
    assert "not found" in result["message"]


def test_pause_ambiguous_multiple(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    session.active_workstreams = ["ws-001", "ws-002"]
    result = dispatch("/pause", session)
    assert "Which workstream?" in result["message"]


def test_pause_single_auto_selects(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    session.active_workstreams = ["ws-001"]
    result = dispatch("/pause", session)
    assert "ws-001 paused" in result["message"].lower()


# ── Archive confirmation ─────────────────────────────────────────────

def test_archive_prompts_confirmation(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/archive", session)
    assert "Are you sure" in result["message"]


# ── Toggle commands ──────────────────────────────────────────────────

def test_details_toggle(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    dispatch("/details", session)
    assert session.current_focus.toggle_state.show_details is True


def test_hide_details(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    session.current_focus.toggle_state.show_details = True
    dispatch("/hide-details", session)
    assert session.current_focus.toggle_state.show_details is False


# ── Unknown command ──────────────────────────────────────────────────

def test_unknown_command(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/xyz", session)
    assert "Unknown" in result["message"]


# ── All commands registered ──────────────────────────────────────────

def test_all_commands_dispatch_without_error(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    # All known commands (matching the help output)
    cmds = [
        "/help", "/exit", "/quit", "/new x", "/open x", "/projects", "/archive",
        "/search x", "/analyze x", "/argue x", "/review", "/compare x", "/synthesize",
        "/pause", "/resume", "/steer ws x", "/deepen x", "/abandon x",
        "/status", "/hypotheses", "/dead-ends", "/document",
        "/details", "/hide-details", "/suggestions", "/hide-suggestions",
        "/export x", "/add-note x", "/upload x", "/help-request", "/config",
    ]
    for cmd in cmds:
        result = dispatch(cmd, session)
        assert isinstance(result, dict)


# ── /status ──────────────────────────────────────────────────────────

def test_status(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/status", session)
    assert session.project_id in result.get("summary", "")
