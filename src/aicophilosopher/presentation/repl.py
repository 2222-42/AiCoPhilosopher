"""Console Agent REPL main loop (002-console-agent)."""

from __future__ import annotations

import re
from collections.abc import Callable
from queue import Queue
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

# Map NLU intent types to coordinator.run(…) command vocabulary.
# The coordinator only recognises a small set of commands (see
# ProjectCoordinatorAgent.run); other intents fall through to the
# default _start_dialogue branch.
INTENT_TO_COMMAND: dict[str, str] = {
    "start_inquiry": "start",
    "clarify_question": "refine_goal",
    "propose_workstream": "propose_workstream",
    "steer_workstream": "steer",
    "request_status": "status",
    "request_detail": "start",       # fall through to dialogue
    "request_export": "start",       # export handled via StoragePort later
    "approve_action": "approve_goal",
    "reject_action": "start",        # rejection routes to dialogue
    "ask_question": "start",
    "inject_information": "start",   # PDF ingestion via separate pipeline
    "request_help": "start",
    "pause_session": "start",
    "resume_session": "start",
    "archive_project": "start",
    "compare_traditions": "propose_workstream",
}


def _translate_intent(intent_type: str) -> str:
    """Translate an NLU intent value into a coordinator command name."""
    return INTENT_TO_COMMAND.get(intent_type, "start")


# ── Fast-path keyword detection ────────────────────────────────────────

# Only trigger workstream launch when the input starts with or
# primarily consists of these launch patterns.
_WORKSTREAM_LAUNCH_PATTERNS: list[tuple[str, str]] = [
    (r"\bstart\b.*\b(literature|search)\b", "literature_search"),
    (r"\bsearch\b.*\b(for|papers?|literature)\b", "literature_search"),
    (r"\bliterature\b.*\b(search|review)\b", "literature_search"),
    (r"\bdo\b.*\b(literature|search)\b", "literature_search"),
    (r"\banaly(sis|ze)\b.*\b(concept|this|that|idea)\b", "concept_analysis"),
    (r"\bconcept\b.*\banalysis\b", "concept_analysis"),
    (r"\b(argue|argument|construct).*\b", "argumentation"),
    (r"\bcompar(e|ison|ing)\b.*\b(tradition|cross)\b", "cross_traditional_comparison"),
    (r"\bcross.traditional\b", "cross_traditional_comparison"),
    (r"\breview\b.*\b(argument|workstream|finding)\b", "critical_review"),
    (r"\bsynthes(is|ize)\b", "synthesis"),
]


def _detect_workstream_launch(text: str) -> str | None:
    """If text matches a workstream launch pattern, return the type. Else None."""
    lower = text.lower()
    for pattern, ws_type in _WORKSTREAM_LAUNCH_PATTERNS:
        if re.search(pattern, lower):
            return ws_type
    return None


async def _process_slash_command(
    stripped: str,
    session: SessionState,
    coordinator: Any,
) -> dict[str, Any]:
    """Handle slash commands (/status, /logs, /exit, …)."""
    cmd = stripped.strip().lower()

    # Route /status to coordinator for rich status display
    if cmd == "/status":
        try:
            status_response = await coordinator.run(command="status")
            render_response(status_response, session.current_focus)
            return status_response
        except Exception:
            # Fallback: show minimal session-based status
            render_response({
                "summary": (
                    f"Project: {session.project_id}\n"
                    f"Status: {session.status.value}\n"
                    f"Active workstreams: {len(session.active_workstreams)}"
                ),
            }, session.current_focus)
            return {"summary": f"Project: {session.project_id} — {session.status.value}"}

    # /logs [workstream_id] — view workstream output
    if cmd.startswith("/logs"):
        parts = stripped.strip().split(maxsplit=1)
        ws_id = parts[1] if len(parts) > 1 else ""
        try:
            log_response = await coordinator.run(command="logs", workstream_id=ws_id)
            render_response(log_response, session.current_focus)
            return log_response
        except Exception:
            render_response({"error": "Could not fetch workstream logs."}, session.current_focus)
            return {"error": "Could not fetch workstream logs."}

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


