from typing import Protocol


class GenerationResult:
    text: str = ""
    usage: dict[str, int] = {}
    model: str = ""
    finish_reason: str | None = None


class LLMPort(Protocol):
    async def generate(self, prompt: str, **kwargs: object) -> GenerationResult:
        ...

    async def embed(self, text: str, **kwargs: object) -> list[float]:
        ...
