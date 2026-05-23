"""Slash command parser and router (T-020). Full 28-command registry."""

from __future__ import annotations

from typing import Any

from aicophilosopher.domain.entities.session import SessionState

# ── Command registry ────────────────────────────────────────────────────

COMMANDS: dict[str, dict[str, Any]] = {
    "/help": {"category": "session", "args": 0},
    "/exit": {"category": "session", "args": 0},
    "/quit": {"category": "session", "args": 0},
    "/new": {"category": "session", "args": 1},
    "/open": {"category": "session", "args": 1},
    "/projects": {"category": "session", "args": 0},
    "/archive": {"category": "session", "args": 0},
    "/search": {"category": "inquiry", "args": 1},
    "/analyze": {"category": "inquiry", "args": 1},
    "/argue": {"category": "inquiry", "args": 1},
    "/review": {"category": "inquiry", "args": 0},
    "/compare": {"category": "inquiry", "args": 1},
    "/synthesize": {"category": "inquiry", "args": 0},
    "/pause": {"category": "steering", "args": 0},
    "/resume": {"category": "steering", "args": 0},
    "/steer": {"category": "steering", "args": 2},
    "/deepen": {"category": "steering", "args": 1},
    "/abandon": {"category": "steering", "args": 1},
    "/status": {"category": "view", "args": 0},
    "/hypotheses": {"category": "view", "args": 0},
    "/dead-ends": {"category": "view", "args": 0},
    "/document": {"category": "view", "args": 0},
    "/details": {"category": "view", "args": 0},
    "/hide-details": {"category": "view", "args": 0},
    "/suggestions": {"category": "view", "args": 0},
    "/hide-suggestions": {"category": "view", "args": 0},
    "/export": {"category": "export", "args": 1},
    "/add-note": {"category": "export", "args": 1},
    "/upload": {"category": "export", "args": 1},
    "/help-request": {"category": "config", "args": 0},
    "/config": {"category": "config", "args": 0},
}


def dispatch(command: str, session: SessionState) -> dict[str, Any]:
    """Parse and route a slash command."""

    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    args_str = parts[1] if len(parts) > 1 else ""

    if cmd not in COMMANDS:
        return {"message": f"Unknown command: '{cmd}'. Type /help for available commands."}

    spec = COMMANDS[cmd]

    # Handle toggle commands directly
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

    if cmd == "/exit" or cmd == "/quit":
        return {"action": "exit", "message": "Goodbye!"}

    if cmd == "/help":
        return _help_response()

    if cmd == "/status":
        return {
            "summary": f"Project: {session.project_id} — {session.status.value}",
            "active_workstreams": [
                f"{ws} — (tracked)" for ws in session.active_workstreams
            ],
        }

    # Commands with required args
    if spec["args"] > 0 and not args_str:
        return {"message": f"'{cmd}' requires an argument. Usage: {cmd} <arg>"}

    return {"message": f"Command '{cmd}' acknowledged.", "args": args_str}


def _help_response() -> dict[str, Any]:
    categories: dict[str, list[str]] = {}
    for name, spec in COMMANDS.items():
        categories.setdefault(spec["category"], []).append(name)

    lines = ["Available commands:\n"]
    for cat, cmds in categories.items():
        lines.append(f"  [{cat}]: {', '.join(cmds)}")
    return {"message": "\n".join(lines)}
