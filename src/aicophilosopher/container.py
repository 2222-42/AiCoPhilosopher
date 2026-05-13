from typing import Any, overload

from aicophilosopher.domain.services.config import Config
from aicophilosopher.infrastructure.adapters.claude_adapter import ClaudeBackend
from aicophilosopher.infrastructure.adapters.gemini_adapter import GeminiBackend
from aicophilosopher.infrastructure.adapters.ollama_adapter import OllamaBackend


class Container:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._registry: dict[str, type[Any]] = {}
        self._instances: dict[str, Any] = {}
        self.config = config or {}

    def register(self, interface: type, implementation: type[Any]) -> None:
        self._registry[self._key(interface)] = implementation

    @overload
    def resolve(self, interface: type) -> Any: ...
    @overload
    def resolve(self, interface: str) -> Any: ...
    def resolve(self, interface: type | str) -> Any:
        key = interface if isinstance(interface, str) else self._key(interface)
        if key in self._instances:
            return self._instances[key]
        if key in self._registry:
            impl = self._registry[key]
            instance = impl()
            self._instances[key] = instance
            return instance
        raise NotImplementedError(f"No adapter registered for {key}")

    def register_instance(self, interface: type | str, instance: Any) -> None:
        key = interface if isinstance(interface, str) else self._key(interface)
        self._instances[key] = instance

    @staticmethod
    def _key(interface: type) -> str:
        mod = getattr(interface, "__module__", "")
        name = getattr(interface, "__name__", str(interface))
        return f"{mod}.{name}" if mod else name

    @staticmethod
    def create_llm_backend(config: Config | None = None) -> Any:
        cfg = config or Config()
        backend = cfg.llm_backend
        if backend == "claude":
            return ClaudeBackend(api_key=cfg.llm_api_key or None, model=cfg.llm_model or "claude-3-5-sonnet-20241022")
        elif backend == "gemini":
            return GeminiBackend(api_key=cfg.llm_api_key or None, model=cfg.llm_model or "gemini-1.5-pro")
        elif backend == "ollama":
            return OllamaBackend(model=cfg.llm_model or "llama3")
        else:
            raise ValueError(f"Unknown LLM backend: {backend}")