async def _process_natural_language(
    stripped: str,
    session: SessionState,
    coordinator: Any,
    llm_port: Any,
    test_mode: bool,
) -> dict[str, Any]:
    """Route natural-language input via fast-path keywords or NLU."""
    if test_mode:
        # Skip LLM in test_mode — use mock coordinator directly
        return await coordinator.run(user_input=stripped)

    # Fast-path: explicit keywords bypass NLU entirely
    lower = stripped.lower().strip().rstrip(".!?")

    # Approve / reject
    if lower in ("yes", "y", "go ahead", "sure", "approved", "approve",
                  "はい", "いい", "いいよ", "ok", "okay", "proceed"):
        return await coordinator.run(user_input=stripped, command="approve_goal")
    if lower in ("no", "n", "stop", "don't", "not yet", "cancel",
                    "いいえ", "やめ", "だめ"):
        return await coordinator.run(user_input=stripped, command="start")

    # Workstream launch — detect type from keywords
    if (ws_type := _detect_workstream_launch(lower)) is not None:
        return await coordinator.run(
            user_input=stripped,
            command="propose_workstream",
            workstream_type=ws_type,
        )

    intent = await classify_intent(stripped, session.current_focus, llm_port)
    command = _translate_intent(intent.intent_type.value if intent else "start_inquiry")
    return await coordinator.run(
        user_input=stripped,
        command=command,
    )


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
        return await _process_slash_command(stripped, session, coordinator)

    response = await _process_natural_language(
        stripped, session, coordinator, llm_port, test_mode
    )
    render_response(response, session.current_focus)
    return response


# ── Session lifecycle ────────────────────────────────────────────────────


async def _finalize(session: SessionState, reason: str, storage: Any = None) -> None:
    """Mark session as paused and persist state before finalizing."""
    session.status = SessionStatus.PAUSED
    session.exit_reason = reason
    try:
        from aicophilosopher.presentation.session_manager import SessionManager

        sm = SessionManager(storage=storage)
        # Persist full session state (including config_snapshot) BEFORE finalizing
        await sm.save_session(session)
        await sm.finalize_session(str(session.session_id), reason)
    except (ImportError, AttributeError):
        pass  # SessionManager not yet wired


async def _reactivate_session(sm: Any, session: SessionState) -> SessionState:
    """Mark a loaded session active under the current process and re-persist."""
    import os
    from datetime import UTC, datetime

    session.status = SessionStatus.ACTIVE
    session.pid = os.getpid()
    now = datetime.now(UTC)
    session.heartbeat_at = now
    session.last_active_at = now
    session.exit_reason = None
    try:
        await sm.save_session(session)
    except (AttributeError, TypeError):
        pass
    return session


async def _startup_flow(  # noqa: C901
    project_id: str | None = None,
    test_mode: bool = False,
    storage: Any = None,
) -> SessionState | None:
    if test_mode:
        return SessionState(project_id=project_id or "test-proj")

    try:
        from aicophilosopher.presentation.session_manager import SessionManager
    except ImportError:
        return None

    sm = SessionManager(storage=storage)

    # Reclaim stale sessions
    try:
        reclaimed = await sm.reclaim_stale_sessions()
        if reclaimed > 0:
            print(f"[System] Reclaimed {reclaimed} stale session(s).")
    except (AttributeError, NotImplementedError):
        pass

    if project_id:
        session = await sm.load_session(project_id)
        if session:
            if session.status == SessionStatus.ACTIVE:
                live = await sm.is_active_session_live(session.pid)
                if live:
                    print("Warning: Another active session exists for this project.")
                    return None
            return await _reactivate_session(sm, session)
        return await sm.create_session(project_id)

    projects = await sm.list_projects()
    if not projects:
        return None

    for p in projects:
        if p.get("session_status") == "paused":
            session = await sm.load_session(str(p["project_id"]))
            if session:
                return await _reactivate_session(sm, session)

    return None


# ── Workstream status poller ─────────────────────────────────────────────


