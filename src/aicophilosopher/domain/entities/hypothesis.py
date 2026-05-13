from pydantic import BaseModel, ConfigDict, Field

from aicophilosopher.domain.value_objects.enums import HypothesisStatus, HypothesisStrength, Origin


class CounterArgument(BaseModel):
    model_config = ConfigDict(frozen=False)

    argument_id: str
    claim: str
    source: str
    strength: float = Field(default=0.0, ge=0.0, le=1.0)
    tradition: str | None = None


class Reference(BaseModel):
    model_config = ConfigDict(frozen=False)

    reference_id: str
    title: str
    authors: list[str] = []
    year: int | None = None
    source: str = ""
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class HypothesisRecord(BaseModel):
    model_config = ConfigDict(frozen=False)

    hypothesis_id: str
    statement: str
    strength: HypothesisStrength = HypothesisStrength.WEAK
    origin: Origin = Origin.AI
    supporting_evidence: list[Reference] = []
    counter_arguments: list[CounterArgument] = []
    dialectical_children: list[str] = []
    status: HypothesisStatus = HypothesisStatus.ACTIVE
    epistemic_tradition: str | None = None
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    created_at: str = ""
