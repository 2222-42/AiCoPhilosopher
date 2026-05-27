"""Integration tests for US1: natural language inquiry end-to-end (T-014)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aicophilosopher.domain.entities.session import SessionState, SessionStatus
from aicophilosopher.ports.llm_port import GenerationResult


def _nlu_json(intent_type: str, confidence: float = 0.95) -> str:
    return json.dumps(
        {
            "intent_type": intent_type,
            "confidence": confidence,
            "extracted_entities": {"topic": "free will"},
            "alternative_intents": [],
            "needs_clarification": confidence < 0.85,
        }
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=GenerationResult(text=_nlu_json("start_inquiry")))
    return llm


@pytest.fixture
def mock_coordinator() -> MagicMock:
    coord = MagicMock()
    coord.run = AsyncMock(
        return_value={
            "message": "That's a rich question.",
            "dialogue_state": "clarifying",
            "turn": 1,
        }
    )
    return coord


@pytest.fixture
def test_session() -> SessionState:
    return SessionState(project_id="proj-001")


# ── Full inquiry flow (NLU → coordinator → render) ──────────────────────


@pytest.mark.asyncio
async def test_full_inquiry_flow(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    """test_mode=False exercises the real NLU → coordinator path."""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input(
            "I want to explore free will",
            test_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )
    assert result is not None
    assert "dialogue_state" in result
    # NLU was invoked (real LLM call)
    mock_llm.generate.assert_called_once()
    mock_coordinator.run.assert_called_once()


@pytest.mark.asyncio
async def test_clarification_dialogue(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    """Clarification intent routed through NLU to coordinator."""
    from aicophilosopher.presentation.repl import _process_input

    mock_llm.generate = AsyncMock(return_value=GenerationResult(text=_nlu_json("clarify_question")))
    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input(
            "From an ontological angle",
            test_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )
    assert result is not None
    # Coordinator receives intent-derived command
    mock_coordinator.run.assert_called_once()


@pytest.mark.asyncio
async def test_empty_input_no_crash(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    result = await _process_input("", test_session, mock_coordinator, mock_llm, test_mode=False)
    assert result is None
    mock_coordinator.run.assert_not_called()


@pytest.mark.asyncio
async def test_exit_command_finalizes_session(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    from aicophilosopher.presentation.repl import _process_input

    result = await _process_input(
        "/exit", test_session, mock_coordinator, mock_llm, test_mode=False
    )
    assert test_session.status == SessionStatus.PAUSED
    assert result is not None


@pytest.mark.asyncio
async def test_five_turn_conversation(mock_llm: MagicMock, mock_coordinator: MagicMock) -> None:
    from aicophilosopher.presentation.repl import _process_input

    session = SessionState(project_id="proj-001")
    turns = [
        "I want to explore free will",
        "From an ontological angle",
        "Focus on compatibilism",
        "How are things going?",
        "/exit",
    ]
    with patch("aicophilosopher.presentation.repl.render_response"):
        for _, turn in enumerate(turns):
            await _process_input(turn, session, mock_coordinator, mock_llm, test_mode=False)

    assert session.status == SessionStatus.PAUSED
    # 4 NL text turns called coordinator, /exit does not
    assert mock_coordinator.run.call_count == 4
