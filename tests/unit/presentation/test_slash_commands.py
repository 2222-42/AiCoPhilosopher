"""Unit tests for slash command parser and router (T-019 / Issue #59)."""

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


def test_steer_with_two_args_is_unimplemented(session: SessionState) -> None:
    """/steer is registered but not wired — must not pretend success."""
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/steer ws-001 focus on compatibilism", session)
    assert result.get("implemented") is False
    assert "Not implemented" in result["message"]
    assert "error" in result


# ── Quoted argument parsing ──────────────────────────────────────────


def test_quoted_args_preserved(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch('/search "What is truth?"', session)
    assert result["action"] == "propose_workstream"
    assert "What is truth?" in result["user_input"]


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


def test_pause_single_is_unimplemented(session: SessionState) -> None:
    """Validation passes, but pause is not wired — no fake success."""
    from aicophilosopher.presentation.slash_commands import dispatch

    session.active_workstreams = ["ws-001"]
    result = dispatch("/pause", session)
    assert result.get("implemented") is False
    assert "Not implemented" in result["message"]
    assert "paused" not in result["message"].lower() or "not implemented" in result["message"].lower()


# ── Archive is not a fake approval flow ──────────────────────────────


def test_archive_is_unimplemented(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/archive", session)
    assert result.get("implemented") is False
    assert "Not implemented" in result["message"]
    assert result.get("is_approval_request") is not True


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

    cmds = [
        "/help",
        "/exit",
        "/quit",
        "/new x",
        "/open x",
        "/projects",
        "/archive",
        "/search x",
        "/analyze x",
        "/argue x",
        "/review",
        "/compare x",
        "/synthesize",
        "/pause",
        "/resume",
        "/steer ws x",
        "/deepen x",
        "/abandon x",
        "/status",
        "/hypotheses",
        "/dead-ends",
        "/document",
        "/details",
        "/hide-details",
        "/suggestions",
        "/hide-suggestions",
        "/export x",
        "/add-note x",
        "/upload x",
        "/help-request",
        "/config",
    ]
    for cmd in cmds:
        result = dispatch(cmd, session)
        assert isinstance(result, dict)


# ── Inquiry → coordinator action ─────────────────────────────────────


@pytest.mark.parametrize(
    ("cmd", "ws_type"),
    [
        ("/search free will", "literature_search"),
        ("/analyze intentionality", "concept_analysis"),
        ("/argue compatibilism", "argumentation"),
        ("/compare free will", "cross_traditional_comparison"),
        ("/review", "critical_review"),
        ("/synthesize", "synthesis"),
    ],
)
def test_inquiry_commands_return_propose_workstream(
    session: SessionState, cmd: str, ws_type: str
) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch(cmd, session)
    assert result["action"] == "propose_workstream"
    assert result["workstream_type"] == ws_type
    # Must not look like a completed search/analysis
    assert "Searching for" not in result.get("message", "")
    assert "Analyzing concept" not in result.get("message", "")
    assert "acknowledged" not in result.get("message", "").lower()


# ── Echo-only commands are explicitly unimplemented ──────────────────


@pytest.mark.parametrize(
    "cmd",
    [
        "/new question",
        "/open proj-1",
        "/projects",
        "/export markdown",
        "/add-note hello",
        "/upload path.pdf",
        "/help-request",
        "/config key=value",
        "/hypotheses",
        "/dead-ends",
        "/document",
        "/deepen concept",
        "/abandon h-1",
    ],
)
def test_echo_only_commands_are_unimplemented(session: SessionState, cmd: str) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch(cmd, session)
    assert result.get("implemented") is False
    assert "Not implemented" in result["message"]
    assert "error" in result
    # Must not pretend success (progressive/completed verbs as the primary claim)
    lower = result["message"].lower()
    for fake in (
        "creating new project",
        "opening project",
        "exporting as",
        "acknowledged",
        "help request sent",
    ):
        assert fake not in lower


# ── /status ──────────────────────────────────────────────────────────


def test_status(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/status", session)
    assert session.project_id in result.get("summary", "")


# ── T-021: Response rendering format checks ──────────────────────────


def test_status_response_has_summary(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/status", session)
    assert "summary" in result


def test_help_response_has_categories(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/help", session)
    assert "Session" in result["message"]
    assert "Steering" in result["message"]


def test_error_response_starts_with_usage(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/search", session)
    assert result["message"].startswith("Usage")


def test_toggle_commands_return_message(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/details", session)
    assert "message" in result
    assert "Details" in result["message"]


def test_archive_response_not_approval(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/archive", session)
    assert result.get("is_approval_request") is not True
    assert result.get("implemented") is False
