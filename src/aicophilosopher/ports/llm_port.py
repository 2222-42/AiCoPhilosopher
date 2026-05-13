from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class GenerationResult:
    text: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    model: str = ""
    finish_reason: str | None = None


class LLMPort(Protocol):
    async def generate(self, prompt: str, **kwargs: object) -> GenerationResult:
        ...

    async def embed(self, text: str, **kwargs: object) -> list[float]:
        ...
