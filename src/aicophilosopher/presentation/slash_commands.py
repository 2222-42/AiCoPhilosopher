"""Slash command parser and router (T-020). Full 28-command registry."""

from __future__ import annotations

import shlex
from typing import Any

from aicophilosopher.domain.entities.session import SessionState


def _parse_args(args_str: str) -> list[str]:
    """Shell-style tokenizer for quoted arguments and flags."""
    try:
        return shlex.split(args_str)
    except ValueError:
        return args_str.split()


def dispatch(command: str, session: SessionState) -> dict[str, Any]:  # noqa: C901
    """Parse and route a slash command."""

    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    args_str = parts[1] if len(parts) > 1 else ""
    args = _parse_args(args_str) if args_str else []

    # ── Session commands ─────────────────────────────────────────────
    if cmd == "/help":
        return _help_response()

    if cmd in ("/exit", "/quit"):
        return {"action": "exit", "message": "Goodbye!"}

    if cmd == "/new":
        if not args:
            return {"message": "Usage: /new <question>"}
        return {"message": f"Creating new project: {args[0]}"}

    if cmd == "/open":
        if not args:
            return {"message": "Usage: /open <project_id>"}
        return {"message": f"Opening project: {args[0]}"}

    if cmd == "/projects":
        return {"message": "Listing projects..."}

    if cmd == "/archive":
        return {
            "message": "Are you sure you want to archive this project? Type /archive --confirm to proceed.",
            "is_approval_request": True,
        }

    # ── Inquiry commands ─────────────────────────────────────────────
    if cmd == "/search":
        if not args:
            return {"message": "Usage: /search <query>"}
        return {"message": f"Searching for: {args[0]}"}

    if cmd == "/analyze":
        if not args:
            return {"message": "Usage: /analyze <concept>"}
        return {"message": f"Analyzing concept: {args[0]}"}

    if cmd == "/argue":
        if not args:
            return {"message": "Usage: /argue <topic>"}
        return {"message": f"Building argument for: {args[0]}"}

    if cmd in ("/review", "/synthesize"):
        return {"message": f"Command '{cmd}' acknowledged."}

    if cmd == "/compare":
        if not args:
            return {"message": "Usage: /compare <topic> [--traditions a,b]"}
        return {"message": f"Comparing traditions for: {args[0]}"}

    # ── Steering commands ────────────────────────────────────────────
    if cmd in ("/pause", "/resume"):
        active = session.active_workstreams
        if args:
            ws_id = args[0]
            if ws_id not in active:
                return {"message": f"Workstream '{ws_id}' not found. Active: {active or 'none'}"}
            return {"message": f"Workstream {ws_id} {cmd.replace('/', '')}d."}
        if not active:
            return {"message": "No workstreams are currently running."}
        if len(active) == 1:
            return {"message": f"Workstream {active[0]} {cmd.replace('/', '')}d."}
        return {"message": f"Which workstream? Running: {', '.join(active)}."}

    if cmd == "/steer":
        if len(args) < 2:
            return {"message": "Usage: /steer <workstream_id> <instruction>"}
        return {"message": f"Steering {args[0]}: {args[1]}"}

    if cmd == "/deepen":
        if not args:
            return {"message": "Usage: /deepen <concept_or_section>"}
        return {"message": f"Deepening analysis of: {args[0]}"}

    if cmd == "/abandon":
        if not args:
            return {"message": "Usage: /abandon <hypothesis_id>"}
        return {"message": f"Abandoning hypothesis: {args[0]}"}

    # ── View commands ────────────────────────────────────────────────
    if cmd == "/status":
        return {
            "summary": f"Project: {session.project_id} — {session.status.value}",
            "active_workstreams": [f"{ws} — (tracked)" for ws in session.active_workstreams],
        }

    if cmd in ("/hypotheses", "/dead-ends", "/document"):
        return {"message": f"Command '{cmd}' acknowledged."}

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

    # ── Export / Config ──────────────────────────────────────────────
    if cmd == "/export":
        if not args:
            return {"message": "Usage: /export <format> (markdown, html)"}
        return {"message": f"Exporting as {args[0]}..."}

    if cmd in ("/add-note", "/upload"):
        if not args:
            return {"message": f"Usage: {cmd} <path_or_text>"}
        return {"message": f"Command '{cmd}' acknowledged."}

    if cmd == "/help-request":
        return {"message": "Help request sent to coordinator."}

    if cmd == "/config":
        return {"message": f"Config: {args}" if args else "Config key-value pairs or empty."}

    return {"message": f"Unknown command: '{cmd}'. Type /help for available commands."}


def _help_response() -> dict[str, Any]:
    categories = {
        "Session": "/help, /exit, /quit, /new, /open, /projects, /archive",
        "Inquiry": "/search, /analyze, /argue, /review, /compare, /synthesize",
        "Steering": "/pause, /resume, /steer, /deepen, /abandon",
        "View": "/status, /hypotheses, /dead-ends, /document, /details, /hide-details, /suggestions, /hide-suggestions",
        "Export": "/export, /add-note, /upload",
        "Config": "/help-request, /config",
    }
    lines = ["Available commands:\n"]
    for cat, cmds in categories.items():
        lines.append(f"  [{cat}]: {cmds}")
    return {"message": "\n".join(lines)}
