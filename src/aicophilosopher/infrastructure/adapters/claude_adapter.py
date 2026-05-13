

class ClaudeBackend:
    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, **kwargs: object) -> dict[str, object]:
        raise NotImplementedError

    async def embed(self, text: str, **kwargs: object) -> list[float]:
        raise NotImplementedError
