"""Unit tests for REPL main loop (T-010)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aicophilosopher.domain.entities.session import SessionState, SessionStatus


@pytest.fixture
def mock_session() -> SessionState:
    return SessionState(project_id="proj-001")


@pytest.fixture
def mock_llm() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_coordinator() -> MagicMock:
    coord = MagicMock()
    coord.run = AsyncMock(
        return_value={
            "message": "Welcome!",
            "dialogue_state": "awaiting_question",
            "turn": 0,
        }
    )
    return coord


# ── Startup in test_mode ────────────────────────────────────────────────


def test_test_mode_creates_session(mock_session: SessionState) -> None:
    assert mock_session.status == SessionStatus.ACTIVE


@pytest.mark.asyncio
async def test_startup_test_mode() -> None:
    from aicophilosopher.presentation.repl import _startup_flow

    result = await _startup_flow(project_id="proj-001", test_mode=True)
    assert result is not None
    assert result.project_id == "proj-001"


@pytest.mark.asyncio
async def test_startup_test_mode_no_project() -> None:
    from aicophilosopher.presentation.repl import _startup_flow

    result = await _startup_flow(project_id=None, test_mode=True)
    assert result is not None
    assert result.project_id == "test-proj"


# ── Input routing ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_natural_language_routed(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    result = await _process_input(
        "explore free will", mock_session, mock_coordinator, mock_llm, test_mode=True
    )
    mock_coordinator.run.assert_called_once()
    assert result is not None


@pytest.mark.asyncio
async def test_slash_input_routed(
    mock_session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    result = await _process_input(
        "/exit", mock_session, mock_coordinator, mock_llm, test_mode=True
    )
    assert result is not None
    assert result.get("action") == "exit"


@pytest.mark.asyncio
async def test_empty_input_ignored(
    mock_session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    result = await _process_input(
        "", mock_session, mock_coordinator, mock_llm, test_mode=True
    )
    assert result is None
    mock_coordinator.run.assert_not_called()


# ── Slash commands ──────────────────────────────────────────────────────


def test_slash_help() -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    result = _handle_slash("/help", SessionState(project_id="p1"))
    assert "commands" in result["message"].lower()


def test_slash_details(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    _handle_slash("/details", mock_session)
    assert mock_session.current_focus.toggle_state.show_details is True


def test_slash_hide_details(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    mock_session.current_focus.toggle_state.show_details = True
    _handle_slash("/hide-details", mock_session)
    assert mock_session.current_focus.toggle_state.show_details is False


def test_slash_suggestions(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    _handle_slash("/suggestions", mock_session)
    assert mock_session.current_focus.toggle_state.show_suggestions is True


def test_slash_hide_suggestions(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    mock_session.current_focus.toggle_state.show_suggestions = True
    _handle_slash("/hide-suggestions", mock_session)
    assert mock_session.current_focus.toggle_state.show_suggestions is False


def test_slash_unknown(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    result = _handle_slash("/xyz", mock_session)
    assert "unknown" in result["message"].lower()


# ── Session finalization ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_finalize_sets_paused(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _finalize

    await _finalize(mock_session, "user_exit")
    assert mock_session.status == SessionStatus.PAUSED
    assert mock_session.exit_reason == "user_exit"


# ── Rendering dispatch ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_response_rendered(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.render_response") as mock_render:
        await _process_input(
            "hello", mock_session, mock_coordinator, mock_llm, test_mode=True
        )
        mock_render.assert_called_once()
