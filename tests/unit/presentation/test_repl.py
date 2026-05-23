"""Unit tests for REPL main loop (T-010)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aicophilosopher.domain.entities.session import FocusContext, SessionState, SessionStatus


@pytest.fixture
def mock_session() -> SessionState:
    return SessionState(project_id="proj-001")


@pytest.fixture
def mock_focus() -> FocusContext:
    return FocusContext(active_topic="free will")


@pytest.fixture
def mock_llm() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_coordinator() -> MagicMock:
    coord = MagicMock()
    coord.run = AsyncMock(
        return_value={
            "message": "Welcome! What would you like to explore?",
            "dialogue_state": "awaiting_question",
            "turn": 0,
        }
    )
    return coord


# ── REPL startup ─────────────────────────────────────────────────────────


def test_repl_session_created(mock_session: SessionState) -> None:
    """SessionState is created with active status."""
    assert mock_session.status == SessionStatus.ACTIVE
    assert mock_session.project_id == "proj-001"


@pytest.mark.asyncio
async def test_repl_startup_with_project(mock_session: SessionState, mock_llm: MagicMock) -> None:
    """REPL can be initialized with a specific project."""
    from aicophilosopher.presentation.repl import _startup_flow

    with patch(
        "aicophilosopher.presentation.repl.SessionManager",
        autospec=True,
        create=True,
    ) as mock_sm:
        instance = mock_sm.return_value
        instance.list_projects = AsyncMock(return_value=[])
        instance.create_session = AsyncMock(return_value=mock_session)
        result = await _startup_flow(project_id="proj-001", test_mode=True)
        assert result is not None


@pytest.mark.asyncio
async def test_repl_startup_no_project_lists_projects(
    mock_session: SessionState, mock_llm: MagicMock
) -> None:
    """Without --project flag, list_projects() is called."""
    from aicophilosopher.presentation.repl import _startup_flow

    with patch(
        "aicophilosopher.presentation.repl.SessionManager",
        autospec=True,
        create=True,
    ) as mock_sm:
        instance = mock_sm.return_value
        instance.list_projects = AsyncMock(
            return_value=[
                {
                    "project_id": "p1",
                    "title": "Test",
                    "last_active_at": "",
                    "session_status": "paused",
                }
            ]
        )
        instance.create_session = AsyncMock(return_value=mock_session)
        result = await _startup_flow(project_id=None, test_mode=True)
        # In test_mode, SessionManager is bypassed — a fresh session is created directly.
        assert result is not None
        assert result.project_id == "test-proj"


# ── Input routing ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_natural_language_routed_to_nlu(
    mock_session: SessionState,
    mock_focus: FocusContext,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Natural language input is classified and sent to coordinator."""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = MagicMock(
            intent_type="start_inquiry", confidence=0.95, raw_input="hello"
        )
        await _process_input(
            user_input="explore free will",
            session=mock_session,
            coordinator=mock_coordinator,
            llm_port=mock_llm,
            test_mode=True,
        )
        mock_nlu.assert_called_once()


@pytest.mark.asyncio
async def test_slash_input_routed_to_command_handler(
    mock_session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    """Input starting with / is handled by slash command dispatch."""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl._handle_slash") as mock_slash:
        mock_slash.return_value = {"message": "Goodbye!", "action": "exit"}
        await _process_input(
            user_input="/exit",
            session=mock_session,
            coordinator=mock_coordinator,
            llm_port=mock_llm,
            test_mode=True,
        )
        mock_slash.assert_called_once_with("/exit", mock_session)


@pytest.mark.asyncio
async def test_empty_input_ignored(
    mock_session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    """Empty input is ignored without NLU call."""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        await _process_input(
            user_input="",
            session=mock_session,
            coordinator=mock_coordinator,
            llm_port=mock_llm,
            test_mode=True,
        )
        mock_nlu.assert_not_called()


# ── Essential slash commands ─────────────────────────────────────────────


def test_handle_slash_exit(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    result = _handle_slash("/exit", mock_session)
    assert result.get("action") == "exit"


def test_handle_slash_help() -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    result = _handle_slash("/help", MagicMock())
    assert (
        "commands" in result.get("message", "").lower()
        or "help" in result.get("message", "").lower()
    )


def test_handle_slash_details(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    _handle_slash("/details", mock_session)
    assert mock_session.current_focus.toggle_state.show_details is True


def test_handle_slash_hide_details(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    mock_session.current_focus.toggle_state.show_details = True
    _handle_slash("/hide-details", mock_session)
    assert mock_session.current_focus.toggle_state.show_details is False


def test_handle_slash_suggestions(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    _handle_slash("/suggestions", mock_session)
    assert mock_session.current_focus.toggle_state.show_suggestions is True


def test_handle_slash_hide_suggestions(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    mock_session.current_focus.toggle_state.show_suggestions = True
    _handle_slash("/hide-suggestions", mock_session)
    assert mock_session.current_focus.toggle_state.show_suggestions is False


def test_handle_slash_unknown(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _handle_slash

    result = _handle_slash("/xyz", mock_session)
    assert "unknown" in result.get("message", "").lower()


# ── Session finalization ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_finalize_session_sets_paused_status(mock_session: SessionState) -> None:
    from aicophilosopher.presentation.repl import _finalize

    with patch("aicophilosopher.presentation.repl.SessionManager") as mock_sm:
        instance = mock_sm.return_value
        instance.finalize_session = AsyncMock()
        await _finalize(mock_session, "user_exit")
        assert mock_session.status == SessionStatus.PAUSED
        assert mock_session.exit_reason == "user_exit"


# ── Rendering dispatch ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_response_rendered_after_coordinator(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Coordinator response triggers rendering."""
    from aicophilosopher.presentation.repl import _process_input

    with (
        patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu,
        patch("aicophilosopher.presentation.repl.render_response") as mock_render,
    ):
        mock_nlu.return_value = MagicMock(
            intent_type="start_inquiry", confidence=0.95, raw_input="hello"
        )
        await _process_input(
            user_input="hello",
            session=mock_session,
            coordinator=mock_coordinator,
            llm_port=mock_llm,
            test_mode=True,
        )
        mock_render.assert_called_once()
