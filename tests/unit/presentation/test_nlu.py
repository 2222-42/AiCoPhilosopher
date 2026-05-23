"""Unit tests for NLU intent classifier (T-008)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from aicophilosopher.domain.entities.session import (
    FocusContext,
    IntentType,
    UserIntent,
)
from aicophilosopher.ports.llm_port import GenerationResult

# ── Fixtures ─────────────────────────────────────────────────────────────


def _make_llm_response(intent_type: str, confidence: float) -> GenerationResult:
    return GenerationResult(
        text=json.dumps(
            {
                "intent_type": intent_type,
                "confidence": confidence,
                "extracted_entities": {"topic": "free will"},
                "alternative_intents": [],
                "needs_clarification": confidence < 0.85,
            }
        )
    )


def _make_llm_response_with_alternatives(
    intent_type: str, confidence: float, alternatives: list[dict]
) -> GenerationResult:
    return GenerationResult(
        text=json.dumps(
            {
                "intent_type": intent_type,
                "confidence": confidence,
                "extracted_entities": {},
                "alternative_intents": alternatives,
                "needs_clarification": confidence < 0.85,
            }
        )
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    return MagicMock()


@pytest.fixture
def focus() -> FocusContext:
    return FocusContext(active_topic="free will")


# ── Intent classification: all 16 types ──────────────────────────────────


@pytest.mark.asyncio
async def test_classify_start_inquiry(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("start_inquiry", 0.95))
    result = await classify_intent("I want to explore free will", focus, mock_llm)
    assert result.intent_type == IntentType.START_INQUIRY
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_classify_clarify_question(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("clarify_question", 0.90))
    result = await classify_intent("From an ontological angle", focus, mock_llm)
    assert result.intent_type == IntentType.CLARIFY_QUESTION


@pytest.mark.asyncio
async def test_classify_steer_workstream(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("steer_workstream", 0.92))
    result = await classify_intent("Focus on post-1980 papers", focus, mock_llm)
    assert result.intent_type == IntentType.STEER_WORKSTREAM


@pytest.mark.asyncio
async def test_classify_request_status(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("request_status", 0.88))
    result = await classify_intent("How are things going?", focus, mock_llm)
    assert result.intent_type == IntentType.REQUEST_STATUS


@pytest.mark.asyncio
async def test_classify_approve_action(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("approve_action", 0.94))
    result = await classify_intent("Yes, launch it", focus, mock_llm)
    assert result.intent_type == IntentType.APPROVE_ACTION


@pytest.mark.asyncio
async def test_classify_reject_action(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("reject_action", 0.91))
    result = await classify_intent("No, let's not", focus, mock_llm)
    assert result.intent_type == IntentType.REJECT_ACTION


@pytest.mark.asyncio
async def test_classify_pause_session(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("pause_session", 0.96))
    result = await classify_intent("Let's take a break", focus, mock_llm)
    assert result.intent_type == IntentType.PAUSE_SESSION


@pytest.mark.asyncio
async def test_classify_compare_traditions(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(
        return_value=_make_llm_response("compare_traditions", 0.93)
    )
    result = await classify_intent(
        "How would a phenomenologist approach this?", focus, mock_llm
    )
    assert result.intent_type == IntentType.COMPARE_TRADITIONS


@pytest.mark.asyncio
async def test_classify_request_export(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("request_export", 0.97))
    result = await classify_intent("Export this as markdown", focus, mock_llm)
    assert result.intent_type == IntentType.REQUEST_EXPORT


@pytest.mark.asyncio
async def test_classify_inject_information(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(
        return_value=_make_llm_response("inject_information", 0.89)
    )
    result = await classify_intent("Uploading Pereboom's 2001 paper", focus, mock_llm)
    assert result.intent_type == IntentType.INJECT_INFORMATION


# ── Confidence threshold ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_low_confidence_triggers_clarification(
    mock_llm: MagicMock, focus: FocusContext
) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("start_inquiry", 0.60))
    result = await classify_intent("something vague", focus, mock_llm)
    assert result.needs_clarification is True


@pytest.mark.asyncio
async def test_high_confidence_no_clarification(
    mock_llm: MagicMock, focus: FocusContext
) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("start_inquiry", 0.95))
    result = await classify_intent("I want to explore free will", focus, mock_llm)
    assert result.needs_clarification is False


# ── Raw input preserved ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_raw_input_preserved(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("start_inquiry", 0.92))
    result = await classify_intent("I want to explore free will", focus, mock_llm)
    assert result.raw_input == "I want to explore free will"


# ── Alternative intents ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_alternative_intents_populated(
    mock_llm: MagicMock, focus: FocusContext
) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(
        return_value=_make_llm_response_with_alternatives(
            "start_inquiry",
            0.80,
            [
                {"intent_type": "clarify_question", "confidence": 0.75, "rationale": "could be"},
                {"intent_type": "steer_workstream", "confidence": 0.60, "rationale": "maybe"},
            ],
        )
    )
    result = await classify_intent("free will maybe steer", focus, mock_llm)
    assert len(result.alternative_intents) == 2
    assert result.alternative_intents[0].intent_type == IntentType.CLARIFY_QUESTION


# ── Japanese input ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_classify_japanese_input(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=_make_llm_response("start_inquiry", 0.91))
    result = await classify_intent("自由意志について調べたい", focus, mock_llm)
    assert result.intent_type == IntentType.START_INQUIRY


# ── Malformed LLM response ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_malformed_json_returns_clarification(
    mock_llm: MagicMock, focus: FocusContext
) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(return_value=GenerationResult(text="not valid json"))
    result = await classify_intent("hello", focus, mock_llm)
    assert result.needs_clarification is True


# ── Missing fields in JSON ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_confidence_field_falls_back(
    mock_llm: MagicMock, focus: FocusContext
) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(
        return_value=GenerationResult(
            text=json.dumps({"intent_type": "start_inquiry", "extracted_entities": {}})
        )
    )
    result = await classify_intent("hi", focus, mock_llm)
    assert result.needs_clarification is True
    assert result.confidence < 0.85


# ── Empty input ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_input_returns_clarification(
    mock_llm: MagicMock, focus: FocusContext
) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    result = await classify_intent("", focus, mock_llm)
    assert result.needs_clarification is True
    mock_llm.generate.assert_not_called()


# ── Rule-based fallback (offline) ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_fallback_detect_start_inquiry(
    mock_llm: MagicMock, focus: FocusContext
) -> None:
    from aicophilosopher.presentation.nlu import fallback_classify

    result = fallback_classify("I want to explore consciousness")
    assert result.intent_type == IntentType.START_INQUIRY
    assert result.confidence == 0.80
    assert result.needs_clarification is True


@pytest.mark.asyncio
async def test_fallback_detect_steer(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import fallback_classify

    result = fallback_classify("focus on compatibilism instead")
    assert result.intent_type == IntentType.STEER_WORKSTREAM


@pytest.mark.asyncio
async def test_fallback_detect_approve(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import fallback_classify

    result = fallback_classify("yes go ahead")
    assert result.intent_type == IntentType.APPROVE_ACTION


@pytest.mark.asyncio
async def test_fallback_detect_reject(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import fallback_classify

    result = fallback_classify("no don't do that")
    assert result.intent_type == IntentType.REJECT_ACTION


@pytest.mark.asyncio
async def test_fallback_detect_request_status(
    mock_llm: MagicMock, focus: FocusContext
) -> None:
    from aicophilosopher.presentation.nlu import fallback_classify

    result = fallback_classify("how is it going?")
    assert result.intent_type == IntentType.REQUEST_STATUS


@pytest.mark.asyncio
async def test_fallback_detect_pause(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import fallback_classify

    result = fallback_classify("let's take a break")
    assert result.intent_type == IntentType.PAUSE_SESSION


@pytest.mark.asyncio
async def test_fallback_detect_export(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import fallback_classify

    result = fallback_classify("export as markdown")
    assert result.intent_type == IntentType.REQUEST_EXPORT


@pytest.mark.asyncio
async def test_fallback_no_match_returns_start_inquiry(
    mock_llm: MagicMock, focus: FocusContext
) -> None:
    from aicophilosopher.presentation.nlu import fallback_classify

    result = fallback_classify("xyzzy blarg")
    assert result.intent_type == IntentType.START_INQUIRY
    assert result.needs_clarification is True


# ── Entity extraction ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extracted_entities_preserved(
    mock_llm: MagicMock, focus: FocusContext
) -> None:
    from aicophilosopher.presentation.nlu import classify_intent

    mock_llm.generate = AsyncMock(
        return_value=GenerationResult(
            text=json.dumps(
                {
                    "intent_type": "start_inquiry",
                    "confidence": 0.92,
                    "extracted_entities": {"topic": "free will", "tradition": "analytic"},
                    "alternative_intents": [],
                    "needs_clarification": False,
                }
            )
        )
    )
    result = await classify_intent("explore free will analytically", focus, mock_llm)
    assert result.extracted_entities["topic"] == "free will"
    assert result.extracted_entities["tradition"] == "analytic"
