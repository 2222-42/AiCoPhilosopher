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
    for sub in ("workstreams", "conceptual_genealogy", "artifacts",
                "margin_notes", "logs"):
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


def _require_active_project() -> str:
    """Return the current project id or abort with a non-zero exit."""
    proj_id = _get_current_project_id()
    if proj_id is None:
        raise click.ClickException(
            "No active project. Use `new-project` or `open-project` first."
        )
    proj_dir = _project_dir(proj_id)
    if not proj_dir.exists():
        raise click.ClickException(f"Project '{proj_id}' not found at {proj_dir}.")
    return proj_id


def _load_metadata(proj_id: str) -> dict[str, Any]:
    meta_path = _project_dir(proj_id) / "metadata.json"
    if not meta_path.exists():
        raise click.ClickException(f"Project '{proj_id}' has no metadata.json.")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _as_dict_list(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _failed_workstream_entry(ws_id: str, ws: dict[str, Any]) -> dict[str, Any]:
    return {
        "exploration_id": ws.get("workstream_id", ws_id),
        "goal_attempted": ws.get("goal_statement") or ws.get("type") or ws_id,
        "failure_reason": ws.get("failure_reason") or "workstream failed",
        "lessons_learned": ws.get("lessons_learned") or "",
        "timestamp": ws.get("timestamp") or ws.get("updated_at") or "",
    }


def _load_jsonl_dicts(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _load_hypotheses(proj_id: str) -> list[dict[str, Any]]:
    """Load hypotheses from metadata.json and hypotheses.jsonl.

    metadata.json is the primary current list; hypotheses.jsonl is append-only
    history. Records are de-duplicated by ``hypothesis_id`` (metadata wins).
    """
    meta = _load_metadata(proj_id)
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def _ingest(rows: list[dict[str, Any]], *, prefer_existing: bool) -> None:
        for h in rows:
            hid = str(h.get("hypothesis_id") or h.get("id") or "")
            if not hid:
                # Keep anonymous rows once; use object id for stability in-session.
                hid = f"anon-{id(h)}"
            if hid in by_id and prefer_existing:
                continue
            if hid not in by_id:
                order.append(hid)
            by_id[hid] = h

    _ingest(_as_dict_list(meta.get("hypotheses")), prefer_existing=False)
    _ingest(
        _load_jsonl_dicts(_project_dir(proj_id) / "hypotheses.jsonl"),
        prefer_existing=True,
    )
    return [by_id[hid] for hid in order]


def _load_dead_ends(proj_id: str) -> list[dict[str, Any]]:
    """Load failed explorations from project metadata and dead_ends.jsonl."""
    meta = _load_metadata(proj_id)
    dead_ends: list[dict[str, Any]] = []
    dead_ends.extend(_as_dict_list(meta.get("dead_ends")))
    dead_ends.extend(_as_dict_list(meta.get("failed_explorations")))

    workstreams = meta.get("workstreams") or {}
    if isinstance(workstreams, dict):
        for ws_id, ws in workstreams.items():
            if not isinstance(ws, dict):
                continue
            dead_ends.extend(_as_dict_list(ws.get("failed_explorations")))
            if ws.get("status") == "failed":
                dead_ends.append(_failed_workstream_entry(ws_id, ws))

    dead_ends.extend(_load_jsonl_dicts(_project_dir(proj_id) / "dead_ends.jsonl"))
    return dead_ends


def _not_implemented(feature: str, detail: str) -> None:
    """Fail loudly for CLI features that would otherwise silent no-op."""
    raise click.ClickException(
        f"{feature} is not implemented yet. {detail}"
    )


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------
@click.group(invoke_without_command=True)
@click.option("--project", "-p", help="Project ID to open directly in REPL")
@click.option("--new", "-n", "new_question", help="Create a new project with this question")
@click.option("--test-mode", is_flag=True, help="Launch REPL with mock coordinator (no LLM)")
@click.option("--backend", "-b", help="LLM backend: ollama, claude, gemini (overrides AICOPH_LLM_BACKEND)")
@click.pass_context
def cli(ctx: click.Context, project: str | None, new_question: str | None, test_mode: bool, backend: str | None) -> None:  # noqa: C901
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

    llm_port, coordinator, storage = _wire_backends(project, test_mode=test_mode, backend_override=backend)
    asyncio.run(run_repl(project_id=project, test_mode=test_mode, llm_port=llm_port, coordinator=coordinator, storage=storage))


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
        ("Which philosophical traditions are most relevant? "
         "(e.g., analytic, continental, philosophy_of_technology, "
         "philosophy_of_mathematics)"),
        ("What specific aspect of this question interests you most? "
         "(e.g., ontological, epistemological, ethical, phenomenological)"),
        ("Are there particular philosophers or texts you want to engage with?"),
        ("What would a satisfactory answer look like — a clear argument, "
         "a conceptual map, or a cross-traditional comparison?"),
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



def _print_literature_search_result(result: dict[str, Any]) -> None:
    """Print literature search results with explicit source statuses (#68)."""
    click.echo()
    click.echo("=== Literature Search ===")
    click.echo(f"Results: {result.get('result_count', 0)}")
    click.echo(f"Bridge notes: {len(result.get('bridge_notes', []))}")
    source_statuses = result.get("source_statuses") or {}
    if source_statuses:
        click.echo("Sources:")
        for name, status in source_statuses.items():
            click.echo(f"  - {name}: {status}")
    bibliography = result.get("bibliography") or []
    for entry in bibliography[:5]:
        if not isinstance(entry, dict):
            continue
        title = entry.get("title", "")
        source = entry.get("source", "")
        status = entry.get("source_status", "")
        click.echo(f"  • [{source}/{status}] {title}")


@cli.command()
@click.argument("workstream_type", type=click.Choice([
    "literature_search", "concept_analysis", "cross_traditional_comparison",
    "argumentation", "critical_review", "synthesis",
]))
@click.option("--instructions", "-i", help="Additional instructions")
@click.option("--traditions", "-t", help="Comma-separated tradition list (e.g. analytic,continental)")
def start_workstream(  # noqa: C901
    workstream_type: str, instructions: str | None = None, traditions: str | None = None
) -> None:
    """Launch a workstream using the appropriate AI agent."""
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

    import asyncio

    asyncio.run(
        _dispatch_workstream(
            workstream_type,
            proj_id,
            instructions or default_query,
            trad_list,
        )
    )
    click.echo()
    click.echo(f"Workstream '{workstream_type}' completed.")


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
        _print_literature_search_result(result)
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




async def _dispatch_workstream(
    workstream_type: str,
    proj_id: str,
    query: str,
    trad_list: list[str] | None,
) -> dict[str, Any]:
    """Run the agent, print results, persist hypotheses/document (#63)."""
    from aicophilosopher.application.services.workstream_persistence import (
        persist_workstream_results,
    )

    kwargs: dict[str, object] = {}
    if trad_list:
        kwargs["traditions"] = trad_list

    result = await _run_workstream_agent(workstream_type, proj_id, query, kwargs)
    _echo_workstream_result(workstream_type, result)

    summary = persist_workstream_results(
        project_dir=_project_dir(proj_id),
        workstream_type=workstream_type,
        result=result,
    )
    click.echo()
    click.echo(
        f"Persisted: {summary.get('hypotheses_added', 0)} hypotheses "
        f"to document/metadata (workstream {summary.get('workstream_id', '?')})."
    )
    return summary


@cli.command()
@click.argument("workstream_id")
def pause(workstream_id: str) -> None:
    """Pause a running workstream."""
    _not_implemented(
        "pause",
        f"Workstream lifecycle control is not wired yet "
        f"(requested id={workstream_id!r}). See issue #60.",
    )


@cli.command()
@click.argument("workstream_id")
def resume(workstream_id: str) -> None:
    """Resume a paused or stalled workstream."""
    _not_implemented(
        "resume",
        f"Workstream lifecycle control is not wired yet "
        f"(requested id={workstream_id!r}). See issue #60.",
    )


@cli.command()
@click.argument("workstream_id")
@click.argument("instruction")
def steer(workstream_id: str, instruction: str) -> None:
    """Direct steering of a specific workstream."""
    _not_implemented(
        "steer",
        f"Workstream steering is not wired yet "
        f"(requested id={workstream_id!r}, instruction={instruction!r}). "
        f"See issue #60.",
    )


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
@click.option("--status", "filter_status",
              type=click.Choice(["active", "abandoned", "refined", "refuted"]))
def show_hypotheses(filter_status: str | None = None) -> None:
    """Display hypothesis history from project metadata / hypotheses.jsonl."""
    proj_id = _require_active_project()
    hypotheses = _load_hypotheses(proj_id)

    if filter_status is not None:
        hypotheses = [
            h for h in hypotheses
            if str(h.get("status", "")).lower() == filter_status
        ]

    if not hypotheses:
        if filter_status is None:
            click.echo("No hypotheses recorded yet. Start a workstream to generate them.")
        else:
            click.echo(f"No hypotheses with status '{filter_status}'.")
        return

    click.echo(f"Hypotheses ({len(hypotheses)}) for project {proj_id}:")
    for h in hypotheses:
        hid = h.get("hypothesis_id") or h.get("id") or "?"
        statement = h.get("statement") or h.get("text") or ""
        status = h.get("status", "?")
        strength = h.get("strength", "?")
        confidence = h.get("confidence_score", h.get("confidence", "?"))
        origin = h.get("origin", "?")
        click.echo(
            f"  [{hid}] status={status} strength={strength} "
            f"confidence={confidence} origin={origin}"
        )
        if statement:
            click.echo(f"    {statement}")


@cli.command()
def show_dead_ends() -> None:
    """Display failed explorations from project metadata / dead_ends.jsonl."""
    proj_id = _require_active_project()
    dead_ends = _load_dead_ends(proj_id)

    if not dead_ends:
        click.echo("No dead ends recorded yet.")
        return

    click.echo(f"Dead ends ({len(dead_ends)}) for project {proj_id}:")
    for de in dead_ends:
        eid = de.get("exploration_id") or de.get("id") or "?"
        goal = de.get("goal_attempted") or de.get("goal") or ""
        reason = de.get("failure_reason") or de.get("reason") or ""
        lesson = de.get("lessons_learned") or de.get("lesson") or ""
        ts = de.get("timestamp") or ""
        click.echo(f"  [{eid}] {goal}")
        if reason:
            click.echo(f"    failure: {reason}")
        if lesson:
            click.echo(f"    lesson: {lesson}")
        if ts:
            click.echo(f"    at: {ts}")


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


@cli.command("export")
@click.argument("fmt", required=False, default="markdown",
              type=click.Choice(["markdown", "html", "latex"]))
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    help="Destination file path (default: <project>/exports/living_document.<ext>)",
)
def export_document(fmt: str = "markdown", output: Path | None = None) -> None:
    """Export living document to a file (markdown/html). latex is not implemented."""
    if fmt == "latex":
        _not_implemented(
            "export latex",
            "LaTeX export is post-MVP. Use `export markdown` or `export html`.",
        )

    proj_id = _require_active_project()
    doc_path = _project_dir(proj_id) / "living_document.md"
    if not doc_path.exists():
        raise click.ClickException(
            f"No living document found at {doc_path}."
        )
    content = doc_path.read_text(encoding="utf-8")

    if fmt == "html":
        # Minimal, honest HTML wrapper (not a full Markdown renderer).
        import html as html_lib
        escaped = html_lib.escape(content)
        title = _load_metadata(proj_id).get("title", proj_id)
        safe_title = html_lib.escape(str(title))
        content = (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8">\n'
            f"  <title>{safe_title}</title>\n"
            "</head>\n"
            "<body>\n"
            f"<pre>{escaped}</pre>\n"
            "</body>\n"
            "</html>\n"
        )
        default_name = "living_document.html"
    else:
        default_name = "living_document.md"

    if output is None:
        exports_dir = _project_dir(proj_id) / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        out_path = exports_dir / default_name
    else:
        out_path = output
        out_path.parent.mkdir(parents=True, exist_ok=True)

    out_path.write_text(content, encoding="utf-8")
    click.echo(f"Exported living document ({fmt}) to {out_path}")


@cli.command("config")
@click.argument("key", required=False)
@click.argument("value", required=False)
def config_cmd(key: str | None = None, value: str | None = None) -> None:
    """View configuration (read-only). Setting values is not persisted."""
    from aicophilosopher.domain.services.config import Config

    # Do not swallow Config errors — mis-set AICOPH_* / .env must surface.
    try:
        cfg = Config()
    except Exception as exc:
        raise click.ClickException(
            f"Failed to load configuration: {exc}. "
            "Check AICOPH_* environment variables and .env."
        ) from exc

    # Keys are shell-friendly identifiers usable with `config <key>`.
    display = {
        "llm.backend": cfg.llm_backend,
        "llm.model": cfg.llm_model or "(default)",
        "llm.temperature": cfg.llm_temperature,
        "workspace_dir": cfg.workspace_dir,
        "workspace.resolved": cfg.resolved_workspace_dir(),
        "projects_dir": cfg.projects_dir(),
        "log_level": cfg.log_level,
        "allow_external_search": cfg.allow_external_search,
        "allow_external_agents": cfg.allow_external_agents,
        "opencode_enabled": cfg.opencode_enabled,
        "hermes_enabled": cfg.hermes_enabled,
    }

    if key is None:
        click.echo("Current configuration (from env/defaults; AICOPH_*):")
        for k, v in display.items():
            click.echo(f"  {k}: {v}")
        click.echo()
        click.echo("Note: `config <key> <value>` does not persist settings.")
        click.echo("Set AICOPH_* environment variables or edit .env instead.")
        return

    if value is None:
        # Read a single key if known; otherwise usage error.
        if key in display:
            click.echo(f"{key}: {display[key]}")
            return
        raise click.UsageError(
            f"Unknown config key '{key}'. Known keys: {', '.join(display)}"
        )

    # Refuse to pretend a write succeeded.
    raise click.ClickException(
        f"Setting config is not persisted. "
        f"Refused to pretend '{key}'='{value}' was saved. "
        f"Set AICOPH_* environment variables or edit .env instead."
    )


@cli.command()
def request_help() -> None:
    """Request human assistance from Project Coordinator."""
    _not_implemented(
        "request-help",
        "Project Coordinator help-request routing is not wired for the CLI yet.",
    )
