from typing import Any

from pydantic import BaseModel, ConfigDict

from aicophilosopher.domain.value_objects.enums import WorkstreamStatus, WorkstreamType


class FailedExploration(BaseModel):
    model_config = ConfigDict(frozen=False)

    exploration_id: str
    goal_attempted: str
    failure_reason: str
    lessons_learned: str
    timestamp: str
    full_report_path: str | None = None


class ProgressUpdate(BaseModel):
    model_config = ConfigDict(frozen=False)

    update_id: str
    timestamp: str
    progress_percent: float
    current_action: str
    deliverable_snippet: str | None = None
    uncertainty_flags: list[str] = []


class WorkstreamState(BaseModel):
    model_config = ConfigDict(frozen=False)

    workstream_id: str
    type: WorkstreamType
    status: WorkstreamStatus = WorkstreamStatus.PENDING
    goal_statement: dict[str, Any] = {}
    assigned_coordinator: str = ""
    assigned_sub_agents: list[str] = []
    results: str = ""
    incremental_updates: list[ProgressUpdate] = []
    review_rounds: list[dict[str, Any]] = []
    uncertainty_flags: list[dict[str, Any]] = []
    failed_explorations: list[FailedExploration] = []
