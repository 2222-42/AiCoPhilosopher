"""Unit tests for NLU intent classifier (T-008)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from aicophilosopher.domain.entities.session import FocusContext, IntentType
from aicophilosopher.ports.llm_port import GenerationResult


def _llm(intent_type: str, confidence: float) -> GenerationResult:
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


def _llm_alt(intent_type: str, confidence: float, alternatives: list[dict]) -> GenerationResult:
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


# ── All 16 intent types ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_inquiry(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("start_inquiry", 0.95))
    r = await classify_intent("explore free will", focus, mock_llm)
    assert r.intent_type == IntentType.START_INQUIRY


@pytest.mark.asyncio
async def test_clarify_question(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("clarify_question", 0.90))
    r = await classify_intent("from an ontological angle", focus, mock_llm)
    assert r.intent_type == IntentType.CLARIFY_QUESTION


@pytest.mark.asyncio
async def test_propose_workstream(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("propose_workstream", 0.88))
    r = await classify_intent("yes go ahead", focus, mock_llm)
    assert r.intent_type == IntentType.PROPOSE_WORKSTREAM


@pytest.mark.asyncio
async def test_steer_workstream(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("steer_workstream", 0.92))
    r = await classify_intent("focus on post-1980", focus, mock_llm)
    assert r.intent_type == IntentType.STEER_WORKSTREAM


@pytest.mark.asyncio
async def test_request_status(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("request_status", 0.88))
    r = await classify_intent("how are things?", focus, mock_llm)
    assert r.intent_type == IntentType.REQUEST_STATUS


@pytest.mark.asyncio
async def test_request_detail(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("request_detail", 0.91))
    r = await classify_intent("tell me more about that", focus, mock_llm)
    assert r.intent_type == IntentType.REQUEST_DETAIL


@pytest.mark.asyncio
async def test_request_export(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("request_export", 0.97))
    r = await classify_intent("export as markdown", focus, mock_llm)
    assert r.intent_type == IntentType.REQUEST_EXPORT


@pytest.mark.asyncio
async def test_approve_action(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("approve_action", 0.94))
    r = await classify_intent("yes launch it", focus, mock_llm)
    assert r.intent_type == IntentType.APPROVE_ACTION


@pytest.mark.asyncio
async def test_reject_action(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("reject_action", 0.91))
    r = await classify_intent("no let's not", focus, mock_llm)
    assert r.intent_type == IntentType.REJECT_ACTION


@pytest.mark.asyncio
async def test_ask_question(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("ask_question", 0.93))
    r = await classify_intent("what is a workstream?", focus, mock_llm)
    assert r.intent_type == IntentType.ASK_QUESTION


@pytest.mark.asyncio
async def test_inject_information(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("inject_information", 0.89))
    r = await classify_intent("uploading a paper", focus, mock_llm)
    assert r.intent_type == IntentType.INJECT_INFORMATION


@pytest.mark.asyncio
async def test_request_help(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("request_help", 0.87))
    r = await classify_intent("i'm stuck", focus, mock_llm)
    assert r.intent_type == IntentType.REQUEST_HELP


@pytest.mark.asyncio
async def test_pause_session(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("pause_session", 0.96))
    r = await classify_intent("let's take a break", focus, mock_llm)
    assert r.intent_type == IntentType.PAUSE_SESSION


@pytest.mark.asyncio
async def test_resume_session(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("resume_session", 0.94))
    r = await classify_intent("i'm back let's continue", focus, mock_llm)
    assert r.intent_type == IntentType.RESUME_SESSION


@pytest.mark.asyncio
async def test_archive_project(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("archive_project", 0.95))
    r = await classify_intent("archive this project", focus, mock_llm)
    assert r.intent_type == IntentType.ARCHIVE_PROJECT


@pytest.mark.asyncio
async def test_compare_traditions(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("compare_traditions", 0.93))
    r = await classify_intent("how would a phenomenologist approach this?", focus, mock_llm)
    assert r.intent_type == IntentType.COMPARE_TRADITIONS


# ── Slash bypass ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_slash_input_not_passed_to_nlu() -> None:
    """NLU should never receive /-prefixed input (handled by slash dispatcher)."""
    # This is enforced by the REPL loop, not NLU. We verify NLU handles it gracefully.
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value=_llm("start_inquiry", 0.2))
    r = await classify_intent("/exit", FocusContext(), mock_llm)
    # Low confidence → needs clarification (does not silently treat as command)
    assert r.needs_clarification is True


# ── Confidence threshold ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_low_confidence_clarification(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("start_inquiry", 0.60))
    r = await classify_intent("vague", focus, mock_llm)
    assert r.needs_clarification is True


@pytest.mark.asyncio
async def test_high_confidence_no_clarification(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("start_inquiry", 0.95))
    r = await classify_intent("explore free will", focus, mock_llm)
    assert r.needs_clarification is False


# ── Raw input ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_raw_input_preserved(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("start_inquiry", 0.92))
    r = await classify_intent("explore free will", focus, mock_llm)
    assert r.raw_input == "explore free will"


# ── Alternatives sorted ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_alternatives_sorted_by_confidence(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(
        return_value=_llm_alt(
            "start_inquiry", 0.80,
            [
                {"intent_type": "clarify_question", "confidence": 0.50, "rationale": "low"},
                {"intent_type": "steer_workstream", "confidence": 0.90, "rationale": "high"},
                {"intent_type": "request_status", "confidence": 0.70, "rationale": "mid"},
            ],
        )
    )
    r = await classify_intent("test", focus, mock_llm)
    assert len(r.alternative_intents) == 3
    assert r.alternative_intents[0].confidence == 0.90
    assert r.alternative_intents[-1].confidence == 0.50


# ── Japanese ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_japanese(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=_llm("start_inquiry", 0.91))
    r = await classify_intent("自由意志について調べたい", focus, mock_llm)
    assert r.intent_type == IntentType.START_INQUIRY


# ── Malformed JSON ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_malformed_json(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(return_value=GenerationResult(text="not json"))
    r = await classify_intent("hello", focus, mock_llm)
    assert r.needs_clarification is True


# ── Empty input ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_empty_input(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    r = await classify_intent("", focus, mock_llm)
    assert r.needs_clarification is True
    mock_llm.generate.assert_not_called()


# ── Configurable threshold ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_configurable_threshold(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    # confidence=0.82 > default 0.85 → needs_clarification=True
    mock_llm.generate = AsyncMock(return_value=_llm("start_inquiry", 0.82))
    r = await classify_intent("test", focus, mock_llm)
    assert r.needs_clarification is True
    # confidence=0.82 >= threshold=0.80, LLM's needs_clarification=False
    mock_llm.generate = AsyncMock(
        return_value=GenerationResult(text=json.dumps({
            "intent_type": "start_inquiry", "confidence": 0.82,
            "extracted_entities": {}, "alternative_intents": [],
            "needs_clarification": False,
        }))
    )
    r = await classify_intent("test", focus, mock_llm, confidence_threshold=0.80)
    assert r.needs_clarification is False


# ── float() safety ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_non_numeric_confidence_handled(mock_llm: MagicMock, focus: FocusContext) -> None:
    from aicophilosopher.presentation.nlu import classify_intent
    mock_llm.generate = AsyncMock(
        return_value=GenerationResult(
            text=json.dumps(
                {"intent_type": "start_inquiry", "confidence": "high",
                 "extracted_entities": {}, "alternative_intents": [], "needs_clarification": False}
            )
        )
    )
    r = await classify_intent("test", focus, mock_llm)
    assert r.needs_clarification is True
    assert r.confidence == 0.0


# ── Fallback (contract: intent in alternative_intents[0]) ───────────────


def test_fallback_uses_alternative_intents() -> None:
    from aicophilosopher.presentation.nlu import fallback_classify
    r = fallback_classify("yes go ahead")
    assert r.intent_type == IntentType.START_INQUIRY  # generic fallback
    assert len(r.alternative_intents) == 1
    assert r.alternative_intents[0].intent_type == IntentType.APPROVE_ACTION
    assert r.confidence == 0.80
    assert r.needs_clarification is True


def test_fallback_no_match() -> None:
    from aicophilosopher.presentation.nlu import fallback_classify
    r = fallback_classify("xyzzy")
    assert r.intent_type == IntentType.START_INQUIRY
    assert r.alternative_intents == []


# ── Entity extraction ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_entities_preserved(mock_llm: MagicMock, focus: FocusContext) -> None:
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
    r = await classify_intent("explore free will analytically", focus, mock_llm)
    assert r.extracted_entities["topic"] == "free will"
