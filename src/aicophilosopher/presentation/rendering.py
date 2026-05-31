"""Progressive disclosure renderer for Console Agent REPL (T-013)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

if TYPE_CHECKING:
    from aicophilosopher.domain.entities.session import FocusContext


def render_response(  # noqa: C901
    response: dict[str, Any],
    focus: FocusContext,
    console: Console | None = None,
) -> None:
    """Render coordinator response with progressive disclosure.

    Sections: Summary, Epistemic Status, Active Workstreams,
    [Details] (togglable), [Suggestions] (togglable).
    """
    if console is None:
        console = Console()

    summary = response.get("summary") or response.get("message", "")
    error = response.get("error", "")

    if error:
        console.print(Panel(error, title="Error", border_style="red"))
    elif isinstance(summary, str) and summary.strip():
        lines = summary.strip().split("\n")
        if len(lines) > 5:
            summary = "\n".join(lines[:5]) + "\n[...]"
        console.print(Panel(summary, title="Summary", border_style="bold"))

    epistemic = response.get("epistemic_status", "")
    if epistemic:
        console.print(Panel(epistemic, title="Epistemic Status"))

    workstreams = response.get("active_workstreams", [])
    if workstreams:
        ws_text = Text()
        for ws in workstreams:
            ws_text.append(f"• {ws}\n")
        console.print(Panel(ws_text, title="Active Workstreams"))

    if response.get("is_approval_request"):
        opts = response.get("approval_options", [])
        opt_lines = "\n".join(f"  {i + 1}. {o}" for i, o in enumerate(opts))
        console.print(
            Panel(opt_lines, title="⚠️ Approval Required", border_style="red")
        )

    if focus.toggle_state.show_details:
        details = response.get("details", "")
        if details:
            console.print(Panel(details, title="Details"))
        else:
            console.print("No additional details available.")
    else:
        console.print(Text("[Details]", style="dim"))

    if focus.toggle_state.show_suggestions:
        suggestions = response.get("suggestions", [])
        if suggestions:
            sug_text = Text()
            for s in suggestions:
                sug_text.append(f"• {s}\n")
            console.print(Panel(sug_text, title="Suggestions"))
        else:
            console.print("No suggestions at this time.")
    else:
        console.print(Text("[Suggestions]", style="dim"))
