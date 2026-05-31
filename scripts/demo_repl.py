#!/usr/bin/env python3
"""Interactive REPL demo with a mock coordinator — no LLM required.

Usage:
    cd aicophilosopher && source .venv/bin/activate
    python scripts/demo_repl.py
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from aicophilosopher.domain.entities.session import SessionState
from aicophilosopher.presentation.rendering import render_response

# ── Mock coordinator with pre-scripted Socratic dialogue ────────────────

_dialogue_state = 0
_socratic_responses = [
    {
        "summary": "Welcome! I'm your philosophical co-investigator. What question would you like to explore?",
        "epistemic_status": "No hypotheses yet — awaiting your inquiry.",
        "dialogue_state": "awaiting_question",
        "turn": 0,
    },
    {
        "summary": "That's a rich question. To help me frame the inquiry: which philosophical tradition or methodological angle interests you most? For example, analytic, continental, phenomenological, philosophy of technology?",
        "epistemic_status": "Active hypotheses: 0 | Confidence: clarifying",
        "dialogue_state": "clarifying",
        "turn": 1,
    },
    {
        "summary": "Good. One more clarification — are there specific thinkers or texts you'd like me to engage with, or should I cast a wide net first?",
        "epistemic_status": "Active hypotheses: 0 | Tradition: being refined",
        "dialogue_state": "clarifying",
        "turn": 2,
    },
    {
        "summary": "Based on our discussion, I propose this refined research goal:\n\n**Explore whether agency requires libertarian free will, or if compatibilist accounts suffice, drawing on analytic action theory and phenomenology of embodied choice.**\n\nWould you like to approve this goal?",
        "epistemic_status": "Active hypotheses: 1 proposed | Confidence: 0.75",
        "active_workstreams": [],
        "dialogue_state": "goal_proposed",
        "is_approval_request": True,
        "approval_options": [
            "Yes, approve and start workstreams",
            "No, let's refine further",
            "Change the angle to focus on phenomenology only",
        ],
        "turn": 3,
    },
    {
        "summary": "Goal approved! I'll now launch parallel workstreams:\n\n• Literature Search — finding papers on agency + free will (2000-2024)\n• Concept Analysis — clarifying 'agency', 'autonomy', 'free will'\n• Argumentation — reconstructing compatibilist vs incompatibilist positions\n\nType /status to track progress, or continue the dialogue.",
        "epistemic_status": "Active hypotheses: 1 | Confidence: 0.80 | Review: in progress",
        "active_workstreams": [
            "WS-001: Literature Search — running",
            "WS-002: Concept Analysis — running",
            "WS-003: Argumentation — pending",
        ],
        "dialogue_state": "workstreams_launched",
        "turn": 4,
    },
]


def _mock_coordinator():
    coord = MagicMock()

    async def _run(user_input: str = "", **kwargs: object) -> dict:
        global _dialogue_state
        cmd = str(kwargs.get("command", ""))
        if cmd == "status":
            return {
                "summary": "Status: 3 workstreams active. 1 hypothesis under review.",
                "epistemic_status": "Active: 1 | Under review: 1",
                "active_workstreams": [
                    "WS-001: Literature Search — 60% complete",
                    "WS-002: Concept Analysis — 30% complete",
                    "WS-003: Argumentation — pending",
                ],
                "dialogue_state": "workstreams_launched",
            }
        resp = _socratic_responses[min(_dialogue_state, len(_socratic_responses) - 1)]
        if "goal" not in user_input.lower() or _dialogue_state < 3:
            _dialogue_state += 1
        return {**resp}

    coord.run = AsyncMock(side_effect=_run)
    return coord


# ── Main loop ──────────────────────────────────────────────────────────


async def main() -> None:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory

    session = SessionState(project_id="demo-project")
    coordinator = _mock_coordinator()
    llm_port = MagicMock()

    prompt_session = PromptSession(history=FileHistory(".aicophilosopher_demo_history"))
    print("═" * 60)
    print("  AI Co-Philosopher — Interactive Demo")
    print("  (mock coordinator, no LLM required)")
    print("═" * 60)
    print()
    print("Type a philosophical question to begin the Socratic dialogue.")
    print("Try: /help, /status, /details, /exit")
    print()

    # Show welcome
    resp = await coordinator.run(user_input="")
    render_response(resp, session.current_focus)

    while True:
        try:
            user_input = await prompt_session.prompt_async("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended. Goodbye!")
            break

        stripped = user_input.strip()
        if not stripped:
            continue

        if stripped == "/exit":
            print("Session saved. Goodbye!")
            break

        if stripped == "/help":
            print("Commands: /exit, /status, /details, /hide-details, /suggestions, /hide-suggestions")
            print("Or just type a philosophical question!\n")
            continue

        if stripped == "/status":
            resp = await coordinator.run(command="status")
            render_response(resp, session.current_focus)
            continue

        if stripped == "/details":
            session.current_focus.toggle_state.show_details = True
            print("[Details] section enabled.")
            continue

        if stripped == "/hide-details":
            session.current_focus.toggle_state.show_details = False
            print("[Details] section hidden.")
            continue

        if stripped == "/suggestions":
            session.current_focus.toggle_state.show_suggestions = True
            print("[Suggestions] section enabled.")
            continue

        if stripped == "/hide-suggestions":
            session.current_focus.toggle_state.show_suggestions = False
            print("[Suggestions] section hidden.")
            continue

        # Natural language → coordinator
        resp = await coordinator.run(user_input=stripped)
        render_response(resp, session.current_focus)


if __name__ == "__main__":
    asyncio.run(main())
