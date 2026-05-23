"""Console Agent REPL main loop (002-console-agent).

Provides run_repl() entry point and internal helpers for
input processing, slash command handling, and session lifecycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aicophilosopher.domain.entities.session import SessionState, SessionStatus
from aicophilosopher.presentation.nlu import classify_intent
from aicophilosopher.presentation.rendering import render_response

# Sentinel for SessionManager (T-016) — patched in tests
SessionManager: Any = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from aicophilosopher.ports.llm_port import LLMPort

# ── Slash command handler (inline — full registry in T-020) ──────────────


def _handle_slash(command: str, session: SessionState) -> dict[str, Any]:
    """Handle essential slash commands for US1.

    Full 28-command registry replaces this in Phase 5 (T-020).
    """
    cmd = command.strip().lower()

    if cmd == "/exit":
        return {"action": "exit", "message": "Goodbye!"}

    if cmd == "/help":
        return {
            "message": "Available commands:\n"
            "  /exit, /help, /status\n"
            "  /details, /hide-details\n"
            "  /suggestions, /hide-suggestions\n"
            "\nUse natural language for philosophical inquiry."
        }

    if cmd == "/details":
        session.current_focus.toggle_state.show_details = True
        return {"message": "[Details] section enabled."}

    if cmd == "/hide-details":
        session.current_focus.toggle_state.show_details = False
        return {"message": "[Details] section hidden."}

    if cmd == "/suggestions":
        session.current_focus.toggle_state.show_suggestions = True
        return {"message": "[Suggestions] section enabled."}

    if cmd == "/hide-suggestions":
        session.current_focus.toggle_state.show_suggestions = False
        return {"message": "[Suggestions] section hidden."}

    return {"message": f"Unknown command: '{command}'. Type /help for available commands."}


# ── Input processing ─────────────────────────────────────────────────────


async def _process_input(
    user_input: str,
    session: SessionState,
    coordinator: Any,
    llm_port: LLMPort,
    test_mode: bool = False,
) -> dict[str, Any] | None:
    """Process a single user input line through NLU or slash dispatch."""
    stripped = user_input.strip()

    if not stripped:
        return None

    # Slash command dispatch
    if stripped.startswith("/"):
        slash_result = _handle_slash(stripped, session)
        if slash_result.get("action") == "exit":
            await _finalize(session, "user_exit")
            return slash_result
        # Render slash result
        render_response(slash_result, session.current_focus)
        return slash_result

    # Natural language → NLU → coordinator
    await classify_intent(stripped, session.current_focus, llm_port)
    if test_mode and hasattr(coordinator, "run"):
        response = await coordinator.run(user_input=stripped)
    else:
        response = await coordinator.run(user_input=stripped)

    render_response(response, session.current_focus)
    return response


# ── Session lifecycle ────────────────────────────────────────────────────


async def _finalize(session: SessionState, reason: str) -> None:
    """Mark session as paused and record exit reason."""
    session.status = SessionStatus.PAUSED
    session.exit_reason = reason


async def _startup_flow(
    project_id: str | None = None,
    test_mode: bool = False,
) -> SessionState | None:
    """Determine project, create/load session, return SessionState.

    In test_mode, creates a fresh session bypassing SessionManager.
    """
    if test_mode:
        return SessionState(project_id=project_id or "test-proj")

    from aicophilosopher.presentation.session_manager import SessionManager

    sm = SessionManager()
    if project_id:
        session = await sm.load_session(project_id)
        if session:
            session.status = SessionStatus.ACTIVE
            return session
        return await sm.create_session(project_id)

    projects = await sm.list_projects()
    if not projects:
        return None  # No projects yet — caller prompts user

    # In non-interactive mode, pick first paused project
    for p in projects:
        if p.get("session_status") == "paused":
            return await sm.load_session(p["project_id"])

    return None


# ── Main REPL entry point ────────────────────────────────────────────────


async def run_repl(
    project_id: str | None = None,
    test_mode: bool = False,
    llm_port: LLMPort | None = None,
    coordinator: Any = None,
) -> None:
    """Launch the Console Agent REPL.

    Uses prompt_toolkit for interactive input in production mode.
    In test_mode, skips prompt_toolkit and uses mock coordinator.
    """
    session = await _startup_flow(project_id=project_id, test_mode=test_mode)
    if session is None:
        print("No projects found. Start a new project first.")
        return

    if test_mode:
        # Simple REPL loop for testing
        if coordinator is None:
            from unittest.mock import AsyncMock, MagicMock
            coordinator = MagicMock()
            coordinator.run = AsyncMock(
                return_value={
                    "message": "Welcome! What philosophical question would you like to explore?",
                    "dialogue_state": "awaiting_question",
                    "turn": 0,
                }
            )
        if llm_port is None:
            from unittest.mock import MagicMock
            llm_port = MagicMock()

        print(f"Session started for project: {session.project_id}")
        return  # Test mode — tests drive the loop via _process_input directly
    else:
        # Production mode: prompt_toolkit REPL
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory

        prompt_session = PromptSession(history=FileHistory(".aicophilosopher_history"))
        print("Welcome to AiCoPhilosopher — your philosophical research collaborator.")
        print(f"Project: {session.project_id}")
        print("Type a philosophical question to begin, or /help for commands.\n")

        while True:
            try:
                user_input = await prompt_session.prompt_async("> ")
            except (EOFError, KeyboardInterrupt):
                await _finalize(session, "user_interrupt")
                print("\nSession saved. Goodbye!")
                break

            result = await _process_input(
                user_input, session, coordinator, llm_port, test_mode=False
            )
            if result and result.get("action") == "exit":
                print(result.get("message", "Goodbye!"))
                break
