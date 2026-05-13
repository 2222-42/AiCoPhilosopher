from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConceptNode(BaseModel):
    model_config = ConfigDict(frozen=False)

    concept_id: str
    name: str
    tradition: str = "analytic"
    definition: str = ""
    related_concepts: list[str] = []
    distinctions: list[dict[str, Any]] = []
    genealogy: list[dict[str, Any]] = []
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    notes: str = ""


class Distinction(BaseModel):
    model_config = ConfigDict(frozen=False)

    distinction_id: str
    concept_a: str
    concept_b: str
    distinction_type: str
    description: str
    tradition: str = "analytic"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ThoughtExperiment(BaseModel):
    model_config = ConfigDict(frozen=False)

    experiment_id: str
    title: str
    description: str
    tradition: str = "analytic"
    epistemic_status: str = "proposed"
    analysis: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
