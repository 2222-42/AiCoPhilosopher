"""Console Agent REPL main loop (002-console-agent)."""

from __future__ import annotations

from typing import Any

from aicophilosopher.domain.entities.session import SessionState, SessionStatus
from aicophilosopher.presentation.nlu import classify_intent
from aicophilosopher.presentation.rendering import render_response

# ── Slash command handler (inline — full registry in T-020) ─────────────


def _handle_slash(command: str, session: SessionState) -> dict[str, Any]:
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

    if cmd == "/status":
        return {
            "summary": f"Project: {session.project_id} — {session.status.value}",
            "active_workstreams": [
                f"{ws} — (tracked)" for ws in session.active_workstreams
            ],
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
    llm_port: Any,
    test_mode: bool = False,
) -> dict[str, Any] | None:
    stripped = user_input.strip()
    if not stripped:
        return None

    if stripped.startswith("/"):
        slash_result = _handle_slash(stripped, session)
        # Delegate to full command registry if available
        if slash_result.get("message", "").startswith("Unknown command"):
            try:
                from aicophilosopher.presentation.slash_commands import dispatch

                slash_result = dispatch(stripped, session)
            except ImportError:
                pass
        if slash_result.get("action") == "exit":
            await _finalize(session, "user_exit")
            return slash_result
        render_response(slash_result, session.current_focus)
        return slash_result

    # Natural language → NLU → coordinator
    if test_mode:
        # Skip LLM in test_mode — use mock coordinator directly
        response = await coordinator.run(user_input=stripped)
    else:
        intent = await classify_intent(stripped, session.current_focus, llm_port)
        response = await coordinator.run(
            user_input=stripped,
            command=intent.intent_type.value if intent else "start",
        )

    render_response(response, session.current_focus)
    return response


# ── Session lifecycle ────────────────────────────────────────────────────


async def _finalize(session: SessionState, reason: str) -> None:
    """Mark session as paused and attempt persistence."""
    session.status = SessionStatus.PAUSED
    session.exit_reason = reason
    try:
        from aicophilosopher.presentation.session_manager import SessionManager

        await SessionManager().finalize_session(str(session.session_id), reason)
    except (ImportError, AttributeError):
        pass  # SessionManager not yet wired (T-016)


async def _startup_flow(  # noqa: C901
    project_id: str | None = None,
    test_mode: bool = False,
) -> SessionState | None:
    if test_mode:
        return SessionState(project_id=project_id or "test-proj")

    try:
        from aicophilosopher.presentation.session_manager import SessionManager
    except ImportError:
        return None

    sm = SessionManager()

    # Reclaim stale sessions
    try:
        reclaimed = await sm.reclaim_stale_sessions()  # type: ignore[attr-defined]
        if reclaimed > 0:
            print(f"[System] Reclaimed {reclaimed} stale session(s).")
    except (AttributeError, NotImplementedError):
        pass

    if project_id:
        session = await sm.load_session(project_id)  # type: ignore[attr-defined]
        if session:
            if session.status == SessionStatus.ACTIVE:
                live = await sm.is_active_session_live(session.pid)  # type: ignore[attr-defined]
                if live:
                    print("Warning: Another active session exists for this project.")
                    return None
            session.status = SessionStatus.ACTIVE
            return session
        return await sm.create_session(project_id)  # type: ignore[attr-defined]

    projects = await sm.list_projects()  # type: ignore[attr-defined]
    if not projects:
        return None

    for p in projects:
        if p.get("session_status") == "paused":
            session = await sm.load_session(p["project_id"])  # type: ignore[attr-defined]
            if session:
                session.status = SessionStatus.ACTIVE  # ← fix: reactivate on resume
                return session

    return None


# ── Main REPL entry point ────────────────────────────────────────────────


async def run_repl(
    project_id: str | None = None,
    test_mode: bool = False,
    llm_port: Any = None,
    coordinator: Any = None,
) -> None:
    session = await _startup_flow(project_id=project_id, test_mode=test_mode)
    if session is None:
        if test_mode:
            return
        print("No projects found. Start a new project first.")
        return

    if test_mode:
        if coordinator is None:
            from unittest.mock import AsyncMock, MagicMock

            coordinator = MagicMock()
            coordinator.run = AsyncMock(
                return_value={
                    "message": "Welcome!",
                    "dialogue_state": "awaiting_question",
                    "turn": 0,
                }
            )
        if llm_port is None:
            from unittest.mock import MagicMock

            llm_port = MagicMock()
        return  # tests drive via _process_input directly

    if llm_port is None or coordinator is None:
        raise RuntimeError(
            "llm_port and coordinator are required in production mode. "
            "Use --test-mode for testing without real backends."
        )

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
