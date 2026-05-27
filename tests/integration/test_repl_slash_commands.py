"""Integration tests for slash commands — US3 (T-023)."""

import pytest

from aicophilosopher.domain.entities.session import SessionState


@pytest.fixture
def session() -> SessionState:
    return SessionState(project_id="proj-001")


def test_help_lists_all_categories(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/help", session)
    for cat in ("Session", "Inquiry", "Steering", "View", "Export", "Config"):
        assert cat in result["message"]


def test_status_includes_project_id(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/status", session)
    assert session.project_id in result.get("summary", "")


def test_pause_resume_workstream_lifecycle(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    session.active_workstreams = ["ws-001"]
    r1 = dispatch("/pause ws-001", session)
    assert "paused" in r1["message"].lower()
    r2 = dispatch("/resume ws-001", session)
    assert "resumed" in r2["message"].lower()


def test_toggle_details_roundtrip(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    dispatch("/details", session)
    assert session.current_focus.toggle_state.show_details is True
    dispatch("/hide-details", session)
    assert session.current_focus.toggle_state.show_details is False


def test_unknown_command_returns_help_hint(session: SessionState) -> None:
    from aicophilosopher.presentation.slash_commands import dispatch

    result = dispatch("/xyz", session)
    assert "/help" in result["message"]
