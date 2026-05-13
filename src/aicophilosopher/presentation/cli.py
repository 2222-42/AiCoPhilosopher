from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table
from rich.tree import Tree

from aicophilosopher.presentation.commands import cli

console = Console()


def progressive_disclosure(summary: str, details: str = "", suggestions: str = "") -> None:
    console.print()
    console.print(Panel(f"[bold]Summary[/bold]\n\n{summary}", title="AiCoPhilosopher"))
    console.print()

    if details:
        console.print(Panel(Markdown(details), title="[Details]"))
        console.print()

    if suggestions:
        console.print(Panel(Markdown(suggestions), title="[Suggestions]"))
        console.print()


def render_status(project_id: str, status_data: dict[str, int | bool | str]) -> None:
    table = Table(title="Epistemic Status Overview")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="bold")
    table.add_row("Active Hypotheses", str(status_data.get("active_hypotheses", 0)))
    table.add_row("Refuted", str(status_data.get("refuted_hypotheses", 0)))
    table.add_row("Under Review", str(status_data.get("under_review", 0)))
    table.add_row("Stalled", str(status_data.get("stalled", 0)))
    console.print(table)
    console.print()

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )
    with progress:
        progress.add_task("Literature Search", total=100)
        progress.add_task("Concept Analysis", total=100)


def render_document(content: str, section: str | None = None, show_annotations: bool = False) -> None:
    if section:
        console.print(f"[bold]Section: {section}[/bold]")
        console.print()
    md = Markdown(content)
    console.print(md)
    if show_annotations:
        console.print()
        console.print("[dim]Annotations are embedded as HTML comments in the source.[/dim]")


def render_hypotheses_table(hypotheses: list[dict[str, str]]) -> None:
    table = Table(title="Hypothesis History")
    table.add_column("ID", style="dim")
    table.add_column("Statement", style="cyan")
    table.add_column("Strength", style="yellow")
    table.add_column("Status", style="bold")
    table.add_column("Origin")
    for h in hypotheses:
        table.add_row(
            h.get("hypothesis_id", ""),
            h.get("statement", ""),
            h.get("strength", ""),
            h.get("status", ""),
            h.get("origin", ""),
        )
    console.print(table)


def render_dead_ends(dead_ends: list[dict[str, str]]) -> None:
    if not dead_ends:
        console.print("[yellow]No failed explorations yet.[/yellow]")
        return
    for de in dead_ends:
        console.print(Panel(
            f"[bold]Goal:[/bold] {de.get('goal_attempted', '')}\n"
            f"[bold]Failure:[/bold] {de.get('failure_reason', '')}\n"
            f"[bold]Lesson:[/bold] {de.get('lessons_learned', '')}",
            title=f"Failed Exploration: {de.get('exploration_id', '')}",
        ))


def render_workstream_tree(workstreams: list[dict[str, str | int]]) -> None:
    tree = Tree("Active Workstreams")
    for ws in workstreams:
        branch = tree.add(f"[bold]{ws.get('workstream_id', '')}[/bold] — {ws.get('type', '')}")
        branch.add(f"Status: [green]{ws.get('status', '')}[/green]")
        branch.add(f"Progress: {ws.get('progress_percent', 0)}%")
    console.print(tree)


def main() -> None:
    console.print("[bold magenta]AI Co-Philosopher[/bold magenta]")
    console.print("[dim]An agentic workbench for philosophical research[/dim]")
    console.print()
    cli()


if __name__ == "__main__":
    main()
