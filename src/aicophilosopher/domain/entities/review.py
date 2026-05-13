from pydantic import BaseModel, ConfigDict, Field

from aicophilosopher.domain.value_objects.enums import ReviewerVerdictStatus, ReviewRoundStatus


class ReviewerVerdict(BaseModel):
    model_config = ConfigDict(frozen=False)

    reviewer_id: str
    reviewer_lens: str
    status: ReviewerVerdictStatus = ReviewerVerdictStatus.APPROVED
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    comments: str = ""
    identified_issues: list[str] = []


class ReviewRound(BaseModel):
    model_config = ConfigDict(frozen=False)

    round_number: int
    workstream_id: str
    status: ReviewRoundStatus = ReviewRoundStatus.PENDING
    reviewer_verdicts: list[ReviewerVerdict] = []
    escalation_flag: bool = False
    escalation_reason: str = ""
