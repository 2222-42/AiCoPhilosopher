
from aicophilosopher.ports.llm_port import GenerationResult, LLMPort


class GeminiBackend(LLMPort):
    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-pro") -> None:
        self.api_key = api_key
        self.model = model

    async def generate(self, prompt: str, **kwargs: object) -> GenerationResult:
        try:
            import google.generativeai as genai
        except ImportError:
            return GenerationResult(text="", usage={}, model=self.model, finish_reason="error")

        genai.configure(api_key=self.api_key)  # type: ignore[attr-defined]
        model = genai.GenerativeModel(self.model)  # type: ignore[attr-defined]
        resp = await model.generate_content_async(prompt)
        usage = {}
        if hasattr(resp, "usage_metadata") and resp.usage_metadata:
            usage = {
                "prompt_tokens": resp.usage_metadata.prompt_token_count or 0,
                "completion_tokens": resp.usage_metadata.candidates_token_count or 0,
            }
        return GenerationResult(
            text=resp.text or "",
            usage=usage,
            model=self.model,
            finish_reason=getattr(resp, "finish_reason", None),
        )

    async def embed(self, text: str, **kwargs: object) -> list[float]:
        try:
            import google.generativeai as genai
        except ImportError:
            return []

        genai.configure(api_key=self.api_key)  # type: ignore[attr-defined]
        result = await genai.embed_content_async(model="models/embedding-001", content=text)  # type: ignore[attr-defined]
        embedding: list[float] = result["embedding"]
        return embedding
