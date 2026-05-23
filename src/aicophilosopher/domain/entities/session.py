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

# ── Enums (UPPER_CASE per codebase convention) ──────────────────────────


class SessionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class SpeakerType(StrEnum):
    USER = "user"
    COORDINATOR = "coordinator"
    SYSTEM = "system"


class IntentType(StrEnum):
    START_INQUIRY = "start_inquiry"
    CLARIFY_QUESTION = "clarify_question"
    PROPOSE_WORKSTREAM = "propose_workstream"
    STEER_WORKSTREAM = "steer_workstream"
    REQUEST_STATUS = "request_status"
    REQUEST_DETAIL = "request_detail"
    REQUEST_EXPORT = "request_export"
    APPROVE_ACTION = "approve_action"
    REJECT_ACTION = "reject_action"
    ASK_QUESTION = "ask_question"
    INJECT_INFORMATION = "inject_information"
    REQUEST_HELP = "request_help"
    PAUSE_SESSION = "pause_session"
    RESUME_SESSION = "resume_session"
    ARCHIVE_PROJECT = "archive_project"
    COMPARE_TRADITIONS = "compare_traditions"


class ApprovalRequestType(StrEnum):
    WORKSTREAM_PROPOSAL = "workstream_proposal"
    NORMATIVE_JUDGMENT = "normative_judgment"
    INCOMMENSURABILITY_RESOLUTION = "incommensurability_resolution"
    REVIEW_ESCALATION = "review_escalation"
    EXTERNAL_SEARCH_CONSENT = "external_search_consent"
    SYNTHESIS_CONFLICT = "synthesis_conflict"
    GOAL_REFINEMENT = "goal_refinement"


class Urgency(StrEnum):
    BLOCKING = "blocking"
    NON_BLOCKING = "non_blocking"


class ActionType(StrEnum):
    CREATED_PROJECT = "created_project"
    REFINED_GOAL = "refined_goal"
    LAUNCHED_WORKSTREAM = "launched_workstream"
    PAUSED_WORKSTREAM = "paused_workstream"
    RESUMED_WORKSTREAM = "resumed_workstream"
    STEERED_WORKSTREAM = "steered_workstream"
    INGESTED_PDF = "ingested_pdf"
    SYNTHESIZED_DOCUMENT = "synthesized_document"
    EXPORTED_DOCUMENT = "exported_document"
    ADDED_NOTE = "added_note"
    ESCALATED_TO_USER = "escalated_to_user"
    ARCHIVED_PROJECT = "archived_project"


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
    """Thematic grouping of dialogue turns with epistemic snapshot.

    Turns are NOT stored on the model. Use SessionState.get_turns_for_context()
    to reconstruct the turn list from dialogue_history at runtime.
    """

    model_config = ConfigDict(frozen=False)

    context_id: UUID = Field(default_factory=uuid4)
    label: str = Field(..., min_length=1, max_length=200)
    summary: str = ""
    parent_context: UUID | None = None
    epistemic_state: EpistemicSnapshot = Field(default_factory=EpistemicSnapshot)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    closed_at: datetime | None = None


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
    options: list[ApprovalOption] = Field(..., min_length=1, max_length=5)
    urgency: Urgency = Urgency.NON_BLOCKING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved_at: datetime | None = None
    user_choice: int | None = None
    user_comment: str | None = None


class SessionState(BaseModel):
    """Root aggregate for the REPL session."""

    model_config = ConfigDict(frozen=False)

    session_id: UUID = Field(default_factory=uuid4)
    project_id: str
    status: SessionStatus = SessionStatus.ACTIVE
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

    def get_turns_for_context(self, context_id: UUID) -> list[DialogueTurn]:
        """Reconstruct turn list for a ContextBlock from dialogue_history.

        This is the authoritative lookup; turns are NOT stored on ContextBlock.
        """
        return [t for t in self.dialogue_history if t.context_id == context_id]
