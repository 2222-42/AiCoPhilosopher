from typing import Any

from aicophilosopher.domain.exceptions import ValidationError


class BaseTool:
    name: str = ""
    description: str = ""

    async def execute(self, **kwargs: object) -> Any:
        raise NotImplementedError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValidationError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def unregister_tool(self, name: str) -> None:
        self._tools.pop(name, None)
