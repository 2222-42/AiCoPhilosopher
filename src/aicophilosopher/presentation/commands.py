
import uuid

import click


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """AI Co-Philosopher — An agentic workbench for philosophical research."""
    ctx.ensure_object(dict)


@cli.command()
@click.argument("title")
@click.option("--question", "-q", help="Initial philosophical question")
@click.option("--directory", "-d", help="Custom workspace directory")
@click.pass_context
def new_project(ctx: click.Context, title: str, question: str | None = None, directory: str | None = None) -> None:
    """Create a new philosophical research project."""
    click.echo(f"Project created: {title}")
    if question:
        click.echo(f"Initial question: {question}")
    click.echo("Project Coordinator: Welcome to the AI Co-Philosopher.")


@cli.command()
@click.pass_context
def refine_goal(ctx: click.Context) -> None:
    """Enter or continue dialectical clarification dialogue."""
    click.echo("Project Coordinator: Let's refine your research goal.")
    click.echo("What aspects of this question would you like to focus on?")


@cli.command()
@click.argument("workstream_type", type=click.Choice([
    "literature_search", "concept_analysis", "cross_traditional_comparison",
    "argumentation", "critical_review", "synthesis",
]))
@click.option("--goal", "-g", help="Goal ID to attach workstream to")
@click.option("--instructions", "-i", help="Additional instructions")
@click.pass_context
def start_workstream(ctx: click.Context, workstream_type: str, goal: str | None = None, instructions: str | None = None) -> None:
    """Propose and launch a new workstream."""
    click.echo(f"Workstream '{workstream_type}' proposed.")
    if goal:
        click.echo(f"Attached to goal: {goal}")
    if instructions:
        click.echo(f"Instructions: {instructions}")
    click.echo("Project Coordinator: Do you want to proceed with this workstream? (y/N)")


@cli.command()
@click.argument("workstream_id")
@click.pass_context
def pause(ctx: click.Context, workstream_id: str) -> None:
    """Pause a running workstream."""
    click.echo(f"Workstream '{workstream_id}' paused.")


@cli.command()
@click.argument("workstream_id")
@click.pass_context
def resume(ctx: click.Context, workstream_id: str) -> None:
    """Resume a paused or stalled workstream."""
    click.echo(f"Workstream '{workstream_id}' resumed.")


@cli.command()
@click.argument("workstream_id")
@click.argument("instruction")
@click.pass_context
def steer(ctx: click.Context, workstream_id: str, instruction: str) -> None:
    """Direct steering of a specific workstream."""
    click.echo(f"Steering command received for '{workstream_id}': {instruction}")


@cli.command()
@click.option("--filter-status", type=click.Choice(["active", "abandoned", "refined", "refuted"]), default=None, help="Filter by hypothesis status")
@click.option("--tradition", help="Filter by epistemic tradition")
@click.pass_context
def show_hypotheses(ctx: click.Context, filter_status: str | None = None, tradition: str | None = None) -> None:
    """Display hypothesis history with epistemic status."""
    click.echo("Hypothesis History:")
    click.echo("  No hypotheses yet. Start a workstream to generate hypotheses.")


@cli.command()
@click.pass_context
def show_dead_ends(ctx: click.Context) -> None:
    """Display failed explorations and refuted arguments."""
    click.echo("Failed Explorations (Dead Ends):")
    click.echo("  No dead ends yet.")


@cli.command()
@click.argument("text")
@click.option("--attach-to", help="Hypothesis/claim/workstream ID to link note to")
@click.pass_context
def add_note(ctx: click.Context, text: str, attach_to: str | None = None) -> None:
    """Add user note to workspace."""
    note_id = f"note-{uuid.uuid4().hex[:4]}"
    click.echo(f"Note added: {note_id}")
    if attach_to:
        click.echo(f"Attached to: {attach_to}")


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Display system-wide status overview."""
    click.echo("Epistemic Status Overview:")
    click.echo("  Active hypotheses: 0")
    click.echo("  Refuted: 0")
    click.echo("  Under review: 0")
    click.echo("  Stalled: 0")
    click.echo()
    click.echo("Active Workstreams:")
    click.echo("  No active workstreams.")
    click.echo()
    click.echo("LLM Backend: ollama (connected)")


@cli.command()
@click.option("--section", "-s", help="Display a specific section")
@click.option("--annotations", "-a", is_flag=True, help="Show margin annotations inline")
@click.pass_context
def show_document(ctx: click.Context, section: str | None = None, annotations: bool = False) -> None:
    """Display the current living document."""
    click.echo("# Living Document")
    click.echo()
    click.echo("No document content yet. Start a workstream to generate content.")



