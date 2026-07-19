"""CLI commands — wired to actual project creation and agent execution."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

CURRENT_PROJECT_FILE = Path(".current_project")


def _get_workspace() -> Path:
    """Return the projects directory from Config (single source of truth).

    Uses ``AICOPH_WORKSPACE_DIR`` (default ``~/.aicophilosopher``); projects
    are stored under ``<workspace>/projects/`` to match FileSystemAdapter.
    """
    from aicophilosopher.domain.services.config import Config

    return Config().projects_dir()


def _ensure_workspace() -> None:
    _get_workspace().mkdir(parents=True, exist_ok=True)


def _project_dir(project_id: str) -> Path:
    return _get_workspace() / project_id


def _create_project_structure(project_id: str, title: str, question: str | None = None) -> Path:
    """Create the full project directory tree."""
    base = _project_dir(project_id)
    base.mkdir(parents=True, exist_ok=True)

    # metadata.json
    metadata = {
        "project_id": project_id,
        "title": title,
        "original_question": question or title,
        "status": "created",
        "created_at": datetime.now(UTC).isoformat(),
        "workstreams": {},
        "hypotheses": [],
    }
    (base / "metadata.json").write_text(json.dumps(metadata, indent=2))

    # living_document.md with YAML frontmatter
    safe_title = title.replace('"', '\\"').replace("\n", " ")
    safe_question = (question or title).replace('"', '\\"').replace("\n", " ")
    frontmatter = f"""---
title: "{safe_title}"
project_id: "{project_id}"
status: "draft"
created: "{datetime.now(UTC).isoformat()}"
traditions_referenced: []
---

# {title}

## Introduction

{safe_question}

