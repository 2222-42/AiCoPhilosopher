"""Unit tests for progressive disclosure renderer (T-012)."""

from io import StringIO

import pytest
from rich.console import Console

from aicophilosopher.domain.entities.session import FocusContext


@pytest.fixture
def console() -> Console:
    return Console(file=StringIO(), force_terminal=True, width=100, no_color=True, markup=False)


@pytest.fixture
def focus() -> FocusContext:
    return FocusContext()


def _render_capture(console: Console, response: dict, focus: FocusContext) -> str:
    from aicophilosopher.presentation.rendering import render_response

    render_response(response, focus, console)
    return console.file.getvalue()  # type: ignore[union-attr]


# ── Summary always visible ───────────────────────────────────────────────


def test_summary_always_visible(console: Console, focus: FocusContext) -> None:
    output = _render_capture(console, {"summary": "Hello world"}, focus)
    assert "Hello world" in output


def test_summary_truncated_at_five_lines(console: Console, focus: FocusContext) -> None:
    long_summary = "\n".join(f"Line {i}" for i in range(1, 8))
    output = _render_capture(console, {"summary": long_summary}, focus)
    assert "Line 6" not in output or "[...]" in output


# ── Epistemic status always visible ──────────────────────────────────────


def test_epistemic_status_rendered(console: Console, focus: FocusContext) -> None:
    output = _render_capture(
        console,
        {"epistemic_status": "Confidence: 0.85 | Tradition: Analytic"},
        focus,
    )
    assert "Confidence: 0.85" in output


# ── Active workstreams ───────────────────────────────────────────────────


def test_workstreams_rendered_when_present(console: Console, focus: FocusContext) -> None:
    output = _render_capture(
        console,
        {"active_workstreams": ["WS-001: running", "WS-002: completed"]},
        focus,
    )
    assert "WS-001" in output


def test_workstreams_omitted_when_empty(console: Console, focus: FocusContext) -> None:
    output = _render_capture(console, {}, focus)
    assert "Active Workstreams" not in output


# ── Details toggle ───────────────────────────────────────────────────────


def test_details_collapsed_by_default(console: Console, focus: FocusContext) -> None:
    output = _render_capture(
        console, {"details": "Deep analysis here"}, focus
    )
    assert "[Details]" in output
    assert "Deep analysis here" not in output


def test_details_expanded_when_toggled(console: Console, focus: FocusContext) -> None:
    focus.toggle_state.show_details = True
    output = _render_capture(
        console, {"details": "Deep analysis here"}, focus
    )
    assert "Deep analysis here" in output


# ── Suggestions toggle ───────────────────────────────────────────────────


def test_suggestions_collapsed_by_default(console: Console, focus: FocusContext) -> None:
    output = _render_capture(
        console, {"suggestions": ["Try argumentation"]}, focus
    )
    assert "[Suggestions]" in output
    assert "Try argumentation" not in output


def test_suggestions_expanded_when_toggled(console: Console, focus: FocusContext) -> None:
    focus.toggle_state.show_suggestions = True
    output = _render_capture(
        console, {"suggestions": ["Try argumentation"]}, focus
    )
    assert "Try argumentation" in output


# ── Approval requests ────────────────────────────────────────────────────


def test_approval_request_surfaced(console: Console, focus: FocusContext) -> None:
    output = _render_capture(
        console,
        {
            "summary": "I found frameworks",
            "is_approval_request": True,
            "approval_options": ["Analytic", "Phenomenology", "Pragmatism"],
        },
        focus,
    )
    assert "Approval" in output


# ── System messages ──────────────────────────────────────────────────────


def test_system_message_style(console: Console, focus: FocusContext) -> None:
    output = _render_capture(
        console,
        {"message": "Workstream WS-001 completed"},
        focus,
    )
    assert "WS-001" in output or "completed" in output


# ── Empty sections ───────────────────────────────────────────────────────


def test_empty_details_shows_placeholder(console: Console, focus: FocusContext) -> None:
    focus.toggle_state.show_details = True
    output = _render_capture(console, {}, focus)
    assert "No additional details" in output


def test_empty_suggestions_shows_placeholder(console: Console, focus: FocusContext) -> None:
    focus.toggle_state.show_suggestions = True
    output = _render_capture(console, {}, focus)
    assert "No suggestions" in output


# ── T-021: Slash command response rendering ──────────────────────────


def test_status_command_renders_summary(console: Console, focus: FocusContext) -> None:
    from aicophilosopher.domain.entities.session import SessionState
    from aicophilosopher.presentation.slash_commands import dispatch

    session = SessionState(project_id="proj-001")
    result = dispatch("/status", session)
    output = _render_capture(console, result, focus)
    assert "proj-001" in output


def test_help_command_renders_message(console: Console, focus: FocusContext) -> None:
    from aicophilosopher.domain.entities.session import SessionState
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/help", SessionState(project_id="p1"))
    output = _render_capture(console, result, focus)
    assert "commands" in output.lower()


def test_error_command_renders_usage(console: Console, focus: FocusContext) -> None:
    from aicophilosopher.domain.entities.session import SessionState
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/search", SessionState(project_id="p1"))
    output = _render_capture(console, result, focus)
    assert "Usage" in output


def test_archive_command_renders_approval(console: Console, focus: FocusContext) -> None:
    from aicophilosopher.domain.entities.session import SessionState
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/archive", SessionState(project_id="p1"))
    output = _render_capture(console, result, focus)
    assert "Approval" in output
