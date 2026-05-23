"""Console Agent session domain entities — 002-console-agent.

All entities are pure Pydantic v2 models with zero external dependencies.
Per Clean Architecture: imports ONLY stdlib + pydantic.
"""

import os
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ── Enums ────────────────────────────────────────────────────────────────


class SessionStatus(StrEnum):
    active = "active"
    paused = "paused"
    closed = "closed"


class SpeakerType(StrEnum):
    user = "user"
    coordinator = "coordinator"
    system = "system"


class IntentType(StrEnum):
    start_inquiry = "start_inquiry"
    clarify_question = "clarify_question"
    propose_workstream = "propose_workstream"
    steer_workstream = "steer_workstream"
    request_status = "request_status"
    request_detail = "request_detail"
    request_export = "request_export"
    approve_action = "approve_action"
    reject_action = "reject_action"
    ask_question = "ask_question"
    inject_information = "inject_information"
    request_help = "request_help"
    pause_session = "pause_session"
    resume_session = "resume_session"
    archive_project = "archive_project"
    compare_traditions = "compare_traditions"


class ApprovalRequestType(StrEnum):
    workstream_proposal = "workstream_proposal"
    normative_judgment = "normative_judgment"
    incommensurability_resolution = "incommensurability_resolution"
    review_escalation = "review_escalation"
    external_search_consent = "external_search_consent"
    synthesis_conflict = "synthesis_conflict"
    goal_refinement = "goal_refinement"


class Urgency(StrEnum):
    blocking = "blocking"
    non_blocking = "non_blocking"


class ActionType(StrEnum):
    created_project = "created_project"
    refined_goal = "refined_goal"
    launched_workstream = "launched_workstream"
    paused_workstream = "paused_workstream"
    resumed_workstream = "resumed_workstream"
    steered_workstream = "steered_workstream"
    ingested_pdf = "ingested_pdf"
    synthesized_document = "synthesized_document"
    exported_document = "exported_document"
    added_note = "added_note"
    escalated_to_user = "escalated_to_user"
    archived_project = "archived_project"


# ── Nested models (depended on by multiple entities) ─────────────────────


class AlternativeIntent(BaseModel):
    """Alternative intent interpretation with rationale."""

    model_config = ConfigDict(frozen=False)

    intent_type: IntentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str


class ToggleState(BaseModel):
    """Persisted toggle state for progressive disclosure sections."""

    model_config = ConfigDict(frozen=False)

    show_details: bool = False
    show_suggestions: bool = False


class EpistemicSnapshot(BaseModel):
    """Snapshot of epistemic state at context block creation/closure."""

    model_config = ConfigDict(frozen=False)

    active_claims: list[str] = Field(default_factory=list)
    hypotheses_discussed: list[str] = Field(default_factory=list)
    key_conclusions: list[str] = Field(default_factory=list)


class PendingDecision(BaseModel):
    """A decision awaiting user response within FocusContext."""

    model_config = ConfigDict(frozen=False)

    decision_id: UUID = Field(default_factory=uuid4)
    decision_type: ApprovalRequestType
    description: str
    presented_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None


class ApprovalOption(BaseModel):
    """An option within an ApprovalRequest."""

    model_config = ConfigDict(frozen=False)

    index: int
    label: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    consequences: str = ""


class ActionTaken(BaseModel):
    """Record of an action performed by the coordinator."""

    model_config = ConfigDict(frozen=False)

    action_type: ActionType
    target_id: str | None = None
    description: str
    result: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ── Core entities ─────────────────────────────────────────────────────────


class UserIntent(BaseModel):
    """Parsed NLU classification result for a user turn."""

    model_config = ConfigDict(frozen=False)

    intent_type: IntentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    extracted_entities: dict[str, Any] = Field(default_factory=dict)
    raw_input: str
    alternative_intents: list[AlternativeIntent] = Field(default_factory=list)
    needs_clarification: bool = False

    @field_validator("alternative_intents")
    @classmethod
    def _at_most_three_alternatives(cls, v: list[AlternativeIntent]) -> list[AlternativeIntent]:
        if len(v) > 3:
            msg = "alternative_intents must contain at most 3 entries"
            raise ValueError(msg)
        return v


class DialogueTurn(BaseModel):
    """A single exchange within a REPL session."""

    model_config = ConfigDict(frozen=False)

    turn_id: UUID = Field(default_factory=uuid4)
    speaker: SpeakerType
    content: str = Field(..., min_length=1)
    intent: UserIntent | None = None
    actions_taken: list[ActionTaken] = Field(default_factory=list)
    context_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    approved_by_user: bool | None = None


class ContextBlock(BaseModel):
    """Thematic grouping of dialogue turns with epistemic snapshot."""

    model_config = ConfigDict(frozen=False)

    context_id: UUID = Field(default_factory=uuid4)
    label: str = Field(..., min_length=1, max_length=200)
    summary: str = ""
    parent_context: UUID | None = None
    epistemic_state: EpistemicSnapshot = Field(default_factory=EpistemicSnapshot)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None

    @property
    def turns(self) -> list[UUID]:
        """Derived index — reconstructed from dialogue_turns WHERE context_id = self.context_id.

        Not persisted; DialogueTurn.context_id is the authoritative back-reference.
        """
        raise NotImplementedError("Computed at runtime from dialogue_turns table")


class FocusContext(BaseModel):
    """Coordinator's current attention window within a session."""

    model_config = ConfigDict(frozen=False)

    active_topic: str = ""
    last_workstream_id: str | None = None
    last_hypothesis_id: str | None = None
    pending_decisions: list[PendingDecision] = Field(default_factory=list)
    recent_claim_ids: list[str] = Field(default_factory=list)
    last_context_id: UUID | None = None
    toggle_state: ToggleState = Field(default_factory=ToggleState)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalRequest(BaseModel):
    """A pending decision requiring user input."""

    model_config = ConfigDict(frozen=False)

    request_id: UUID = Field(default_factory=uuid4)
    request_type: ApprovalRequestType
    description: str = Field(..., min_length=10)
    options: list[ApprovalOption] = Field(default_factory=list)
    urgency: Urgency = Urgency.non_blocking
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    user_choice: int | None = None
    user_comment: str | None = None

    @field_validator("options")
    @classmethod
    def _options_count(cls, v: list[ApprovalOption]) -> list[ApprovalOption]:
        if not 1 <= len(v) <= 5:
            msg = "ApprovalRequest.options must contain 1–5 entries"
            raise ValueError(msg)
        return v


class SessionState(BaseModel):
    """Root aggregate for the REPL session."""

    model_config = ConfigDict(frozen=False)

    session_id: UUID = Field(default_factory=uuid4)
    project_id: str
    status: SessionStatus = SessionStatus.active
    pid: int = Field(default_factory=os.getpid)
    heartbeat_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dialogue_history: list[DialogueTurn] = Field(default_factory=list)
    context_blocks: list[ContextBlock] = Field(default_factory=list)
    current_focus: FocusContext = Field(default_factory=FocusContext)
    approval_requests: list[ApprovalRequest] = Field(default_factory=list)
    active_workstreams: list[str] = Field(default_factory=list)
    exit_reason: str | None = None
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
