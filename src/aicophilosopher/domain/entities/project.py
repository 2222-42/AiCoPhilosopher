from typing import Any

from pydantic import BaseModel, ConfigDict

from aicophilosopher.domain.value_objects.enums import ProjectStatus


class GoalStatement(BaseModel):
    model_config = ConfigDict(frozen=False)

    goal_id: str
    description: str
    approved_by_user: bool = False
    traditions: list[str] = []
    methodological_preferences: dict[str, Any] | None = None


class ProjectMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    created_at: str
    updated_at: str
    total_workstreams: int = 0
    total_hypotheses: int = 0
    total_uncertainty_records: int = 0


class ExternalConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    hermes_enabled: bool = False
    opencode_enabled: bool = False
    allow_external_search: bool = False


class ProjectState(BaseModel):
    model_config = ConfigDict(frozen=False)

    project_id: str
    title: str
    original_question: str
    status: ProjectStatus = ProjectStatus.CREATED
    refined_goals: list[GoalStatement] = []
    workstreams: dict[str, dict[str, Any]] = {}
    living_document: str = ""
    dialectical_history: list[dict[str, Any]] = []
    hypotheses: list[dict[str, Any]] = []
    conceptual_genealogy: dict[str, dict[str, Any]] = {}
    uncertainty_registry: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    metadata: ProjectMetadata | None = None
    external_layer_config: ExternalConfig | None = None
