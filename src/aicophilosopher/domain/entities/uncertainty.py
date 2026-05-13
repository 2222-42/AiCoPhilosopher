from pydantic import BaseModel, ConfigDict, Field

from aicophilosopher.domain.value_objects.enums import ReviewStatus


class UncertaintyRecord(BaseModel):
    model_config = ConfigDict(frozen=False)

    claim_id: str
    claim_text: str
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    counter_argument_strength: float = Field(default=0.0, ge=0.0, le=1.0)
    tradition_validity: dict[str, float] = {}
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    stalled_sections: list[str] = []
    last_updated: str = ""
