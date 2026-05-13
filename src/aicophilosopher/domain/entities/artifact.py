from typing import Any

from pydantic import BaseModel, ConfigDict

from aicophilosopher.domain.value_objects.enums import ArtifactType


class Artifact(BaseModel):
    model_config = ConfigDict(frozen=False)

    artifact_id: str
    artifact_type: ArtifactType = ArtifactType.OTHER
    title: str = ""
    file_path: str
    workstream_id: str | None = None
    metadata: dict[str, Any] = {}
    created_at: str = ""
