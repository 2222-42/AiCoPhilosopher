"""Unit tests for Console Agent session domain entities (T-004)."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from aicophilosopher.domain.entities.session import (
    ActionTaken,
    ActionType,
    AlternativeIntent,
    ApprovalOption,
    ApprovalRequest,
    ApprovalRequestType,
    ContextBlock,
    DialogueTurn,
    EpistemicSnapshot,
    FocusContext,
    IntentType,
    PendingDecision,
    SessionState,
    SessionStatus,
    SpeakerType,
    ToggleState,
    Urgency,
    UserIntent,
)

# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def sample_intent() -> UserIntent:
    return UserIntent(
        intent_type=IntentType.START_INQUIRY,
        confidence=0.92,
        extracted_entities={"topic": "free will"},
        raw_input="I want to explore free will",
    )


@pytest.fixture
def sample_turn(sample_intent: UserIntent) -> DialogueTurn:
    return DialogueTurn(speaker=SpeakerType.USER, content="test", intent=sample_intent)


@pytest.fixture
def sample_session() -> SessionState:
    return SessionState(project_id="proj-001")


# ── SessionStatus ────────────────────────────────────────────────────────


class TestSessionStatus:
    def test_values(self) -> None:
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.PAUSED == "paused"
        assert SessionStatus.CLOSED == "closed"

    def test_str_enum(self) -> None:
        assert str(SessionStatus.ACTIVE) == "active"
        assert isinstance(SessionStatus.ACTIVE, str)


# ── SpeakerType ──────────────────────────────────────────────────────────


class TestSpeakerType:
    def test_three_values(self) -> None:
        assert len(SpeakerType) == 3

    def test_values(self) -> None:
        assert SpeakerType.USER == "user"
        assert SpeakerType.COORDINATOR == "coordinator"
        assert SpeakerType.SYSTEM == "system"


# ── IntentType ───────────────────────────────────────────────────────────


class TestIntentType:
    def test_sixteen_values(self) -> None:
        assert len(IntentType) == 16

    def test_key_values(self) -> None:
        assert IntentType.START_INQUIRY == "start_inquiry"
        assert IntentType.STEER_WORKSTREAM == "steer_workstream"
        assert IntentType.PAUSE_SESSION == "pause_session"
        assert IntentType.COMPARE_TRADITIONS == "compare_traditions"


# ── ApprovalRequestType ──────────────────────────────────────────────────


class TestApprovalRequestType:
    def test_seven_values(self) -> None:
        assert len(ApprovalRequestType) == 7

    def test_key_values(self) -> None:
        assert ApprovalRequestType.WORKSTREAM_PROPOSAL == "workstream_proposal"
        assert ApprovalRequestType.EXTERNAL_SEARCH_CONSENT == "external_search_consent"
        assert ApprovalRequestType.GOAL_REFINEMENT == "goal_refinement"


# ── UserIntent ───────────────────────────────────────────────────────────


class TestUserIntent:
    def test_basic(self) -> None:
        ui = UserIntent(intent_type=IntentType.START_INQUIRY, confidence=0.9, raw_input="hi")
        assert ui.intent_type == IntentType.START_INQUIRY
        assert ui.confidence == 0.9
        assert ui.needs_clarification is False

    def test_confidence_bounds(self) -> None:
        with pytest.raises(ValidationError):
            UserIntent(intent_type=IntentType.START_INQUIRY, confidence=-0.1, raw_input="x")
        with pytest.raises(ValidationError):
            UserIntent(intent_type=IntentType.START_INQUIRY, confidence=1.1, raw_input="x")

    def test_alternative_intents_max_three(self) -> None:
        alt = AlternativeIntent(
            intent_type=IntentType.CLARIFY_QUESTION, confidence=0.5, rationale="maybe"
        )
        with pytest.raises(ValidationError):
            UserIntent(
                intent_type=IntentType.START_INQUIRY,
                confidence=0.9,
                raw_input="test",
                alternative_intents=[alt, alt, alt, alt],
            )

    def test_alternative_intents_three_ok(self) -> None:
        alt = AlternativeIntent(
            intent_type=IntentType.CLARIFY_QUESTION, confidence=0.5, rationale="maybe"
        )
        ui = UserIntent(
            intent_type=IntentType.START_INQUIRY,
            confidence=0.9,
            raw_input="test",
            alternative_intents=[alt, alt, alt],
        )
        assert len(ui.alternative_intents) == 3

    def test_extracted_entities(self, sample_intent: UserIntent) -> None:
        assert sample_intent.extracted_entities["topic"] == "free will"

    def test_raw_input_preserved(self) -> None:
        ui = UserIntent(
            intent_type=IntentType.ASK_QUESTION, confidence=0.95, raw_input="what is this?"
        )
        assert ui.raw_input == "what is this?"


# ── DialogueTurn ─────────────────────────────────────────────────────────


class TestDialogueTurn:
    def test_user_turn_with_intent(self, sample_turn: DialogueTurn) -> None:
        assert sample_turn.speaker == SpeakerType.USER
        assert sample_turn.intent is not None

    def test_coordinator_turn_with_actions(self) -> None:
        action = ActionTaken(action_type=ActionType.LAUNCHED_WORKSTREAM, description="test")
        turn = DialogueTurn(
            speaker=SpeakerType.COORDINATOR, content="launched", actions_taken=[action]
        )
        assert len(turn.actions_taken) == 1
        assert turn.intent is None

    def test_system_turn(self) -> None:
        turn = DialogueTurn(speaker=SpeakerType.SYSTEM, content="Workstream completed")
        assert turn.speaker == SpeakerType.SYSTEM

    def test_content_min_length(self) -> None:
        with pytest.raises(ValidationError):
            DialogueTurn(speaker=SpeakerType.USER, content="")

    def test_turn_id_generated(self) -> None:
        turn = DialogueTurn(speaker=SpeakerType.USER, content="x")
        assert isinstance(turn.turn_id, UUID)

    def test_timestamp_utc(self) -> None:
        turn = DialogueTurn(speaker=SpeakerType.USER, content="x")
        assert turn.timestamp.tzinfo == UTC

    def test_context_id_optional(self) -> None:
        turn = DialogueTurn(speaker=SpeakerType.USER, content="x")
        assert turn.context_id is None


# ── ContextBlock ─────────────────────────────────────────────────────────


class TestContextBlock:
    def test_basic(self) -> None:
        cb = ContextBlock(label="Compatibilism review")
        assert cb.label == "Compatibilism review"
        assert cb.summary == ""

    def test_label_max_length(self) -> None:
        with pytest.raises(ValidationError):
            ContextBlock(label="x" * 201)

    def test_no_turns_property(self) -> None:
        """ContextBlock no longer has a turns property; use SessionState.get_turns_for_context."""
        cb = ContextBlock(label="test")
        with pytest.raises(AttributeError):
            _ = cb.turns

    def test_parent_context_optional(self) -> None:
        cb = ContextBlock(label="test")
        assert cb.parent_context is None

    def test_epistemic_snapshot(self) -> None:
        cb = ContextBlock(label="test")
        assert isinstance(cb.epistemic_state, EpistemicSnapshot)
        assert cb.epistemic_state.active_claims == []


# ── EpistemicSnapshot ────────────────────────────────────────────────────


class TestEpistemicSnapshot:
    def test_defaults(self) -> None:
        es = EpistemicSnapshot()
        assert es.active_claims == []
        assert es.hypotheses_discussed == []
        assert es.key_conclusions == []

    def test_with_data(self) -> None:
        es = EpistemicSnapshot(
            active_claims=["c1", "c2"],
            hypotheses_discussed=["h1"],
            key_conclusions=["Software abstraction is ontologically distinct"],
        )
        assert len(es.active_claims) == 2
        assert len(es.key_conclusions) == 1


# ── FocusContext ─────────────────────────────────────────────────────────


class TestFocusContext:
    def test_defaults(self) -> None:
        fc = FocusContext()
        assert fc.active_topic == ""
        assert fc.last_workstream_id is None
        assert fc.last_hypothesis_id is None
        assert fc.pending_decisions == []
        assert fc.recent_claim_ids == []
        assert isinstance(fc.toggle_state, ToggleState)

    def test_toggle_state_default(self) -> None:
        fc = FocusContext()
        assert fc.toggle_state.show_details is False
        assert fc.toggle_state.show_suggestions is False

    def test_updated_at_utc(self) -> None:
        fc = FocusContext()
        assert fc.updated_at.tzinfo == UTC


# ── ToggleState ──────────────────────────────────────────────────────────


class TestToggleState:
    def test_defaults(self) -> None:
        ts = ToggleState()
        assert ts.show_details is False
        assert ts.show_suggestions is False

    def test_explicit(self) -> None:
        ts = ToggleState(show_details=True, show_suggestions=True)
        assert ts.show_details is True
        assert ts.show_suggestions is True


# ── PendingDecision ──────────────────────────────────────────────────────


class TestPendingDecision:
    def test_basic(self) -> None:
        pd = PendingDecision(
            decision_type=ApprovalRequestType.WORKSTREAM_PROPOSAL,
            description="Propose literature search workstream",
        )
        assert pd.decision_type == ApprovalRequestType.WORKSTREAM_PROPOSAL
        assert isinstance(pd.decision_id, UUID)


# ── ApprovalRequest ──────────────────────────────────────────────────────


class TestApprovalRequest:
    def test_basic(self) -> None:
        ar = ApprovalRequest(
            request_type=ApprovalRequestType.WORKSTREAM_PROPOSAL,
            description="Propose literature search on compatibilism",
            options=[ApprovalOption(index=0, label="Accept")],
        )
        assert ar.urgency == Urgency.NON_BLOCKING
        assert ar.resolved_at is None

    def test_description_min_length(self) -> None:
        with pytest.raises(ValidationError):
            ApprovalRequest(
                request_type=ApprovalRequestType.WORKSTREAM_PROPOSAL,
                description="short",
                options=[ApprovalOption(index=0, label="Accept")],
            )

    def test_options_min_one(self) -> None:
        with pytest.raises(ValidationError):
            ApprovalRequest(
                request_type=ApprovalRequestType.WORKSTREAM_PROPOSAL,
                description="test description long enough",
                options=[],
            )

    def test_options_max_five(self) -> None:
        opts = [ApprovalOption(index=i, label=f"Option {i}") for i in range(6)]
        with pytest.raises(ValidationError):
            ApprovalRequest(
                request_type=ApprovalRequestType.WORKSTREAM_PROPOSAL,
                description="test description long enough",
                options=opts,
            )

    def test_options_five_ok(self) -> None:
        opts = [ApprovalOption(index=i, label=f"Option {i}") for i in range(5)]
        ar = ApprovalRequest(
            request_type=ApprovalRequestType.WORKSTREAM_PROPOSAL,
            description="test description long enough",
            options=opts,
        )
        assert len(ar.options) == 5

    def test_resolution_with_choice(self) -> None:
        ar = ApprovalRequest(
            request_type=ApprovalRequestType.NORMATIVE_JUDGMENT,
            description="Choose an ethical framework",
            options=[
                ApprovalOption(index=0, label="Deontology"),
                ApprovalOption(index=1, label="Consequentialism"),
            ],
            resolved_at=datetime.now(UTC),
            user_choice=0,
        )
        assert ar.user_choice == 0


# ── ApprovalOption ───────────────────────────────────────────────────────


class TestApprovalOption:
    def test_basic(self) -> None:
        opt = ApprovalOption(index=0, label="Accept")
        assert opt.index == 0
        assert opt.label == "Accept"

    def test_label_max_length(self) -> None:
        with pytest.raises(ValidationError):
            ApprovalOption(index=0, label="x" * 201)


# ── ActionTaken ──────────────────────────────────────────────────────────


class TestActionTaken:
    def test_basic(self) -> None:
        at = ActionTaken(action_type=ActionType.LAUNCHED_WORKSTREAM, description="Started WS-001")
        assert at.action_type == ActionType.LAUNCHED_WORKSTREAM

    def test_optional_target(self) -> None:
        at = ActionTaken(
            action_type=ActionType.STEERED_WORKSTREAM, description="Steered", target_id="ws-001"
        )
        assert at.target_id == "ws-001"

    def test_timestamp_utc(self) -> None:
        at = ActionTaken(action_type=ActionType.CREATED_PROJECT, description="test")
        assert at.timestamp.tzinfo == UTC


# ── SessionState ─────────────────────────────────────────────────────────


class TestSessionState:
    def test_basic(self, sample_session: SessionState) -> None:
        assert sample_session.project_id == "proj-001"
        assert sample_session.status == SessionStatus.ACTIVE
        assert sample_session.pid > 0
        assert isinstance(sample_session.session_id, UUID)

    def test_default_focus_context(self, sample_session: SessionState) -> None:
        assert isinstance(sample_session.current_focus, FocusContext)

    def test_dialogue_history_empty(self, sample_session: SessionState) -> None:
        assert sample_session.dialogue_history == []

    def test_heartbeat_utc(self, sample_session: SessionState) -> None:
        assert sample_session.heartbeat_at.tzinfo == UTC

    def test_created_at_utc(self, sample_session: SessionState) -> None:
        assert sample_session.created_at.tzinfo == UTC

    def test_last_active_at_utc(self, sample_session: SessionState) -> None:
        assert sample_session.last_active_at.tzinfo == UTC

    def test_timestamps_chronological(self, sample_session: SessionState) -> None:
        assert sample_session.created_at <= sample_session.last_active_at

    def test_exit_reason_optional(self, sample_session: SessionState) -> None:
        assert sample_session.exit_reason is None

    def test_status_transition(self, sample_session: SessionState) -> None:
        assert sample_session.status == SessionStatus.ACTIVE
        sample_session.status = SessionStatus.PAUSED
        assert sample_session.status == SessionStatus.PAUSED
        sample_session.status = SessionStatus.ACTIVE
        assert sample_session.status == SessionStatus.ACTIVE
        sample_session.status = SessionStatus.CLOSED
        assert sample_session.status == SessionStatus.CLOSED

    def test_config_snapshot_default(self, sample_session: SessionState) -> None:
        assert sample_session.config_snapshot == {}

    def test_config_snapshot_with_data(self) -> None:
        s = SessionState(project_id="p1", config_snapshot={"nlu.confidence_threshold": 0.85})
        assert s.config_snapshot["nlu.confidence_threshold"] == 0.85

    def test_active_workstreams_default(self, sample_session: SessionState) -> None:
        assert sample_session.active_workstreams == []

    def test_model_copy_works(self, sample_session: SessionState) -> None:
        copy = sample_session.model_copy()
        copy.status = SessionStatus.PAUSED
        assert sample_session.status == SessionStatus.ACTIVE
        assert copy.status == SessionStatus.PAUSED

    def test_model_copy_deep_nested(self, sample_session: SessionState) -> None:
        sample_session.active_workstreams.append("ws-001")
        copy = sample_session.model_copy(deep=True)
        copy.active_workstreams.append("ws-002")
        assert len(sample_session.active_workstreams) == 1
        assert len(copy.active_workstreams) == 2

    def test_get_turns_for_context(self) -> None:
        """SessionState.get_turns_for_context filters dialogue_history by context_id."""
        ctx_id = UUID("00000000-0000-0000-0000-000000000001")
        t1 = DialogueTurn(speaker=SpeakerType.USER, content="in ctx", context_id=ctx_id)
        t2 = DialogueTurn(speaker=SpeakerType.USER, content="not in ctx")
        s = SessionState(project_id="p1", dialogue_history=[t1, t2])
        result = s.get_turns_for_context(ctx_id)
        assert len(result) == 1
        assert result[0].content == "in ctx"

    def test_get_turns_for_context_empty(self) -> None:
        """Returns empty list when no turns match context_id."""
        s = SessionState(project_id="p1")
        result = s.get_turns_for_context(UUID("00000000-0000-0000-0000-000000000099"))
        assert result == []
