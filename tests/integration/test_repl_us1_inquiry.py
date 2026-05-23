"""Integration tests for US1: natural language inquiry end-to-end (T-014)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aicophilosopher.domain.entities.session import FocusContext, SessionState, SpeakerType
from aicophilosopher.ports.llm_port import GenerationResult


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=GenerationResult(
            text='{"intent_type":"start_inquiry","confidence":0.95,'
            '"extracted_entities":{"topic":"free will"},"alternative_intents":[],'
            '"needs_clarification":false}'
        )
    )
    return llm


@pytest.fixture
def mock_coordinator() -> MagicMock:
    coord = MagicMock()
    coord.run = AsyncMock(
        return_value={
            "message": "That's a rich question. Let me clarify your angle...",
            "dialogue_state": "clarifying",
            "turn": 1,
        }
    )
    return coord


@pytest.fixture
def test_session() -> SessionState:
    return SessionState(project_id="proj-001")


# ── Full inquiry flow ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_inquiry_flow(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    """Launch REPL → type question → NLU → coordinator → render."""
    from aicophilosopher.presentation.nlu import classify_intent
    from aicophilosopher.presentation.repl import _process_input
    from aicophilosopher.presentation.rendering import render_response

    result = await _process_input(
        "I want to explore free will",
        test_session,
        mock_coordinator,
        mock_llm,
        test_mode=True,
    )
    assert result is not None
    assert "dialogue_state" in result


@pytest.mark.asyncio
async def test_clarification_dialogue(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    """User answers coordinator's Socratic question."""
    from aicophilosopher.presentation.repl import _process_input

    mock_llm.generate = AsyncMock(
        return_value=GenerationResult(
            text='{"intent_type":"clarify_question","confidence":0.90,'
            '"extracted_entities":{"angle":"ontological"},"alternative_intents":[],'
            '"needs_clarification":false}'
        )
    )
    result = await _process_input(
        "From an ontological angle",
        test_session,
        mock_coordinator,
        mock_llm,
        test_mode=True,
    )
    assert result is not None


@pytest.mark.asyncio
async def test_empty_input_no_crash(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    """Empty input returns None, no crash."""
    from aicophilosopher.presentation.repl import _process_input

    result = await _process_input("", test_session, mock_coordinator, mock_llm, test_mode=True)
    assert result is None


@pytest.mark.asyncio
async def test_exit_command_finalizes_session(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    """Slash exit triggers session finalization."""
    from aicophilosopher.presentation.repl import _process_input

    result = await _process_input(
        "/exit", test_session, mock_coordinator, mock_llm, test_mode=True
    )
    assert test_session.status.value == "paused"
    assert result is not None


@pytest.mark.asyncio
async def test_five_turn_conversation(
    mock_llm: MagicMock, mock_coordinator: MagicMock
) -> None:
    """5-turn conversation — verify all turns processed."""
    from aicophilosopher.presentation.repl import _process_input

    session = SessionState(project_id="proj-001")
    turns = [
        "I want to explore free will",
        "From an ontological angle",
        "Focus on compatibilism",
        "How are things going?",
        "/exit",
    ]
    for i, turn in enumerate(turns):
        if turn == "/exit":
            mock_llm.generate = AsyncMock(return_value=GenerationResult(text="{}"))
        await _process_input(turn, session, mock_coordinator, mock_llm, test_mode=True)

    assert session.status.value == "paused"
