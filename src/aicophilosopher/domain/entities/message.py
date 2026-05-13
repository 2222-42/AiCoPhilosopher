from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from aicophilosopher.domain.value_objects.enums import MessageType


class EpistemicStatus(BaseModel):
    model_config = ConfigDict(frozen=False)

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    review_status: str = "unreviewed"
    tradition_context: list[str] = []
    uncertainty_flags: list[str] = []


class StatusUpdatePayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    workstream_id: str
    status: str = "running"
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    current_action: str = ""
    deliverable_snippet: str | None = None
    uncertainty_flags: list[str] = []


class DelegationRequestPayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    task_id: str
    task_type: str
    goal_statement: dict[str, Any] = {}
    constraints: dict[str, Any] = {}
    deadline: str = ""
    attachments: list[str] = []


class DelegationResponsePayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    task_id: str
    status: Literal["accepted", "rejected"] = "accepted"
    rejection_reason: str | None = None
    estimated_completion: str = ""


class SteeringCommandPayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    workstream_id: str
    command: str
    parameters: dict[str, Any] = {}


class SteeringAckPayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    workstream_id: str
    command_received: str
    new_plan_summary: str = ""
    impact_assessment: str = ""


class HelpRequestPayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    requesting_agent: str
    problem_type: Literal["incommensurability", "ethical_dilemma", "phenomenological_validation", "review_deadlock"] = "incommensurability"
    problem_description: str = ""
    attempted_solutions: list[str] = []
    options_for_user: list[str] = []
    urgency: Literal["blocking", "non_blocking"] = "blocking"
    context_attachments: list[str] = []


class HelpResponsePayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    response_to: str
    selected_option: int = 0
    user_comment: str = ""
    additional_instructions: str | None = None


class ReviewRequestPayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    workstream_id: str
    round_number: int = 1
    report_path: str = ""
    review_criteria: list[str] = []
    reviewer_lenses: list[str] = []
    max_reviewers: int = 2


class ReviewResponsePayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    workstream_id: str
    round_number: int = 1
    reviewer_id: str = ""
    reviewer_lens: str = ""
    verdict: dict[str, Any] = {}


class ResultDeliveryPayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    task_id: str
    workstream_id: str
    result_type: str = ""
    deliverable_path: str = ""
    summary: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = {}


class ErrorNotificationPayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    error_code: str = ""
    severity: Literal["warning", "critical"] = "warning"
    source_agent: str = ""
    description: str = ""
    retry_count: int = 0
    max_retries: int = 3
    fallback_activated: bool = False


class UserNotificationPayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    notification_type: Literal["workstream_completed", "review_escalation", "help_needed", "goal_achieved"] = "workstream_completed"
    workstream_id: str = ""
    summary: str = ""
    action_required: bool = False
    suggested_next_steps: list[str] = []


_MESSAGE_PAYLOAD_MAP: dict[MessageType, type[BaseModel]] = {
    MessageType.STATUS_UPDATE: StatusUpdatePayload,
    MessageType.DELEGATION_REQUEST: DelegationRequestPayload,
    MessageType.DELEGATION_RESPONSE: DelegationResponsePayload,
    MessageType.STEERING_COMMAND: SteeringCommandPayload,
    MessageType.STEERING_ACK: SteeringAckPayload,
    MessageType.HELP_REQUEST: HelpRequestPayload,
    MessageType.HELP_RESPONSE: HelpResponsePayload,
    MessageType.REVIEW_REQUEST: ReviewRequestPayload,
    MessageType.REVIEW_RESPONSE: ReviewResponsePayload,
    MessageType.RESULT_DELIVERY: ResultDeliveryPayload,
    MessageType.ERROR_NOTIFICATION: ErrorNotificationPayload,
    MessageType.USER_NOTIFICATION: UserNotificationPayload,
}


class Message(BaseModel):
    model_config = ConfigDict(frozen=False)

    message_id: str
    sender_id: str
    recipient_id: str
    message_type: MessageType
    payload: dict[str, Any] = {}
    timestamp: str = ""
    epistemic_status: EpistemicStatus | None = None
    correlation_id: str | None = None

    @classmethod
    def validate_payload(cls, message_type: MessageType, payload: dict[str, Any]) -> bool:
        payload_cls = _MESSAGE_PAYLOAD_MAP.get(message_type)
        if payload_cls is None:
            return False
        try:
            payload_cls.model_validate(payload)
            return True
        except Exception:
            return False


def get_payload_schema(message_type: MessageType) -> type[BaseModel] | None:
    return _MESSAGE_PAYLOAD_MAP.get(message_type)
