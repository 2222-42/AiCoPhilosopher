from pydantic import BaseModel, ConfigDict


class Note(BaseModel):
    model_config = ConfigDict(frozen=False)

    note_id: str
    text: str
    project_id: str
    attached_to: str | None = None
    created_at: str = ""
    updated_at: str = ""
