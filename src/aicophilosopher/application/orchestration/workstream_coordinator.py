import uuid
from typing import Any

from aicophilosopher.application.orchestration.base import BaseAgent

WORKSTREAM_TYPE_MAP: dict[str, type] = {}


def register_workstream_type(name: str, coordinator_class: type) -> None:
    WORKSTREAM_TYPE_MAP[name] = coordinator_class


class WorkstreamCoordinatorAgent(BaseAgent):
    def __init__(
        self,
        workstream_id: str,
        workstream_type: str,
        goal_statement: dict[str, Any],
        llm_backend: Any = None,
        message_queue: Any = None,
        filesystem: Any = None,
        **kwargs: object,
    ) -> None:
        super().__init__(agent_id=workstream_id, llm_backend=llm_backend, message_queue=message_queue, config=kwargs.get("config"), tool_registry=kwargs.get("tool_registry"))  # type: ignore[arg-type]
        self.workstream_id = workstream_id
        self.workstream_type = workstream_type
        self.goal_statement = goal_statement
        self.filesystem = filesystem
        self.status = "pending"
        self._incremental_updates: list[dict[str, Any]] = []
        self._sub_agents: list[str] = []
        self._results = ""

    async def start(self) -> None:
        self.status = "running"
        await self._log_update({"action": "start", "message": f"Workstream '{self.workstream_id}' started"})

    async def pause(self) -> None:
        if self.status != "running":
            return
        self.status = "paused"
        await self._log_update({"action": "pause", "message": f"Workstream '{self.workstream_id}' paused"})

    async def resume(self) -> None:
        if self.status != "paused":
            return
        self.status = "running"
        await self._log_update({"action": "resume", "message": f"Workstream '{self.workstream_id}' resumed"})

    async def steer(self, instruction: str) -> None:
        await self._log_update({"action": "steer", "instruction": instruction})

    def fail(self, reason: str) -> None:
        self.status = "failed"
        self._results = f"## Failed: {reason}"

    def stall(self, reason: str) -> None:
        self.status = "stalled"
        self._results = f"## Stalled: {reason}"

    def complete(self, results: str) -> None:
        self.status = "completed"
        self._results = results

    async def get_progress(self) -> dict[str, Any]:
        return {
            "workstream_id": self.workstream_id,
            "type": self.workstream_type,
            "status": self.status,
            "incremental_update_count": len(self._incremental_updates),
            "sub_agent_count": len(self._sub_agents),
        }

    async def add_sub_agent(self, agent_id: str) -> None:
        self._sub_agents.append(agent_id)

    async def _log_update(self, update: dict[str, Any]) -> None:
        entry = {
            "update_id": f"upd-{uuid.uuid4().hex[:8]}",
            "workstream_id": self.workstream_id,
            "timestamp": update.get("timestamp", ""),
            **update,
        }
        self._incremental_updates.append(entry)
        if self.filesystem:
            await self.filesystem.write_json(
                self.workstream_id,
                f"workstreams/{self.workstream_id}_incremental.log",
                self._incremental_updates,
            )

    @staticmethod
    def create_workstream(ws_type: str, goal: dict[str, Any], **kwargs: Any) -> "WorkstreamCoordinatorAgent":
        coord_cls = WORKSTREAM_TYPE_MAP.get(ws_type, WorkstreamCoordinatorAgent)
        if coord_cls is None:
            coord_cls = WorkstreamCoordinatorAgent
        ws_id = f"ws-{uuid.uuid4().hex[:8]}"
        return coord_cls(  # type: ignore[no-any-return]
            workstream_id=ws_id,
            workstream_type=ws_type,
            goal_statement=goal,
            **kwargs,
        )
