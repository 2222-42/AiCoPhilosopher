

class OllamaBackend:
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    async def generate(self, prompt: str, **kwargs: object) -> dict[str, object]:
        raise NotImplementedError

    async def embed(self, text: str, **kwargs: object) -> list[float]:
        raise NotImplementedError
