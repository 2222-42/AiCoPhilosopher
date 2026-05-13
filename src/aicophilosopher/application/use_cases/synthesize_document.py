from typing import Any


class SynthesizeDocumentUseCase:
    async def execute(self, project_id: str, **kwargs: object) -> dict[str, Any]:
        raise NotImplementedError
