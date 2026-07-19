from typing import Any

from aicophilosopher.application.orchestration.base import BaseAgent

CLARIFICATION_QUESTIONS = [
    "Thank you for your question. Could you clarify which philosophical tradition or methodological framework you're approaching this from?",
    "Could you help me understand which key concepts you think are most central to this inquiry?",
    "What would a satisfactory answer to this question look like to you?",
    "Are there any specific thinkers, texts, or arguments you'd like me to engage with?",
    "Do you have a preference for how we should proceed — for example, conceptual analysis, literature review, argument reconstruction, or cross-traditional comparison?",
]

# Labels for user answers that follow the initial question, aligned with
# CLARIFICATION_QUESTIONS order (deterministic goal synthesis; no LLM required).
_GOAL_ASPECT_LABELS = (
    "philosophical tradition / framework",
    "central concepts",
    "success criteria",
    "thinkers, texts, or arguments",
    "preferred method",
)

_DEFAULT_GOAL = (
    "To investigate the philosophical question through conceptual analysis and "
    "cross-traditional comparison, producing a structured living document with "
    "annotated arguments and a dialectical history appendix."
)

_GOAL_DELIVERABLE = (
    "Approach: conceptual analysis and cross-traditional comparison; deliver a "
    "structured living document with annotated arguments and a dialectical history "
    "appendix."
)


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
        self.external_bridge: Any = None
        self.active_workstreams: dict[str, dict[str, Any]] = {}

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
        elif command == "logs":
            ws_id = str(kwargs.get("workstream_id", ""))
            return self._get_workstream_logs(ws_id)
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

        if self._turn_count >= len(CLARIFICATION_QUESTIONS):
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
        if self._goal_approved:
            return {"error": "Goal is already approved. Cannot refine an approved goal."}
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
            "message": (
                f"Goal approved! 🎉\n\n"
                f"Approved goal: **{self._goal_proposed}**\n\n"
                f"Now launch a workstream. Try typing:\n"
                f"  • \"start literature search\"\n"
                f"  • \"analyze this concept\"\n"
                f"  • \"compare traditions\"\n"
                f"  • \"construct an argument\"\n"
                f"Or use slash commands: /search, /analyze, /argue, /compare, /status"
            ),
            "dialogue_state": "goal_approved",
            "approved_goal": self._goal_proposed,
        }

    async def _handle_propose_workstream(self, workstream_type: str) -> dict[str, Any]:
        if not self._goal_approved:
            return {"error": "Cannot start workstream: no approved goals. Use `approve_goal` first."}

        # If external bridge is available, delegate the workstream
        bridge_result = None
        if self.external_bridge is not None:
            try:
                bridge_result = await self.external_bridge.request(
                    endpoint="delegate_task",
                    payload={
                        "prompt": (
                            f"You are a philosophical research agent executing a workstream.\n"
                            f"Goal: {self._goal_proposed}\n"
                            f"Workstream type: {workstream_type}\n"
                            f"Execute this workstream and return your findings."
                        ),
                    },
                    consent_scope="workstream_delegation",
                )
            except Exception:
                bridge_result = None

        ws_id = f"ws-{workstream_type}-{len(self.active_workstreams) + 1}"
        self.active_workstreams[ws_id] = {
            "workstream_id": ws_id,
            "type": workstream_type,
            "status": "running",
            "goal": self._goal_proposed,
            "bridge_result": bridge_result,
        }

        msg = f"Workstream '{workstream_type}' launched as {ws_id}."
        if bridge_result and bridge_result.get("status") == "success":
            output_preview = str(bridge_result.get("data", {}).get("output", ""))[:200]
            msg += f"\n\nOpenCode Go response:\n{output_preview}"

        return {
            "message": msg,
            "workstream_type": workstream_type,
            "workstream_id": ws_id,
            "active_workstreams": [
                f"{wid} — {ws['status']}" for wid, ws in self.active_workstreams.items()
            ],
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
        state = self.get_dialogue_state()
        status_msg = {
            "awaiting_question": "No dialogue started yet. Ask a philosophical question to begin.",
            "clarifying": f"Socratic clarification in progress (turn {self._turn_count}/5). Continue the dialogue.",
            "goal_proposed": "A goal has been proposed. Type 'yes' to approve, or continue refining.",
            "goal_approved": "Goal approved! Launch workstreams: type 'start literature search', 'analyze this concept', etc.",
        }.get(state, state)

        return {
            "summary": (
                f"Project: {self.project_id}\n"
                f"State: {state} | Turn: {self._turn_count}/5\n"
                f"Goal approved: {self._goal_approved}"
            ),
            "epistemic_status": status_msg,
            "active_workstreams": [
                f"{wid} — {ws['status']}" for wid, ws in self.active_workstreams.items()
            ],
            "project_id": self.project_id,
            "goal_approved": self._goal_approved,
            "proposed_goal": self._goal_proposed,
            "turn_count": self._turn_count,
            "dialogue_state": state,
            "active_hypotheses": len(self.active_workstreams),
            "refuted_hypotheses": 0,
            "under_review": 0,
            "stalled": 0,
        }

    def _get_workstream_logs(self, workstream_id: str) -> dict[str, Any]:
        """Return output/logs for a specific workstream."""
        if not workstream_id:
            # List all workstreams
            if not self.active_workstreams:
                return {"summary": "No workstreams running.", "active_workstreams": []}
            lines = []
            for wid, ws in self.active_workstreams.items():
                br = ws.get("bridge_result")
                preview = ""
                if br and br.get("status") == "success":
                    output = br.get("data", {}).get("output", "")
                    preview = output[:80] + ("..." if len(output) > 80 else "")
                lines.append(f"{wid} — {ws['status']} | {preview}")
            return {
                "summary": "Active workstreams:\n" + "\n".join(lines),
                "active_workstreams": [
                    f"{wid} — {ws['status']}" for wid, ws in self.active_workstreams.items()
                ],
            }

        ws = self.active_workstreams.get(workstream_id)
        if ws is None:
            return {"error": f"Workstream '{workstream_id}' not found. Active: {list(self.active_workstreams)}"}
        br = ws.get("bridge_result")
        output = ""
        if br and br.get("status") == "success":
            output = br.get("data", {}).get("output", "")
        return {
            "summary": f"Workstream: {workstream_id}\nType: {ws['type']}\nStatus: {ws['status']}",
            "details": output or "(no output yet — workstream may still be running)",
            "epistemic_status": f"Status: {ws['status']}",
        }

    def _user_utterances(self) -> list[str]:
        """Return non-empty user turns from dialogue_history, in order."""
        utterances: list[str] = []
        for entry in self.dialogue_history:
            if entry.get("role") != "user":
                continue
            content = (entry.get("content") or "").strip()
            if content:
                utterances.append(content)
        return utterances

    def _synthesize_goal(self) -> str:
        """Build a research goal from dialogue_history.

        Deterministic rule-based synthesis (no LLM required) so offline tests
        can assert that user content is reflected in the proposed goal. The
        first user turn is treated as the research question; subsequent turns
        are labeled by the clarification aspect they answer.
        """
        user_turns = self._user_utterances()
        if not user_turns:
            return _DEFAULT_GOAL

        question = user_turns[0].rstrip(".!? ").strip()
        if not question:
            return _DEFAULT_GOAL

        header = f'To investigate the question: "{question}".'

        aspect_parts: list[str] = []
        for idx, turn in enumerate(user_turns[1:]):
            cleaned = turn.rstrip().strip()
            if not cleaned:
                continue
            if idx < len(_GOAL_ASPECT_LABELS):
                label = _GOAL_ASPECT_LABELS[idx]
            else:
                label = f"further guidance ({idx - len(_GOAL_ASPECT_LABELS) + 1})"
            aspect_parts.append(f"{label}: {cleaned}")

        if aspect_parts:
            context = " Constraints and context from dialogue — " + "; ".join(aspect_parts) + "."
        else:
            context = ""

        return f"{header}{context} {_GOAL_DELIVERABLE}"

    def get_dialogue_state(self) -> str:
        if self._goal_approved:
            return "goal_approved"
        elif self._goal_proposed:
            return "goal_proposed"
        elif self._turn_count == 0:
            return "awaiting_question"
        return "clarifying"

    # ── State persistence ────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        """Return a JSON-serialisable snapshot of coordinator state."""
        return {
            "turn_count": self._turn_count,
            "goal_proposed": self._goal_proposed,
            "goal_approved": self._goal_approved,
            "dialogue_history": self.dialogue_history,
            "active_workstreams": {
                wid: {"type": ws["type"], "status": ws["status"], "goal": ws.get("goal")}
                for wid, ws in self.active_workstreams.items()
            },
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore coordinator state from a previously saved snapshot."""
        if not state:
            return
        self._turn_count = int(state.get("turn_count", 0))
        self._goal_proposed = state.get("goal_proposed") or None
        self._goal_approved = bool(state.get("goal_approved", False))
        self.dialogue_history = state.get("dialogue_history") or []
        saved_ws = state.get("active_workstreams") or {}
        for wid, ws in saved_ws.items():
            self.active_workstreams[wid] = {
                "workstream_id": wid,
                "type": ws.get("type", ""),
                "status": ws.get("status", "running"),
                "goal": ws.get("goal", ""),
            }