class WorkstreamPoller:
    """Background thread that polls workstream status and queues changes.

    Accepts a callable ``poll_fn`` that returns ``list[dict]`` where each
    dict has at least ``workstream_id`` and ``status`` keys.  This keeps
    the poller decoupled from the StoragePort contract; the REPL loop
    provides a closure that calls the appropriate backend adapter.

    Detects status transitions (running → completed / failed / stalled)
    and pushes dict records
    (``{\"workstream_id\", \"old_status\", \"new_status\"}``) into the
    shared ``update_queue`` for the REPL loop to surface after the
    current turn completes.
    """

    def __init__(
        self,
        poll_fn: Callable[[], list[dict[str, object]]],
        update_queue: Queue[dict[str, object]],
        interval_seconds: float = 2.0,
    ) -> None:
        import threading

        self._poll_fn = poll_fn
        self._queue: Queue[dict[str, object]] = update_queue
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_known: dict[str, str] | None = None

    def start(self) -> None:
        import threading

        if self._thread is not None:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join(timeout=5.0)
        self._thread = None
        self._last_known = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run_loop(self) -> None:
        """Loop: poll, sleep, repeat until stopped."""

        while not self._stop_event.is_set():
            try:
                self._poll_sync()
            except Exception:
                # Log + swallow; the poller must not crash the REPL.
                pass
            self._stop_event.wait(self._interval)

    def _poll_sync(self) -> None:
        """Single poll cycle: call poll_fn, detect transitions, push to queue.

        ``poll_fn()`` MUST be synchronous and return ``list[dict]``.
        """
        import logging

        _logger = logging.getLogger(__name__)

        try:
            workstreams = self._poll_fn()
        except Exception:
            _logger.debug("WorkstreamPoller: poll_fn raised, retrying next cycle", exc_info=True)
            return

        if not isinstance(workstreams, list):
            return

        current: dict[str, str] = {}
        for ws in workstreams:
            wid = str(ws.get("workstream_id", ""))
            status = str(ws.get("status", "unknown"))
            if wid:
                current[wid] = status

        # First poll: initialise baseline without queuing any changes.
        if self._last_known is None:
            self._last_known = current
            return

        # Detect transitions
        all_ids = set(self._last_known) | set(current)
        for wid in sorted(all_ids):  # deterministic ordering
            old = self._last_known.get(wid)
            new = current.get(wid)
            if old != new:
                self._queue.put({
                    "workstream_id": wid,
                    "old_status": old or "(none)",
                    "new_status": new or "(removed)",
                })

        self._last_known = current


# ── Main REPL entry point ────────────────────────────────────────────────


def _save_coordinator_state(session: SessionState, coordinator: Any) -> None:
    """Persist coordinator state into the session snapshot for resume."""
    try:
        state = coordinator.get_state()
    except (AttributeError, TypeError):
        return
    if session.config_snapshot is None:
        session.config_snapshot = {}
    session.config_snapshot["coordinator_state"] = state


def _mock_test_backends(coordinator: Any, llm_port: Any) -> tuple[Any, Any]:
    """Provide mock coordinator/LLM for --test-mode when not injected."""
    from unittest.mock import AsyncMock, MagicMock

    if coordinator is None:
        coordinator = MagicMock()
        coordinator.run = AsyncMock(
            return_value={
                "message": "Welcome to test mode! Try typing a philosophical question.",
                "dialogue_state": "awaiting_question",
                "turn": 0,
            }
        )
    if llm_port is None:
        llm_port = MagicMock()
    return coordinator, llm_port


def _restore_coordinator_state(session: SessionState, coordinator: Any) -> None:
    """Best-effort restore of coordinator state from a previous session."""
    saved_state = (
        session.config_snapshot.get("coordinator_state") if session.config_snapshot else None
    )
    if not saved_state:
        return
    try:
        coordinator.restore_state(saved_state)
        state = coordinator.get_dialogue_state()
        turn = saved_state.get("turn_count", 0)
        goal = saved_state.get("goal_proposed", "")
        goal_ok = saved_state.get("goal_approved", False)

        if turn > 0:
            print(f"\n[Session resumed — turn {turn}, state: {state}]")
            if goal_ok:
                print(f"Approved goal: {goal}")
            elif goal:
                print(f"Proposed goal: {goal}")
            print()
    except Exception:
        pass  # best-effort restore


async def run_repl(
    project_id: str | None = None,
    test_mode: bool = False,
    llm_port: Any = None,
    coordinator: Any = None,
    storage: Any = None,
) -> None:
    session = await _startup_flow(project_id=project_id, test_mode=test_mode, storage=storage)
    if session is None:
        if test_mode:
            return
        print("No projects found. Start a new project first.")
        return

    if test_mode:
        coordinator, llm_port = _mock_test_backends(coordinator, llm_port)

    # ── Production mode ──────────────────────────────────────────────
    if coordinator is None or llm_port is None:
        print(
            "REPL backend not fully configured.\n"
            "Launch with --test-mode for a mock session, or provide\n"
            "a coordinator and LLM port via the Hermes Agent integration."
        )
        return

    _restore_coordinator_state(session, coordinator)

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
            _save_coordinator_state(session, coordinator)
            await _finalize(session, "user_interrupt", storage)
            print("\nSession saved. Goodbye!")
            break

        result = await _process_input(
            user_input, session, coordinator, llm_port, test_mode=False
        )
        if result and result.get("action") == "exit":
            _save_coordinator_state(session, coordinator)
            await _finalize(session, "user_exit", storage)
            print(result.get("message", "Goodbye!"))
            break
