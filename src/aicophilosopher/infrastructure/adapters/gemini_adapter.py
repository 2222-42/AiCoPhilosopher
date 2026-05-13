from aicophilosopher.ports.llm_port import GenerationResult


class GeminiBackend:
    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-pro") -> None:
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, **kwargs: object) -> GenerationResult:
        raise NotImplementedError

    async def embed(self, text: str, **kwargs: object) -> list[float]:
        raise NotImplementedError
