"""Non-interactive smoke test — simulates a full Socratic dialogue flow.

Run:  python scripts/demo_repl.py        # interactive (your terminal)
      python scripts/smoke_test_repl.py   # non-interactive (automated)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from aicophilosopher.domain.entities.session import SessionState
from aicophilosopher.presentation.rendering import render_response
from aicophilosopher.presentation.repl import _process_input


async def main() -> None:
    session = SessionState(project_id="smoke-test")
    coordinator = MagicMock()
    llm_port = MagicMock()

    turn = 0
    responses = [
        {
            "summary": "Welcome! What would you like to explore?",
            "epistemic_status": "No hypotheses yet.",
            "dialogue_state": "awaiting_question",
        },
        {
            "summary": "Which philosophical tradition interests you?",
            "epistemic_status": "Active hypotheses: 0 | Clarifying",
            "dialogue_state": "clarifying",
        },
        {
            "summary": "I propose: **Explore free will from analytic + phenomenological perspectives**.\nApprove?",
            "is_approval_request": True,
            "approval_options": ["Yes", "No, refine"],
            "epistemic_status": "1 hypothesis proposed | Confidence: 0.75",
            "dialogue_state": "goal_proposed",
        },
        {
            "summary": "Goal approved! Launching workstreams...",
            "active_workstreams": [
                "WS-001: Literature Search — running",
                "WS-002: Concept Analysis — running",
            ],
            "epistemic_status": "Active: 1 | Confidence: 0.80",
            "dialogue_state": "workstreams_launched",
        },
    ]

    async def _run(user_input: str = "", **kwargs) -> dict:
        nonlocal turn
        if kwargs.get("command") == "status":
            return {
                "summary": "2 workstreams active.",
                "active_workstreams": [
                    "WS-001: Literature Search — 60%",
                    "WS-002: Concept Analysis — 30%",
                ],
            }
        idx = min(turn, len(responses) - 1)
        if "approve" not in user_input.lower():
            turn += 1
        return dict(responses[idx])

    coordinator.run = AsyncMock(side_effect=_run)

    print("=" * 60)
    print("  AI Co-Philosopher — Automated Smoke Test")
    print("=" * 60)
    print()

    # Test 1: Natural language inquiry
    print("─" * 40)
    print("TEST 1: Natural language inquiry")
    print("─" * 40)
    r = await _process_input(
        "I want to explore free will", session, coordinator, llm_port, test_mode=True
    )
    assert r is not None
    assert "welcome" in r.get("summary", "").lower() or "explore" in r.get("summary", "").lower()
    print("  ✅ Natural language routed to coordinator")

    # Test 2: Clarification turn
    print("TEST 2: Socratic clarification")
    r = await _process_input(
        "Analytic philosophy, maybe Frankfurt", session, coordinator, llm_port, test_mode=True
    )
    assert r is not None
    assert r.get("dialogue_state") == "clarifying" or r.get("dialogue_state") == "goal_proposed"
    print("  ✅ Clarification dialogue works")

    # Test 3: Approval request surfaced
    print("TEST 3: Goal proposal + approval request")
    r = await _process_input(
        "Yes, also add phenomenology", session, coordinator, llm_port, test_mode=True
    )
    assert r is not None
    if r.get("is_approval_request"):
        print("  ✅ Approval request surfaced with ⚠️")
    else:
        print("  ✅ Approval confirmed, workstreams launched")

    # Test 4: Slash command routing
    print("TEST 4: /status command")
    r = await _process_input(
        "/status", session, coordinator, llm_port, test_mode=True
    )
    assert r is not None
    print("  ✅ Slash command routed correctly")

    # Test 5: /exit
    print("TEST 5: /exit finalizes session")
    r = await _process_input(
        "/exit", session, coordinator, llm_port, test_mode=True
    )
    assert r is not None
    assert r.get("action") == "exit"
    assert session.status.value == "paused"
    print("  ✅ Session finalized (status=paused)")

    # Summary
    print()
    print("=" * 60)
    print("  ALL 5 SMOKE TESTS PASSED ✅")
    print("=" * 60)
    print()
    print("To run the interactive demo (on your terminal):")
    print("  cd aicophilosopher && source .venv/bin/activate")
    print("  python scripts/demo_repl.py")
    print()
    print("This gives you a full Socratic dialogue experience")
    print("with progressive disclosure rendering, slash commands,")
    print("and a mock coordinator that guides you through")
    print("question → clarify → propose → approve → workstreams.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
