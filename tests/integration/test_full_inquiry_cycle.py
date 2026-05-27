"""Integration tests for full inquiry cycle — US4 (T-028)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aicophilosopher.domain.entities.session import SessionState
from aicophilosopher.ports.llm_port import GenerationResult


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.generate = AsyncMock(
        return_value=GenerationResult(
            text=json.dumps(
                {
                    "intent_type": "start_inquiry",
                    "confidence": 0.95,
                    "extracted_entities": {},
                    "alternative_intents": [],
                    "needs_clarification": False,
                }
            )
        )
    )
    return llm


@pytest.fixture
def mock_coordinator() -> MagicMock:
    coord = MagicMock()
    coord.run = AsyncMock(
        return_value={
            "message": "Goal refined.",
            "dialogue_state": "goal_proposed",
            "turn": 1,
        }
    )
    return coord


@pytest.fixture
def test_session() -> SessionState:
    return SessionState(project_id="proj-001")


# ── Coordinator dispatch via NLU + _process_input ────────────────────


@pytest.mark.asyncio
async def test_start_inquiry_dispatches_to_coordinator(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    """NLU classifies as start_inquiry → coordinator.run called with command=intent."""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input(
            "explore free will",
            test_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )
    assert result is not None
    mock_coordinator.run.assert_called_once()


@pytest.mark.asyncio
async def test_steer_dispatches_to_coordinator(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    """Steering intent routed through full NLU → coordinator pipeline."""
    from aicophilosopher.presentation.repl import _process_input

    mock_llm.generate = AsyncMock(
        return_value=GenerationResult(
            text=json.dumps(
                {
                    "intent_type": "steer_workstream",
                    "confidence": 0.92,
                    "extracted_entities": {"workstream_id": "ws-001"},
                    "alternative_intents": [],
                    "needs_clarification": False,
                }
            )
        )
    )
    with patch("aicophilosopher.presentation.repl.render_response"):
        result = await _process_input(
            "focus on compatibilism",
            test_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )
    assert result is not None
    mock_coordinator.run.assert_called_once()


@pytest.mark.asyncio
async def test_slash_exit_via_full_cycle(
    mock_llm: MagicMock, mock_coordinator: MagicMock, test_session: SessionState
) -> None:
    """Slash command exits without NLU call."""
    from aicophilosopher.presentation.repl import _process_input

    result = await _process_input(
        "/exit", test_session, mock_coordinator, mock_llm, test_mode=False
    )
    assert result is not None
    assert result.get("action") == "exit"
    mock_llm.generate.assert_not_called()
