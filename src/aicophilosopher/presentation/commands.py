import uuid

import click


@click.group()
def cli() -> None:
    """AI Co-Philosopher — An agentic workbench for philosophical research."""


@cli.command()
@click.argument("title")
@click.option("--question", "-q", help="Initial philosophical question")
@click.option("--directory", "-d", help="Custom workspace directory")
def new_project(title: str, question: str | None = None, directory: str | None = None) -> None:
    """Create a new philosophical research project."""
    click.echo(f"Project created: {title}")
    if question:
        click.echo(f"Initial question: {question}")
    click.echo("Project Coordinator: Welcome to the AI Co-Philosopher.")


@cli.command()
def list_projects() -> None:
    """List all projects with status summary."""
    click.echo("No projects yet. Use `new project` to create one.")


@cli.command()
@click.argument("project_id")
def open_project(project_id: str) -> None:
    """Resume an existing project."""
    click.echo(f"Opening project: {project_id}")


@cli.command()
@click.argument("project_id")
def archive_project(project_id: str) -> None:
    """Archive a completed or inactive project."""
    click.confirm("This will make the project read-only. Continue?", abort=True)
    click.echo(f"Project '{project_id}' archived.")


@cli.command()
def refine_goal() -> None:
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
def start_workstream(workstream_type: str, goal: str | None = None, instructions: str | None = None) -> None:
    """Propose and launch a new workstream."""
    click.echo(f"Workstream '{workstream_type}' proposed.")
    if goal:
        click.echo(f"Attached to goal: {goal}")
    if instructions:
        click.echo(f"Instructions: {instructions}")
    click.echo("Project Coordinator: Do you want to proceed with this workstream? (y/N)")


@cli.command()
@click.argument("workstream_id")
def pause(workstream_id: str) -> None:
    """Pause a running workstream."""
    click.echo(f"Workstream '{workstream_id}' paused.")


@cli.command()
@click.argument("workstream_id")
def resume(workstream_id: str) -> None:
    """Resume a paused or stalled workstream."""
    click.echo(f"Workstream '{workstream_id}' resumed.")


@cli.command()
@click.argument("workstream_id")
@click.argument("instruction")
def steer(workstream_id: str, instruction: str) -> None:
    """Direct steering of a specific workstream."""
    click.echo(f"Steering command received for '{workstream_id}': {instruction}")


@cli.command()
@click.option("--status", "filter_status", type=click.Choice(["active", "abandoned", "refined", "refuted"]), help="Filter by hypothesis status")
@click.option("--tradition", help="Filter by epistemic tradition")
def show_hypotheses(filter_status: str | None = None, tradition: str | None = None) -> None:
    """Display hypothesis history with epistemic status."""
    click.echo("Hypothesis History:")
    click.echo("  No hypotheses yet. Start a workstream to generate hypotheses.")


@cli.command()
def show_dead_ends() -> None:
    """Display failed explorations and refuted arguments."""
    click.echo("Failed Explorations (Dead Ends):")
    click.echo("  No dead ends yet.")


@cli.command()
@click.argument("text")
@click.option("--attach-to", help="Hypothesis/claim/workstream ID to link note to")
def add_note(text: str, attach_to: str | None = None) -> None:
    """Add user note to workspace."""
    note_id = f"note-{uuid.uuid4().hex[:4]}"
    click.echo(f"Note added: {note_id}")
    if attach_to:
        click.echo(f"Attached to: {attach_to}")


@cli.command()
@click.argument("topic")
@click.option("--traditions", "-t", help="Specific traditions to compare")
def compare_traditions(topic: str, traditions: str | None = None) -> None:
    """Request cross-traditional comparison."""
    click.echo(f"Comparing traditions on: {topic}")
    if traditions:
        click.echo(f"Traditions: {traditions}")


@cli.command()
def export() -> None:
    """Export living document to external format."""
    click.echo("Export format: markdown (default)")
    click.echo("Use `export latex` for LaTeX output (post-MVP).")


@cli.command()
def status() -> None:
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
def show_document() -> None:
    """Display the current living document."""
    click.echo("# Living Document")
    click.echo()
    click.echo("No document content yet. Start a workstream to generate content.")


@cli.command()
@click.argument("key", required=False)
@click.argument("value", required=False)
def config(key: str | None = None, value: str | None = None) -> None:
    """View or set configuration."""
    if key is None:
        click.echo("Current configuration:")
        click.echo("  llm.backend: ollama")
        click.echo("  privacy.allow_external_search: false")
    else:
        click.echo(f"Config '{key}' set to: {value}")


@cli.command()
def request_help() -> None:
    """Explicitly request human assistance flag from coordinator."""
    click.echo("Help request sent to Project Coordinator.")
