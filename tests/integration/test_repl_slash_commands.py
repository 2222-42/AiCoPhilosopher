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
    # Full slash_commands registry, not the local stub list
    assert "not yet implemented" in result["message"].lower() or "*" in result["message"]


@pytest.mark.asyncio
async def test_status_via_repl(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    # /status now routes to coordinator.run(command="status")
    mock_coordinator.run.return_value = {
        "summary": f"Project: {session.project_id}",
        "epistemic_status": "clarifying (turn 2/5)",
    }
    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input(
            "/status", session, mock_coordinator, mock_llm, test_mode=True
        )
    assert session.project_id in result.get("summary", "")
    mock_coordinator.run.assert_called_with(command="status")


@pytest.mark.asyncio
async def test_pause_resume_via_repl_are_unimplemented(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    """Pause/resume validate workstream ids but must not pretend to control them."""
    from aicophilosopher.presentation.repl import _process_input

    session.active_workstreams = ["ws-001"]
    with patch("aicophilosopher.presentation.repl.render_response"):
        r1 = await _process_input(
            "/pause ws-001", session, mock_coordinator, mock_llm, test_mode=True
        )
        r2 = await _process_input(
            "/resume ws-001", session, mock_coordinator, mock_llm, test_mode=True
        )
    assert r1 is not None and r2 is not None
    assert "Not implemented" in r1["message"]
    assert "Not implemented" in r2["message"]
    assert r1.get("implemented") is False
    assert r2.get("implemented") is False
    mock_coordinator.run.assert_not_called()


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
async def test_export_command_via_repl_is_unimplemented(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input(
            "/export markdown", session, mock_coordinator, mock_llm, test_mode=True
        )
    assert result is not None
    assert "Not implemented" in result["message"]
    assert result.get("implemented") is False
    assert "Exporting" not in result["message"]


@pytest.mark.asyncio
async def test_search_via_repl_calls_coordinator(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    """Major inquiry slash commands must invoke Coordinator, not echo-only."""
    from aicophilosopher.presentation.repl import _process_input

    mock_coordinator.run.return_value = {
        "message": "Workstream 'literature_search' launched as ws-1.",
        "workstream_type": "literature_search",
        "workstream_id": "ws-1",
    }
    mock_coordinator.active_workstreams = {"ws-1": {"status": "running"}}

    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input(
            "/search free will", session, mock_coordinator, mock_llm, test_mode=True
        )

    mock_coordinator.run.assert_called_once_with(
        user_input="free will",
        command="propose_workstream",
        workstream_type="literature_search",
    )
    assert result is not None
    assert "literature_search" in result.get("message", "") or result.get(
        "workstream_type"
    ) == "literature_search"
    assert session.active_workstreams == ["ws-1"]


@pytest.mark.asyncio
async def test_analyze_via_repl_calls_coordinator(
    session: SessionState, mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    mock_coordinator.run.return_value = {
        "message": "Workstream 'concept_analysis' launched as ws-1.",
        "workstream_type": "concept_analysis",
    }
    with patch("aicophilosopher.presentation.repl.render_response"):
        await _process_input(
            "/analyze intentionality", session, mock_coordinator, mock_llm, test_mode=True
        )

    mock_coordinator.run.assert_called_once_with(
        user_input="intentionality",
        command="propose_workstream",
        workstream_type="concept_analysis",
    )
