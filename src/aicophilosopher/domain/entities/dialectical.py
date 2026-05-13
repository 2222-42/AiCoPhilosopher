from pydantic import BaseModel, ConfigDict, Field

from aicophilosopher.domain.value_objects.enums import DialecticalMoveType


class DialecticalMove(BaseModel):
    model_config = ConfigDict(frozen=False)

    move_id: str
    move_type: DialecticalMoveType
    claim: str
    premises: list[str] = []
    conclusion: str = ""
    source_agent: str = ""
    target_move_id: str | None = None
    timestamp: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    tradition_context: list[str] = []
    notes: str = ""
