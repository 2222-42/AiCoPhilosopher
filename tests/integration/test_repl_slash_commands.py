"""Integration tests for slash commands — US3 (T-023)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aicophilosopher.domain.entities.session import SessionState


@pytest.fixture
def session() -> SessionState:
    return SessionState(project_id="proj-001")


@pytest.fixture
def mock_llm() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_coordinator() -> MagicMock:
    coord = MagicMock()
    coord.run = AsyncMock(return_value={"message": "ok"})
    return coord


# ── REPL-driven tests via _process_input ─────────────────────────────


@pytest.mark.asyncio
async def test_help_via_repl(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input("/help", session, mock_coordinator, mock_llm, test_mode=True)
    assert result is not None
    assert "commands" in result["message"].lower()


@pytest.mark.asyncio
async def test_status_via_repl(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input(
            "/status", session, mock_coordinator, mock_llm, test_mode=True
        )
    assert session.project_id in result.get("summary", "")


@pytest.mark.asyncio
async def test_pause_resume_via_repl(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    session.active_workstreams = ["ws-001"]
    with patch("aicophilosopher.presentation.repl.render_response"):
        r1 = await _process_input(
            "/pause ws-001", session, mock_coordinator, mock_llm, test_mode=True
        )
        r2 = await _process_input(
            "/resume ws-001", session, mock_coordinator, mock_llm, test_mode=True
        )
    assert "paused" in r1["message"].lower()
    assert "resumed" in r2["message"].lower()


@pytest.mark.asyncio
async def test_toggle_via_repl(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.render_response"):
        await _process_input("/details", session, mock_coordinator, mock_llm, test_mode=True)
    assert session.current_focus.toggle_state.show_details is True


@pytest.mark.asyncio
async def test_unknown_command_via_repl(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input("/xyz", session, mock_coordinator, mock_llm, test_mode=True)
    assert "/help" in result["message"]


# ── Expanded US3 scenarios ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_slash_in_natural_language_not_treated_as_command(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    """Text like 'What does /search do?' should NOT be treated as slash command."""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.render_response"):
        await _process_input(
            "What does /search do?", session, mock_coordinator, mock_llm, test_mode=True
        )
    # Should go through coordinator (NL path), not slash handler
    mock_coordinator.run.assert_called_once()


@pytest.mark.asyncio
async def test_export_command_via_repl(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input(
            "/export markdown", session, mock_coordinator, mock_llm, test_mode=True
        )
    assert "Exporting" in result["message"]
