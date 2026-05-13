from typing import Any

from aicophilosopher.ports.llm_port import GenerationResult, LLMPort


class ClaudeBackend(LLMPort):
    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022") -> None:
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, **kwargs: object) -> GenerationResult:
        try:
            import anthropic
        except ImportError:
            return GenerationResult(text="", usage={}, model=self.model, finish_reason="error")

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        resp = await client.messages.create(
            model=self.model,
            max_tokens=int(str(kwargs.get("max_tokens", "4096"))),
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in resp.content if hasattr(block, "text"))
        return GenerationResult(
            text=text,
            usage={"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens},
            model=self.model,
            finish_reason=resp.stop_reason,
        )

    async def embed(self, text: str, **kwargs: object) -> list[float]:
        raise NotImplementedError("Claude does not support standalone embeddings via this API")

    async def generate_stream(self, prompt: str, **kwargs: object) -> Any:
        raise NotImplementedError
