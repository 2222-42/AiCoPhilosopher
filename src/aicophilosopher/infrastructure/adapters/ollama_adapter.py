
import httpx

from aicophilosopher.ports.llm_port import GenerationResult


class OllamaBackend:
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def generate(self, prompt: str, **kwargs: object) -> GenerationResult:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
                data = resp.json()
                return GenerationResult(
                    text=data.get("response", ""),
                    usage={"eval_count": data.get("eval_count", 0), "eval_duration": data.get("eval_duration", 0)},
                    model=self.model,
                    finish_reason="stop" if data.get("done") else None,
                )
        except httpx.HTTPError:
            return GenerationResult(text="", usage={}, model=self.model, finish_reason="error")

    async def embed(self, text: str, **kwargs: object) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                resp.raise_for_status()
                data = resp.json()
                emb: list[float] = data.get("embedding", [])
                return emb
        except httpx.HTTPError:
            return []
