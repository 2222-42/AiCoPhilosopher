"""Unit tests for REPL-to-Coordinator integration (T-024).

Tests the _process_input routing: intent types → coordinator.run(...) calls.
Mocks classify_intent to control which intent is tested; verifies the
coordinator is called with the correct command and payload per intent type.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aicophilosopher.domain.entities.session import (
    IntentType,
    SessionState,
    UserIntent,
)


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
            "summary": "Let me think about that.",
            "dialogue_state": "awaiting_question",
            "turn": 1,
        }
    )
    return coord


def _intent(intent_type: IntentType, confidence: float = 0.95) -> UserIntent:
    """Factory for a high-confidence UserIntent."""
    return UserIntent(
        intent_type=intent_type,
        confidence=confidence,
        raw_input="test input",
        needs_clarification=False,
    )


# ── Intent → Command routing ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_inquiry_routes_to_start(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """start_inquiry intent → coordinator.run(command='start_inquiry', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.START_INQUIRY)

        await _process_input(
            "explore free will",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    mock_nlu.assert_called_once()
    call_args = mock_coordinator.run.call_args
    assert call_args.kwargs.get("command") == "start_inquiry"
    assert call_args.kwargs.get("user_input") == "explore free will"


@pytest.mark.asyncio
async def test_clarify_question_routes_to_refine_goal(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """clarify_question intent → coordinator.run(command='clarify_question', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.CLARIFY_QUESTION)

        await _process_input(
            "I mean in the analytic tradition",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "clarify_question"


@pytest.mark.asyncio
async def test_propose_workstream_routes_to_propose_workstream(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """propose_workstream intent → coordinator.run(command='propose_workstream', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.PROPOSE_WORKSTREAM)

        await _process_input(
            "let's search for papers on compatibilism",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "propose_workstream"


@pytest.mark.asyncio
async def test_steer_workstream_routes_to_steer(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """steer_workstream intent → coordinator.run(command='steer_workstream', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.STEER_WORKSTREAM)

        await _process_input(
            "focus on post-1980 sources",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "steer_workstream"


@pytest.mark.asyncio
async def test_request_status_routes_to_status(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """request_status intent → coordinator.run(command='request_status', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.REQUEST_STATUS)

        await _process_input(
            "how is the search going",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "request_status"


@pytest.mark.asyncio
async def test_request_detail_routes_to_request_detail(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """request_detail intent → coordinator.run(command='request_detail', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.REQUEST_DETAIL)

        await _process_input(
            "tell me more about compatibilism",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "request_detail"


@pytest.mark.asyncio
async def test_request_export_routes_to_request_export(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """request_export intent → coordinator.run(command='request_export', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.REQUEST_EXPORT)

        await _process_input(
            "export this as markdown",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "request_export"


@pytest.mark.asyncio
async def test_approve_action_routes_to_approve_action(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """approve_action intent → coordinator.run(command='approve_action', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.APPROVE_ACTION)

        await _process_input(
            "yes, go ahead",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "approve_action"


@pytest.mark.asyncio
async def test_reject_action_routes_to_reject_action(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """reject_action intent → coordinator.run(command='reject_action', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.REJECT_ACTION)

        await _process_input(
            "no, stop that",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "reject_action"


@pytest.mark.asyncio
async def test_ask_question_routes_to_ask_question(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """ask_question intent → coordinator.run(command='ask_question', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.ASK_QUESTION)

        await _process_input(
            "what do you think about determinism",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "ask_question"


@pytest.mark.asyncio
async def test_inject_information_routes_to_inject_information(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """inject_information intent → coordinator.run(command='inject_information', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.INJECT_INFORMATION)

        await _process_input(
            "I uploaded a PDF for analysis",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "inject_information"


@pytest.mark.asyncio
async def test_request_help_routes_to_request_help(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """request_help intent → coordinator.run(command='request_help', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.REQUEST_HELP)

        await _process_input(
            "I'm stuck, can you help",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "request_help"


@pytest.mark.asyncio
async def test_pause_session_routes_to_pause_session(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """pause_session intent → coordinator.run(command='pause_session', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.PAUSE_SESSION)

        await _process_input(
            "let's take a break",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "pause_session"


@pytest.mark.asyncio
async def test_resume_session_routes_to_resume_session(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """resume_session intent → coordinator.run(command='resume_session', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.RESUME_SESSION)

        await _process_input(
            "let's continue",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "resume_session"


@pytest.mark.asyncio
async def test_archive_project_routes_to_archive_project(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """archive_project intent → coordinator.run(command='archive_project', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.ARCHIVE_PROJECT)

        await _process_input(
            "archive this project",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "archive_project"


@pytest.mark.asyncio
async def test_compare_traditions_routes_to_compare_traditions(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """compare_traditions intent → coordinator.run(command='compare_traditions', ...)"""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.COMPARE_TRADITIONS)

        await _process_input(
            "compare analytic and continental views on free will",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    call_kw = mock_coordinator.run.call_args.kwargs
    assert call_kw.get("command") == "compare_traditions"


# ── Dialogue state routing ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dialogue_state_passed_to_rendering(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Coordinator response dict (including dialogue_state) is passed to render_response."""
    from aicophilosopher.presentation.repl import _process_input

    mock_coordinator.run.return_value = {
        "summary": "I've refined your question.",
        "dialogue_state": "goal_proposed",
        "workstream_proposals": [{"type": "literature_search", "description": "..."}],
    }

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.CLARIFY_QUESTION)
        with patch("aicophilosopher.presentation.repl.render_response") as mock_render:
            await _process_input(
                "refine my question about free will",
                mock_session,
                mock_coordinator,
                mock_llm,
                test_mode=False,
            )

    mock_render.assert_called_once()
    rendered_response = mock_render.call_args.args[0]
    assert rendered_response["dialogue_state"] == "goal_proposed"


@pytest.mark.asyncio
async def test_approval_request_surfaced_in_summary(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """When coordinator returns is_approval_request, render_response receives it."""
    from aicophilosopher.presentation.repl import _process_input

    mock_coordinator.run.return_value = {
        "summary": "I propose launching a literature search.",
        "dialogue_state": "goal_proposed",
        "is_approval_request": True,
        "approval_options": ["Yes, start search", "No, refine further"],
    }

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.PROPOSE_WORKSTREAM)
        with patch("aicophilosopher.presentation.repl.render_response") as mock_render:
            await _process_input(
                "let's search for compatibilism papers",
                mock_session,
                mock_coordinator,
                mock_llm,
                test_mode=False,
            )

    rendered = mock_render.call_args.args[0]
    assert rendered.get("is_approval_request") is True
    assert len(rendered.get("approval_options", [])) == 2


@pytest.mark.asyncio
async def test_coordinator_response_preserves_all_fields(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """All fields from coordinator dict pass through to render_response unchanged."""
    from aicophilosopher.presentation.repl import _process_input

    expected = {
        "summary": "Analysis complete.",
        "epistemic_status": "Active hypotheses: 3 | Refuted: 1",
        "active_workstreams": ["lit-search-001 — running"],
        "details": "Deep analysis of Frankfurt cases...",
        "suggestions": "Try comparing with Strawson's reactive attitudes.",
        "dialogue_state": "clarifying",
        "turn": 7,
        "needs_clarification": True,
    }
    mock_coordinator.run.return_value = expected

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.START_INQUIRY)
        with patch("aicophilosopher.presentation.repl.render_response") as mock_render:
            await _process_input(
                "tell me about free will",
                mock_session,
                mock_coordinator,
                mock_llm,
                test_mode=False,
            )

    rendered = mock_render.call_args.args[0]
    for key, value in expected.items():
        assert rendered.get(key) == value, f"Field '{key}' not preserved"


# ── User input passthrough ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_input_passed_to_coordinator(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Original user_input is passed as user_input kwarg to coordinator.run."""
    from aicophilosopher.presentation.repl import _process_input

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = _intent(IntentType.START_INQUIRY)

        await _process_input(
            "What is the meaning of qualia?",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    assert mock_coordinator.run.call_args.kwargs["user_input"] == "What is the meaning of qualia?"


@pytest.mark.asyncio
async def test_low_confidence_intent_still_routes(
    mock_session: SessionState,
    mock_llm: MagicMock,
    mock_coordinator: MagicMock,
) -> None:
    """Even low-confidence intents route to coordinator (needs_clarification is in UserIntent)."""
    from aicophilosopher.presentation.repl import _process_input

    low_conf = UserIntent(
        intent_type=IntentType.START_INQUIRY,
        confidence=0.45,
        raw_input="hmm",
        needs_clarification=True,
    )

    with patch("aicophilosopher.presentation.repl.classify_intent") as mock_nlu:
        mock_nlu.return_value = low_conf

        await _process_input(
            "hmm",
            mock_session,
            mock_coordinator,
            mock_llm,
            test_mode=False,
        )

    # Coordinator IS called even with low confidence; needs_clarification
    # is handled downstream by the coordinator response rendering.
    mock_coordinator.run.assert_called_once()
