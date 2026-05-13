from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aicophilosopher.domain.value_objects.enums import MessageType


class EpistemicStatus(BaseModel):
    model_config = ConfigDict(frozen=False)

    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    review_status: str = "unreviewed"
    tradition_context: list[str] = []
    uncertainty_flags: list[str] = []


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
