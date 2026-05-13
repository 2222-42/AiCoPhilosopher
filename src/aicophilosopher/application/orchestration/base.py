import logging
from typing import Any

from aicophilosopher.application.services.tool_registry import BaseTool, ToolRegistry
from aicophilosopher.infrastructure.adapters.message_queue_adapter import MessageQueueAdapter
from aicophilosopher.ports.llm_port import GenerationResult, LLMPort


class BaseAgent:
    def __init__(
        self,
        agent_id: str,
        project_id: str = "",
        llm_backend: LLMPort | None = None,
        message_queue: MessageQueueAdapter | None = None,
        tool_registry: ToolRegistry | None = None,
        config: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> None:
        self.agent_id = agent_id
        self.project_id = project_id
        self.llm = llm_backend
        self.message_queue = message_queue
        self.tool_registry = tool_registry
        self.config = config or {}
        self.logger = logging.getLogger(f"aicophilosopher.agent.{agent_id}")
        if tool_registry is not None:
            self.set_tool_registry(tool_registry)

    def set_tool_registry(self, registry: ToolRegistry) -> None:
        self.tool_registry = registry

    def get_tool(self, name: str) -> BaseTool | None:
        if self.tool_registry is None:
            return None
        return self.tool_registry.get_tool(name)

    async def run(self, **kwargs: object) -> Any:
        raise NotImplementedError

    async def send_message(self, recipient_id: str, message_type: str, payload: dict[str, object]) -> str:
        if self.message_queue is None:
            raise RuntimeError("MessageQueue not configured")
        return await self.message_queue.send({
            "sender_id": self.agent_id,
            "project_id": self.project_id,
            "recipient_id": recipient_id,
            "message_type": message_type,
            "payload": payload,
        })

    async def llm_generate(self, prompt: str, **kwargs: object) -> GenerationResult:
        if self.llm is None:
            raise RuntimeError("LLM backend not configured")
        return await self.llm.generate(prompt, **kwargs)