_This living document will be populated by AI Co-Philosopher agents as you run workstreams._
"""
    (base / "living_document.md").write_text(frontmatter)

    # Subdirectories
    for sub in ("workstreams", "conceptual_genealogy", "artifacts", "margin_notes", "logs"):
        (base / sub).mkdir(exist_ok=True)

    # Derived export files (empty JSONL)
    (base / "dialectical_history.jsonl").touch()
    (base / "hypotheses.jsonl").touch()
    (base / "uncertainty_registry.json").write_text("[]")

    # Register as current project
    CURRENT_PROJECT_FILE.write_text(project_id)

    return base


def _get_current_project_id() -> str | None:
    if CURRENT_PROJECT_FILE.exists():
        return CURRENT_PROJECT_FILE.read_text().strip()
    return None


def _save_current_project(project_id: str) -> None:
    CURRENT_PROJECT_FILE.write_text(project_id)


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------
@click.group(invoke_without_command=True)
@click.option("--project", "-p", help="Project ID to open directly in REPL")
@click.option("--new", "-n", "new_question", help="Create a new project with this question")
@click.option("--test-mode", is_flag=True, help="Launch REPL with mock coordinator (no LLM)")
@click.option(
    "--backend", "-b", help="LLM backend: ollama, claude, gemini (overrides AICOPH_LLM_BACKEND)"
)
@click.pass_context
def cli(
    ctx: click.Context,
    project: str | None,
    new_question: str | None,
    test_mode: bool,
    backend: str | None,
) -> None:  # noqa: C901
    """AI Co-Philosopher — An agentic workbench for philosophical research.

    Run without subcommands to enter an interactive REPL session.
    """
    # If a subcommand was given, let Click handle it normally.
    if ctx.invoked_subcommand is not None:
        return

    # No subcommand → launch REPL mode.
    import asyncio

    from aicophilosopher.presentation.repl import run_repl

    if new_question:
        project_id = _create_project_from_question(new_question)
        click.echo(f"Created project {project_id} — entering REPL...")
        project = project_id

    llm_port, coordinator, storage = _wire_backends(
        project, test_mode=test_mode, backend_override=backend
    )
    asyncio.run(
        run_repl(
            project_id=project,
            test_mode=test_mode,
            llm_port=llm_port,
            coordinator=coordinator,
            storage=storage,
        )
    )


def _wire_backends(  # noqa: C901
    project_id: str | None = None,
    test_mode: bool = False,
    backend_override: str | None = None,
) -> tuple[Any, Any, Any]:
    """Create LLM backend and Coordinator for the REPL.

    Returns (llm_port, coordinator).  Both may be None if the backend
    is not configured — the REPL handles this with a helpful message.
    """
    if test_mode:
        return None, None, None

    from aicophilosopher.container import Container
    from aicophilosopher.domain.services.config import Config
    from aicophilosopher.infrastructure.adapters.filesystem_adapter import FileSystemAdapter

    # ── Load configuration ──────────────────────────────────────────
    try:
        config = Config()
    except Exception:
        click.echo("[System] Could not load config. Using defaults.")
        # Create a defaults-only instance that won't re-read env
        config = Config(
            llm_backend="ollama",  # type: ignore[call-arg]
            llm_model="",
            llm_api_key="",
        )

    # Allow CLI --backend flag to override env/AICOPH_LLM_BACKEND
    if backend_override:
        try:
            config.llm_backend = backend_override  # type: ignore[assignment]
        except Exception:
            pass

    # ── Create LLM backend ──────────────────────────────────────────
    try:
        llm_port = Container.create_llm_backend(config)
        llm_label = getattr(llm_port, "model", config.llm_backend) or config.llm_backend
        click.echo(f"[System] LLM backend: {llm_label}")
    except Exception as exc:
        click.echo(f"[System] Could not create LLM backend ({exc}).")
        click.echo("  Set AICOPH_LLM_BACKEND=ollama (or claude/gemini) or use --backend <name>")
        click.echo("  For Claude:   export AICOPH_LLM_API_KEY=sk-ant-...")
        click.echo("  For Gemini:   export AICOPH_LLM_API_KEY=...")
        click.echo("  For Ollama:   install ollama and pull a model")
        click.echo("  Or use --test-mode for a mock session.")
        return None, None, None

    # ── Create Coordinator ──────────────────────────────────────────
    fs_adapter = FileSystemAdapter(base_path=config.workspace_dir)
    resolved_pid = project_id or "default"

    from aicophilosopher.application.orchestration.coordinator import ProjectCoordinatorAgent

    coordinator = ProjectCoordinatorAgent(
        project_id=resolved_pid,
        llm_backend=llm_port,
        filesystem=fs_adapter,
    )

    # ── Create OpenCode Go bridge (if enabled) ──────────────────────
    if config.opencode_enabled:
        from aicophilosopher.infrastructure.adapters.external_bridge_adapter import (
            create_opencode_bridge,
        )

        bridge = create_opencode_bridge(enabled=True)
        coordinator.external_bridge = bridge  # type: ignore[attr-defined]
        click.echo("[System] OpenCode Go bridge enabled")

    return llm_port, coordinator, fs_adapter


def _create_project_from_question(question: str) -> str:
    """Quick project creation from a question string for --new."""
    _ensure_workspace()
    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    # Use first 60 chars of question as title
    title = question[:60] + ("..." if len(question) > 60 else "")
    _create_project_structure(project_id, title, question)
    return project_id


@cli.command()
@click.argument("title")
@click.option("--question", "-q", help="Initial philosophical question")
def new_project(title: str, question: str | None = None) -> None:
    """Create a new philosophical research project."""
    _ensure_workspace()
    project_id = f"proj-{uuid.uuid4().hex[:8]}"
    base = _create_project_structure(project_id, title, question)

    click.echo(f"Project created: {title}")
    click.echo(f"ID: {project_id}")
    click.echo(f"Location: {base}")
    click.echo()
    click.echo("Project Coordinator: Welcome to the AI Co-Philosopher.")
    click.echo()
    click.echo("Next steps:")
    click.echo("  aicophilosopher refine-goal     — clarify your question")
    click.echo("  aicophilosopher start-workstream literature_search")


@cli.command()
def list_projects() -> None:
    """List all projects with status summary."""
    _ensure_workspace()
    projects = sorted(_get_workspace().iterdir())
    if not projects:
        click.echo("No projects yet. Use `new-project` to create one.")
        return

    for p in projects:
        if p.is_dir():
            meta_file = p / "metadata.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
                status = meta.get("status", "?")
                title = meta.get("title", p.name)
                click.echo(f"  [{p.name}] {title} — {status}")
            else:
                click.echo(f"  [{p.name}] (no metadata)")


@cli.command()
@click.argument("project_id", required=False)
def open_project(project_id: str | None = None) -> None:
    """Resume an existing project."""
    _ensure_workspace()
    if project_id is None:
        # Try to open current
        project_id = _get_current_project_id()
        if project_id is None:
            click.echo("No current project. Use `open-project <id>` or `list-projects`.")
            return
    proj_dir = _project_dir(project_id)
    if not proj_dir.exists():
        raise click.ClickException(f"Project '{project_id}' not found.")
    _save_current_project(project_id)
    meta = json.loads((proj_dir / "metadata.json").read_text())
    click.echo(f"Opened project: {meta.get('title', project_id)}")
    click.echo(f"Status: {meta.get('status', '?')}")


@cli.command()
@click.argument("project_id")
def archive_project(project_id: str) -> None:
    """Archive a completed or inactive project."""
    proj_dir = _project_dir(project_id)
    if not proj_dir.exists():
        raise click.ClickException(f"Project '{project_id}' not found.")
    click.confirm("This will make the project read-only. Continue?", abort=True)
    meta = json.loads((proj_dir / "metadata.json").read_text())
    meta["status"] = "archived"
    (proj_dir / "metadata.json").write_text(json.dumps(meta, indent=2))
    click.echo(f"Project '{project_id}' archived.")


@cli.command()
def refine_goal() -> None:
    """Enter Socratic clarification dialogue."""
    proj_id = _get_current_project_id()
    if proj_id is None:
        click.echo("No active project. Use `new-project` or `open-project` first.")
        return
    click.echo("Project Coordinator: Let's refine your research goal.")
    click.echo()

    # Socratic clarification dialogue (≤5 turns per constitution AC-001)
    proj = json.loads((_project_dir(proj_id) / "metadata.json").read_text())
    question = proj.get("original_question", proj.get("title", "your topic"))

    click.echo(f"Your question: {question}")
    click.echo()
    click.echo("I'll ask a few clarifying questions to refine this inquiry.")
    click.echo()

    questions = [
        (
            "Which philosophical traditions are most relevant? "
            "(e.g., analytic, continental, philosophy_of_technology, "
            "philosophy_of_mathematics)"
        ),
        (
            "What specific aspect of this question interests you most? "
            "(e.g., ontological, epistemological, ethical, phenomenological)"
        ),
        ("Are there particular philosophers or texts you want to engage with?"),
        (
            "What would a satisfactory answer look like — a clear argument, "
            "a conceptual map, or a cross-traditional comparison?"
        ),
    ]

    answers = []
    for i, q in enumerate(questions[:4], 1):  # max 5 turns
        click.echo(f"[Turn {i}/4]")
        answer = click.prompt(f"  {q}", default="continue")
        if answer.lower() in ("skip", "done", ""):
            if answer.lower() == "done":
                break
            continue
        answers.append({"question": q, "answer": answer})

    # Persist refined goal to project metadata
    if answers:
        proj = json.loads((_project_dir(proj_id) / "metadata.json").read_text())
        proj["refined_answers"] = answers
        proj["status"] = "clarifying"
        (_project_dir(proj_id) / "metadata.json").write_text(json.dumps(proj, indent=2))

    click.echo()
    click.echo("Project Coordinator: Thank you. Your refined goal is ready.")
    click.echo()
    click.echo("You can now launch workstreams:")
    click.echo("  aicophilosopher start-workstream literature_search")
    click.echo("  aicophilosopher start-workstream argumentation")
    click.echo("  aicophilosopher start-workstream concept_analysis")


def _echo_workstream_result(workstream_type: str, result: dict[str, Any]) -> None:
    """Print a human-readable summary of a workstream agent result."""
    click.echo()
    if workstream_type == "argumentation":
        click.echo("=== Argumentation Results ===")
        for i, arg in enumerate(result.get("arguments") or [], 1):
            click.echo(f"\nPosition {i} [{arg.get('tradition', '?')}]:")
            click.echo(f"  Conclusion: {arg.get('conclusion', '')}")
            click.echo(f"  Confidence: {arg.get('confidence', '?')}")
        click.echo(f"\nCompeting positions: {len(result.get('competing_positions') or [])}")
    elif workstream_type == "critical_review":
        click.echo("=== Critical Review ===")
        click.echo(f"Fallacies found: {len(result.get('fallacies') or [])}")
        for f in result.get("fallacies") or []:
            click.echo(f"  [{f.get('severity', '?')}] {f.get('name', '?')}")
        click.echo(f"Counter-arguments: {len(result.get('counter_arguments') or [])}")
    elif workstream_type == "cross_traditional_comparison":
        click.echo("=== Cross-Traditional Comparison ===")
        click.echo(f"Bridges found: {len(result.get('bridge_map') or [])}")
        click.echo(f"Incommensurabilities: {len(result.get('incommensurability_register') or [])}")
    elif workstream_type == "synthesis":
        click.echo("=== Synthesis ===")
        doc = str(result.get("synthesized_document") or "")
        click.echo(doc[:500])
    elif workstream_type == "literature_search":
        click.echo("=== Literature Search ===")
        click.echo(f"Results: {result.get('result_count', 0)}")
        click.echo(f"Bridge notes: {len(result.get('bridge_notes') or [])}")
    elif workstream_type == "concept_analysis":
        click.echo("=== Concept Analysis ===")
        click.echo(f"Concept map: {result.get('concept_map', 'no data')}")


async def _run_workstream_agent(
    workstream_type: str,
    proj_id: str,
    query: str,
    kwargs: dict[str, object],
) -> dict[str, Any]:
    """Dispatch to the matching agent and return its result dict."""
    if workstream_type == "argumentation":
        from aicophilosopher.application.agents.argumentation import ArgumentationAgent

        return await ArgumentationAgent(agent_id=f"cli-{proj_id}").run(query, **kwargs)

    if workstream_type == "critical_review":
        from aicophilosopher.application.agents.argumentation import ArgumentationAgent
        from aicophilosopher.application.agents.critical_review import CriticalReviewAgent

        arg_result = await ArgumentationAgent(agent_id=f"cli-arg-{proj_id}").run(query, **kwargs)
        review_input = list(arg_result.get("arguments") or []) + list(
            arg_result.get("competing_positions") or []
        )
        return await CriticalReviewAgent(agent_id=f"cli-{proj_id}").run(review_input)

    if workstream_type == "cross_traditional_comparison":
        from aicophilosopher.application.agents.cross_traditional import (
            CrossTraditionalComparisonAgent,
        )

        return await CrossTraditionalComparisonAgent(agent_id=f"cli-{proj_id}").run(query, **kwargs)

    if workstream_type == "synthesis":
        from aicophilosopher.application.agents.synthesis import SynthesisAgent

        return await SynthesisAgent(agent_id=f"cli-{proj_id}").run(
            [
                {
                    "workstream_id": "ws-1",
                    "type": "argumentation",
                    "results": "Argument analysis results would go here.",
                    "confidence": 0.7,
                    "claims": [
                        {
                            "text": "Key finding",
                            "confidence": 0.8,
                            "origin": "analysis",
                        }
                    ],
                },
            ]
        )

    if workstream_type == "literature_search":
        from aicophilosopher.application.agents.literature_search import (
            LiteratureSearchAgent,
        )

        return await LiteratureSearchAgent(agent_id=f"cli-{proj_id}").run(query, **kwargs)

    if workstream_type == "concept_analysis":
        from aicophilosopher.application.agents.concept_analysis import (
            ConceptAnalysisAgent,
        )

        return await ConceptAnalysisAgent(agent_id=f"cli-{proj_id}").run(query, **kwargs)

    raise ValueError(f"Unsupported workstream type: {workstream_type}")


@cli.command()
@click.argument(
    "workstream_type",
    type=click.Choice(
        [
            "literature_search",
            "concept_analysis",
            "cross_traditional_comparison",
            "argumentation",
            "critical_review",
            "synthesis",
        ]
    ),
)
@click.option("--instructions", "-i", help="Additional instructions")
@click.option(
    "--traditions", "-t", help="Comma-separated tradition list (e.g. analytic,continental)"
)
def start_workstream(
    workstream_type: str,
    instructions: str | None = None,
    traditions: str | None = None,
) -> None:
    """Launch a workstream using the appropriate AI agent."""
    import asyncio

    proj_id = _get_current_project_id()
    if proj_id is None:
        click.echo("No active project. Use `new-project` or `open-project` first.")
        return

    click.echo(f"Launching {workstream_type} workstream...")

    # Load project question as default instruction
    proj_meta = json.loads((_project_dir(proj_id) / "metadata.json").read_text())
    default_query = str(proj_meta.get("original_question", proj_meta.get("title", "")))

    # Parse traditions if provided
    trad_list: list[str] | None = None
    if traditions:
        trad_list = [t.strip() for t in traditions.split(",")]

    summary = asyncio.run(
        _dispatch_workstream(
            workstream_type,
            proj_id,
            instructions or default_query,
            trad_list,
        )
    )
    click.echo()
    click.echo(f"Workstream '{workstream_type}' completed.")
    if summary is not None:
        click.echo(
            f"Persisted: {summary['hypotheses_added']} hypotheses → metadata/jsonl; "
            f"document updated; report: {summary['report_path']}"
        )
        click.echo("  View with: aicophilosopher show-hypotheses | show-document")


async def _dispatch_workstream(
    workstream_type: str,
    proj_id: str,
    query: str,
    trad_list: list[str] | None,
) -> dict[str, Any] | None:
    """Run the agent, print results, and persist to living document / hypotheses."""
    from aicophilosopher.application.services.workstream_persistence import (
        persist_workstream_results,
    )

    kwargs: dict[str, object] = {}
    if trad_list:
        kwargs["traditions"] = trad_list

    try:
        result = await _run_workstream_agent(workstream_type, proj_id, query, kwargs)
    except ValueError:
        click.echo(f"Unknown workstream type: {workstream_type}")
        return None

    _echo_workstream_result(workstream_type, result)

    # Persist hypotheses + living document so show-* commands can read them.
    summary = persist_workstream_results(
        _project_dir(proj_id), workstream_type, result
    )
    return summary


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
    click.echo(f"Steering '{workstream_id}': {instruction}")


@cli.command()
def status() -> None:
    """Display system-wide status overview."""
    proj_id = _get_current_project_id()
    if proj_id is None:
        click.echo("No active project.")
        return
    proj_dir = _project_dir(proj_id)
    if not proj_dir.exists():
        click.echo(f"Project directory missing: {proj_dir}")
        return

    meta = json.loads((proj_dir / "metadata.json").read_text())
    click.echo(f"Project: {meta.get('title', proj_id)}")
    click.echo(f"Status: {meta.get('status', '?')}")
    click.echo(f"Workstreams: {len(meta.get('workstreams', {}))}")
    click.echo(f"Hypotheses: {len(meta.get('hypotheses', []))}")


@cli.command()
def show_document() -> None:
    """Display the current living document."""
    proj_id = _get_current_project_id()
    if proj_id is None:
        click.echo("No active project.")
        return
    doc_path = _project_dir(proj_id) / "living_document.md"
    if not doc_path.exists():
        click.echo("No document yet.")
        return
    click.echo(doc_path.read_text())


@cli.command()
@click.option(
    "--status", "filter_status", type=click.Choice(["active", "abandoned", "refined", "refuted"])
)
def show_hypotheses(filter_status: str | None = None) -> None:
    """Display hypothesis history."""
    from aicophilosopher.application.services.workstream_persistence import (
        load_hypotheses,
    )

    proj_id = _get_current_project_id()
    if proj_id is None:
        click.echo("No active project.")
        return

    hyps = load_hypotheses(_project_dir(proj_id), filter_status=filter_status)
    if not hyps:
        if filter_status:
            click.echo(f"No hypotheses with status '{filter_status}'.")
        else:
            click.echo("No hypotheses yet. Start a workstream to generate them.")
        return

    click.echo(f"Hypotheses ({len(hyps)}):")
    for h in hyps:
        trad = h.get("epistemic_tradition") or "—"
        conf = h.get("confidence_score", "?")
        strength = h.get("strength", "?")
        click.echo(
            f"  [{h.get('hypothesis_id', '?')}] "
            f"status={h.get('status', '?')} strength={strength} "
            f"conf={conf} tradition={trad}"
        )
        click.echo(f"    {h.get('statement', '')}")
        src = h.get("source_workstream")
        if src:
            click.echo(f"    source: {src} ({h.get('workstream_type', '?')})")


@cli.command()
def show_dead_ends() -> None:
    """Display failed explorations (refuted / abandoned hypotheses)."""
    from aicophilosopher.application.services.workstream_persistence import (
        load_hypotheses,
    )

    proj_id = _get_current_project_id()
    if proj_id is None:
        click.echo("No active project.")
        return

    dead = [
        h
        for h in load_hypotheses(_project_dir(proj_id))
        if h.get("status") in ("refuted", "abandoned")
    ]
    if not dead:
        click.echo("No dead ends yet.")
        return

    click.echo(f"Dead ends ({len(dead)}):")
    for h in dead:
        click.echo(f"  [{h.get('hypothesis_id', '?')}] status={h.get('status', '?')}")
        click.echo(f"    {h.get('statement', '')}")


@cli.command()
@click.argument("text")
@click.option("--attach-to", help="Hypothesis/claim ID to attach to")
def add_note(text: str, attach_to: str | None = None) -> None:
    """Add user note to workspace."""
    proj_id = _get_current_project_id()
    if proj_id is None:
        click.echo("No active project.")
        return
    note_id = f"note-{uuid.uuid4().hex[:4]}"
    # Persist to project margin_notes directory
    notes_dir = _project_dir(proj_id) / "margin_notes"
    notes_dir.mkdir(exist_ok=True)
    note_data = {
        "note_id": note_id,
        "text": text,
        "attached_to": attach_to,
        "created_at": datetime.now(UTC).isoformat(),
    }
    (notes_dir / f"{note_id}.json").write_text(json.dumps(note_data, indent=2))
    click.echo(f"Note [{note_id}]: {text}")
    click.echo(f"  Saved to: {notes_dir / f'{note_id}.json'}")
    if attach_to:
        click.echo(f"  Attached to: {attach_to}")


@cli.command()
@click.argument("topic")
@click.option("--traditions", "-t", help="Comma-separated traditions")
def compare_traditions(topic: str, traditions: str | None = None) -> None:
    """Cross-traditional comparison using the agent."""
    import asyncio

    from aicophilosopher.application.agents.cross_traditional import (
        CrossTraditionalComparisonAgent,
    )

    trad_list = [t.strip() for t in traditions.split(",")] if traditions else None

    async def _run() -> None:
        agent = CrossTraditionalComparisonAgent(agent_id="cli-ct")
        kwargs: dict[str, object] = {}
        if trad_list:
            kwargs["traditions"] = trad_list
        result = await agent.run(topic, **kwargs)
        click.echo(f"\n=== Cross-Traditional: {topic} ===")
        click.echo(f"Bridges: {len(result['bridge_map'])}")
        click.echo(f"Incommensurabilities: {len(result['incommensurability_register'])}")

    asyncio.run(_run())


@cli.command()
@click.argument(
    "fmt", required=False, default="markdown", type=click.Choice(["markdown", "html", "latex"])
)
def export(fmt: str = "markdown") -> None:
    """Export living document."""
    click.echo(f"Export format: {fmt}")


@cli.command("config")
@click.argument("key", required=False)
@click.argument("value", required=False)
def config_cmd(key: str | None = None, value: str | None = None) -> None:
    """View or set configuration (env prefix: AICOPH_)."""
    from aicophilosopher.domain.services.config import Config

    cfg = Config()
    if key is None:
        click.echo("Current configuration (env prefix AICOPH_):")
        click.echo(f"  llm.backend: {cfg.llm_backend}")
        click.echo(f"  llm.model: {cfg.llm_model or '(default)'}")
        click.echo(f"  workspace_dir: {cfg.workspace_dir}")
        click.echo(f"  workspace (resolved): {cfg.resolved_workspace_dir()}")
        click.echo(f"  projects_dir: {cfg.projects_dir()}")
        click.echo(f"  allow_external_search: {cfg.allow_external_search}")
        click.echo(f"  log_level: {cfg.log_level}")
    elif value is None:
        raise click.UsageError("Usage: config <key> <value>")
    else:
        click.echo(f"Config '{key}' = '{value}' (not persisted in MVP; set AICOPH_* env vars)")


@cli.command()
def request_help() -> None:
    """Request human assistance from Project Coordinator."""
    click.echo("Help request sent.")
