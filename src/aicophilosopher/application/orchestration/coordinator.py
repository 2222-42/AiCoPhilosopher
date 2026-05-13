from typing import Any

from aicophilosopher.application.orchestration.base import BaseAgent

CLARIFICATION_QUESTIONS = [
    "Thank you for your question. Could you clarify which philosophical tradition or methodological framework you're approaching this from?",
    "Could you help me understand which key concepts you think are most central to this inquiry?",
    "What would a satisfactory answer to this question look like to you?",
    "Are there any specific thinkers, texts, or arguments you'd like me to engage with?",
    "Do you have a preference for how we should proceed — for example, conceptual analysis, literature review, argument reconstruction, or cross-traditional comparison?",
]


class ProjectCoordinatorAgent(BaseAgent):
    def __init__(
        self,
        project_id: str,
        llm_backend: Any = None,
        message_queue: Any = None,
        storage: Any = None,
        filesystem: Any = None,
        **kwargs: object,
    ) -> None:
        super().__init__(agent_id="project_coordinator", project_id=project_id, llm_backend=llm_backend, message_queue=message_queue, config=kwargs.get("config"), tool_registry=kwargs.get("tool_registry"))  # type: ignore[arg-type]
        self.project_id = project_id
        self.storage = storage
        self.filesystem = filesystem
        self.dialogue_history: list[dict[str, str]] = []
        self._turn_count = 0
        self._goal_proposed: str | None = None
        self._goal_approved = False

    async def run(self, user_input: str = "", **kwargs: object) -> dict[str, Any]:  # type: ignore[override]
        command = str(kwargs.get("command", "")).lower()
        if command == "start":
            return self._start_dialogue(None) if not user_input else self._start_dialogue(user_input)
        elif command == "refine_goal":
            return self._handle_refine_goal(user_input)
        elif command == "approve_goal":
            return self._handle_approve_goal()
        elif command == "propose_workstream":
            ws_type = str(kwargs.get("workstream_type", "literature_search"))
            return await self._handle_propose_workstream(ws_type)
        elif command == "steer":
            ws_id = str(kwargs.get("workstream_id", ""))
            instruction = str(kwargs.get("instruction", ""))
            return await self._handle_steer(ws_id, instruction)
        elif command == "status":
            return await self._get_status_summary()
        return self._start_dialogue(user_input)

    def _start_dialogue(self, user_input: str | None) -> dict[str, Any]:
        if not user_input:
            return {
                "message": "Welcome to the AI Co-Philosopher. What philosophical question would you like to explore?",
                "dialogue_state": "awaiting_question",
                "turn": 0,
            }

        self._turn_count += 1
        self.dialogue_history.append({"role": "user", "content": user_input})

        if self._turn_count > len(CLARIFICATION_QUESTIONS):
            goal = self._synthesize_goal()
            self._goal_proposed = goal
            return {
                "message": f"Based on our discussion, I'd propose the following refined research goal:\n\n**{goal}**\n\nWould you like to approve this goal, or would you like to refine it further?",
                "dialogue_state": "goal_proposed",
                "proposed_goal": goal,
                "turn": self._turn_count,
            }

        question = CLARIFICATION_QUESTIONS[self._turn_count - 1]
        return {
            "message": question,
            "dialogue_state": "clarifying",
            "turn": self._turn_count,
        }

    def _handle_refine_goal(self, user_input: str) -> dict[str, Any]:
        if not self._goal_proposed:
            return {"error": "No goal has been proposed yet. Please continue the dialogue."}
        self.dialogue_history.append({"role": "user", "content": user_input})
        revised_goal = self._synthesize_goal()
        self._goal_proposed = revised_goal
        return {
            "message": f"I've refined the goal based on your input:\n\n**{revised_goal}**\n\nWould you like to approve this goal, or refine it further?",
            "dialogue_state": "goal_proposed",
            "proposed_goal": revised_goal,
        }

    def _handle_approve_goal(self) -> dict[str, Any]:
        if not self._goal_proposed:
            return {"error": "No goal has been proposed yet."}
        self._goal_approved = True
        return {
            "message": f"Goal approved! You can now launch workstreams using the `start workstream` command.\n\nApproved goal: **{self._goal_proposed}**",
            "dialogue_state": "goals_approved",
            "approved_goal": self._goal_proposed,
        }

    async def _handle_propose_workstream(self, workstream_type: str) -> dict[str, Any]:
        if not self._goal_approved:
            return {"error": "Cannot start workstream: no approved goals. Use `refine_goal` first."}
        return {
            "message": f"Workstream of type '{workstream_type}' proposed for goal: **{self._goal_proposed}**\n\nDo you want to proceed with this workstream?",
            "workstream_type": workstream_type,
            "proposal": {
                "type": workstream_type,
                "goal": {"description": self._goal_proposed, "approved": True},
                "assigned_coordinator": f"{workstream_type}_coordinator",
            },
        }

    async def _handle_steer(self, workstream_id: str, instruction: str) -> dict[str, Any]:
        return {
            "message": f"Steering command received for workstream '{workstream_id}': {instruction}",
            "workstream_id": workstream_id,
            "instruction": instruction,
            "acknowledged": True,
        }

    async def _get_status_summary(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "goal_approved": self._goal_approved,
            "proposed_goal": self._goal_proposed,
            "turn_count": self._turn_count,
            "dialogue_state": "goals_approved" if self._goal_approved else ("goal_proposed" if self._goal_proposed else "clarifying"),
            "active_hypotheses": 0,
            "refuted_hypotheses": 0,
            "under_review": 0,
            "stalled": 0,
        }

    def _synthesize_goal(self) -> str:
        # TODO: incorporate dialogue_history to generate a meaningful goal
        return "To investigate the philosophical question through conceptual analysis and cross-traditional comparison, producing a structured living document with annotated arguments and a dialectical history appendix."

    def get_dialogue_state(self) -> str:
        if self._goal_approved:
            return "goals_approved"
        elif self._goal_proposed:
            return "goal_proposed"
        elif self._turn_count == 0:
            return "awaiting_question"
        return "clarifying"
