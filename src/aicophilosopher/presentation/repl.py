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


# ── Coordinator adapter (T-025) ──────────────────────────────────────


async def _route_to_coordinator(
    intent_type: str,
    user_input: str,
    coordinator: Any,
    session: SessionState,
) -> dict[str, Any]:
    """Map intent types to coordinator.run() commands."""
    command_map = {
        "start_inquiry": "start",
        "clarify_question": "refine_goal",
        "propose_workstream": "propose_workstream",
        "approve_action": "approve_goal",
        "steer_workstream": "steer",
        "request_status": "status",
    }
    command = command_map.get(intent_type, "start")
    return await coordinator.run(user_input=user_input, command=command)


# ── Workstream poller (T-027) ─────────────────────────────────────────


class WorkstreamPoller:
    """Background thread that polls workstream status."""

    def __init__(self, session_id: str, storage: Any = None) -> None:
        self.session_id = session_id
        self.storage = storage
        self._updates: list[dict[str, Any]] = []

    def start(self) -> None:
        pass  # Stub — full impl with threading in T-027

    def stop(self) -> None:
        pass

    def flush(self) -> list[dict[str, Any]]:
        updates = list(self._updates)
        self._updates.clear()
        return updates


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

    # Reclaim stale sessions before listing
    reclaimed = await sm.reclaim_stale_sessions()
    if reclaimed > 0:
        print(f"[System] Reclaimed {reclaimed} stale session(s).")

    if project_id:
        session = await sm.load_session(project_id)
        if session:
            # Concurrent session check
            if session.status == SessionStatus.ACTIVE:
                live = await sm.is_active_session_live(session.pid)
                if live:
                    print("Warning: Another active session exists for this project.")
                    print("Opening in read-only mode is not yet supported.")
                    return None
            session.status = SessionStatus.ACTIVE
            return session
        return await sm.create_session(project_id)

    projects = await sm.list_projects()
    if not projects:
        return None

    # Auto-resume first paused project (non-interactive mode)
    for p in projects:
        if p.get("session_status") == "paused":
            session = await sm.load_session(p["project_id"])
            if session:
                session.status = SessionStatus.ACTIVE
                return session

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
