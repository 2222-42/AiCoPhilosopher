"""Slash command parser and router (T-020). Full 28-command registry.

Commands either:
  - perform real local side effects (toggles, status, exit),
  - return an ``action`` for the REPL to execute via the Coordinator, or
  - return an explicit ``Not implemented`` response (never pretend success).
"""

from __future__ import annotations

import shlex
from typing import Any

from aicophilosopher.domain.entities.session import SessionState

# Inquiry slash → Coordinator workstream type (real path via propose_workstream).
_INQUIRY_WORKSTREAMS: dict[str, str] = {
    "/search": "literature_search",
    "/analyze": "concept_analysis",
    "/argue": "argumentation",
    "/compare": "cross_traditional_comparison",
    "/review": "critical_review",
    "/synthesize": "synthesis",
}

# Commands that require at least one positional argument before dispatch.
_INQUIRY_REQUIRES_ARG: frozenset[str] = frozenset(
    {"/search", "/analyze", "/argue", "/compare"}
)

_USAGE: dict[str, str] = {
    "/new": "Usage: /new <question>",
    "/open": "Usage: /open <project_id>",
    "/search": "Usage: /search <query>",
    "/analyze": "Usage: /analyze <concept>",
    "/argue": "Usage: /argue <topic>",
    "/compare": "Usage: /compare <topic> [--traditions a,b]",
    "/steer": "Usage: /steer <workstream_id> <instruction>",
    "/deepen": "Usage: /deepen <concept_or_section>",
    "/abandon": "Usage: /abandon <hypothesis_id>",
    "/export": "Usage: /export <format> (markdown, html)",
    "/add-note": "Usage: /add-note <path_or_text>",
    "/upload": "Usage: /upload <path_or_text>",
}


def _parse_args(args_str: str) -> list[str]:
    """Shell-style tokenizer for quoted arguments and flags."""
    try:
        return shlex.split(args_str)
    except ValueError:
        return args_str.split()


def _unimplemented(cmd: str, reason: str = "not yet available") -> dict[str, Any]:
    """Honest failure response — never pretends the command succeeded."""
    return {
        "message": (
            f"Not implemented: {cmd} is registered but {reason}. No action was taken."
        ),
        "error": f"Command {cmd} is not implemented",
        "implemented": False,
    }


def dispatch(command: str, session: SessionState) -> dict[str, Any]:  # noqa: C901
    """Parse and route a slash command.

    Returns a response dict.  When ``action`` is ``propose_workstream``, the
    REPL must invoke the Coordinator; local handlers never fake workstream work.
    """

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
            return {"message": _USAGE["/new"]}
        return _unimplemented(
            cmd, "project creation is only available via the CLI (`aicophilosopher --new`)"
        )

    if cmd == "/open":
        if not args:
            return {"message": _USAGE["/open"]}
        return _unimplemented(
            cmd, "project switching is only available via the CLI (`aicophilosopher --project`)"
        )

    if cmd == "/projects":
        return _unimplemented(cmd, "project listing is not yet wired in the REPL")

    if cmd == "/archive":
        return _unimplemented(cmd, "project archival is not yet wired")

    # ── Inquiry commands → Coordinator propose_workstream ────────────
    if cmd in _INQUIRY_WORKSTREAMS:
        if cmd in _INQUIRY_REQUIRES_ARG and not args:
            return {"message": _USAGE[cmd]}
        return {
            "action": "propose_workstream",
            "workstream_type": _INQUIRY_WORKSTREAMS[cmd],
            "user_input": " ".join(args),
        }

    # ── Steering commands ────────────────────────────────────────────
    if cmd in ("/pause", "/resume"):
        # Validate against tracked workstreams, but never pretend control succeeded.
        active = session.active_workstreams
        if args:
            ws_id = args[0]
            if ws_id not in active:
                return {
                    "message": f"Workstream '{ws_id}' not found. Active: {active or 'none'}"
                }
        elif not active:
            return {"message": "No workstreams are currently running."}
        elif len(active) > 1:
            return {"message": f"Which workstream? Running: {', '.join(active)}."}
        return _unimplemented(
            cmd, "workstream pause/resume control is not yet wired (see workstream execution)"
        )

    if cmd == "/steer":
        if len(args) < 2:
            return {"message": _USAGE["/steer"]}
        return _unimplemented(cmd, "workstream steering is not yet wired")

    if cmd == "/deepen":
        if not args:
            return {"message": _USAGE["/deepen"]}
        return _unimplemented(cmd, "deepen is not yet wired")

    if cmd == "/abandon":
        if not args:
            return {"message": _USAGE["/abandon"]}
        return _unimplemented(cmd, "hypothesis abandonment is not yet wired")

    # ── View commands ────────────────────────────────────────────────
    if cmd == "/status":
        return {
            "summary": f"Project: {session.project_id} — {session.status.value}",
            "active_workstreams": [f"{ws} — (tracked)" for ws in session.active_workstreams],
        }

    if cmd in ("/hypotheses", "/dead-ends", "/document"):
        return _unimplemented(cmd, "this view is not yet wired")

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
            return {"message": _USAGE["/export"]}
        return _unimplemented(cmd, "export is not yet wired")

    if cmd in ("/add-note", "/upload"):
        if not args:
            return {"message": _USAGE[cmd]}
        return _unimplemented(cmd, "this command is not yet wired")

    if cmd == "/help-request":
        return _unimplemented(cmd, "help-request is not yet wired to the coordinator")

    if cmd == "/config":
        return _unimplemented(cmd, "config changes are not persisted yet")

    return {"message": f"Unknown command: '{cmd}'. Type /help for available commands."}


def _help_response() -> dict[str, Any]:
    categories = {
        "Session": "/help, /exit, /quit, /new*, /open*, /projects*, /archive*",
        "Inquiry": "/search, /analyze, /argue, /review, /compare, /synthesize  (via coordinator)",
        "Steering": "/pause*, /resume*, /steer*, /deepen*, /abandon*",
        "View": "/status, /hypotheses*, /dead-ends*, /document*, /details, /hide-details, /suggestions, /hide-suggestions",
        "Export": "/export*, /add-note*, /upload*",
        "Config": "/help-request*, /config*",
    }
    lines = [
        "Available commands (* = registered but not yet implemented):\n",
    ]
    for cat, cmds in categories.items():
        lines.append(f"  [{cat}]: {cmds}")
    return {"message": "\n".join(lines)}
