"""Tests: Coordinator propose_workstream runs agents and exposes results (Issue #60).

Also verifies disk persistence of Coordinator workstream results (Issue #83).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aicophilosopher.application.orchestration.coordinator import ProjectCoordinatorAgent
from aicophilosopher.application.services.workstream_runner import (
    SUPPORTED_WORKSTREAM_TYPES,
    normalize_workstream_type,
    run_workstream_agent,
    summarize_agent_result,
)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate Config().projects_dir() under tmp_path for every test."""
    monkeypatch.setenv("AICOPH_WORKSPACE_DIR", str(tmp_path))
    return tmp_path


def _project_dir(workspace: Path, project_id: str) -> Path:
    return workspace / "projects" / project_id


def _seed_project(workspace: Path, project_id: str) -> Path:
    """Create a minimal project skeleton matching CLI new-project layout."""
    proj = _project_dir(workspace, project_id)
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "metadata.json").write_text(
        json.dumps(
            {
                "project_id": project_id,
                "title": "Test Project",
                "status": "created",
                "workstreams": {},
                "hypotheses": [],
            }
        ),
        encoding="utf-8",
    )
    (proj / "living_document.md").write_text(
        f"# Test Project\n\n## Introduction\n\nDraft for {project_id}.\n",
        encoding="utf-8",
    )
    (proj / "hypotheses.jsonl").touch()
    (proj / "workstreams").mkdir(exist_ok=True)
    return proj


async def _approve(coord: ProjectCoordinatorAgent) -> None:
    for _ in range(5):
        result = await coord.run("test inquiry")
        if result.get("dialogue_state") == "goal_proposed":
            break
    await coord.run(command="approve_goal")
    assert coord.get_dialogue_state() == "goal_approved"


@pytest.mark.asyncio
async def test_propose_workstream_runs_literature_search_agent(
    workspace: Path,
) -> None:
    pid = "test-proj-60"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)

    result = await coord.run(command="propose_workstream", workstream_type="literature_search")

    assert "error" not in result
    assert result["status"] == "completed"
    assert "agent_result" in result
    agent = result["agent_result"]
    assert "result_count" in agent
    assert "bibliography" in agent

    ws_id = result["workstream_id"]
    assert ws_id in coord.active_workstreams
    stored = coord.active_workstreams[ws_id]
    assert stored["status"] == "completed"
    assert stored["agent_result"] is not None


@pytest.mark.asyncio
async def test_propose_workstream_all_supported_types(workspace: Path) -> None:
    """Each supported workstream type produces a completed agent result."""
    types = [
        "literature_search",
        "concept_analysis",
        "argumentation",
        "critical_review",
        "cross_traditional",
        "cross_traditional_comparison",
        "synthesis",
    ]
    for ws_type in types:
        pid = f"proj-{ws_type}"
        _seed_project(workspace, pid)
        coord = ProjectCoordinatorAgent(project_id=pid)
        await _approve(coord)
        result = await coord.run(command="propose_workstream", workstream_type=ws_type)
        assert "error" not in result, f"{ws_type}: {result}"
        assert result["status"] == "completed", f"{ws_type}: {result}"
        assert result.get("agent_result"), f"{ws_type}: missing agent_result"
        assert not result["agent_result"].get("error"), f"{ws_type}: {result['agent_result']}"


@pytest.mark.asyncio
async def test_status_and_logs_show_agent_results(workspace: Path) -> None:
    pid = "test-proj-logs"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)

    launch = await coord.run(command="propose_workstream", workstream_type="argumentation")
    ws_id = launch["workstream_id"]

    status = await coord.run(command="status")
    assert any(ws_id in line for line in status["active_workstreams"])
    assert any("completed" in line for line in status["active_workstreams"])

    logs_all = await coord.run(command="logs", workstream_id="")
    assert ws_id in logs_all["summary"]
    assert "arguments=" in logs_all["summary"]

    logs_one = await coord.run(command="logs", workstream_id=ws_id)
    assert logs_one.get("agent_result") is not None
    assert "arguments" in logs_one["agent_result"]
    assert "Result:" in logs_one["summary"]


@pytest.mark.asyncio
async def test_unknown_workstream_type_fails_gracefully(workspace: Path) -> None:
    pid = "test-proj-unknown"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)

    result = await coord.run(command="propose_workstream", workstream_type="not_a_real_type")
    assert result["status"] == "failed"
    assert result["agent_result"].get("error")
    # Failed agent runs must not write disk artefacts.
    proj = _project_dir(workspace, pid)
    assert list((proj / "workstreams").glob("*_report.md")) == []
    assert list((proj / "workstreams").glob("*_result.json")) == []


@pytest.mark.asyncio
async def test_workstream_runner_offline_literature_search() -> None:
    result = await run_workstream_agent(
        "literature_search", "What is free will?", agent_id="t-runner"
    )
    assert "error" not in result
    assert result["result_count"] >= 0
    summary = summarize_agent_result("literature_search", result)
    assert "results=" in summary


def test_normalize_cross_traditional_alias() -> None:
    assert normalize_workstream_type("cross_traditional") == "cross_traditional_comparison"
    assert "cross_traditional_comparison" in SUPPORTED_WORKSTREAM_TYPES


def test_agent_confidence_reads_overall_and_synthesis() -> None:
    conf = ProjectCoordinatorAgent._agent_confidence
    assert conf({"confidence": 0.9}) == 0.9
    assert conf({"overall_confidence": 0.42}) == 0.42
    assert conf({"synthesis_confidence": 0.33}) == 0.33
    # preferred order: confidence before overall
    assert conf({"confidence": 0.1, "overall_confidence": 0.9}) == 0.1
    assert conf({}) == 0.6


# ── Issue #83: Coordinator → disk persistence ───────────────────────────


@pytest.mark.asyncio
async def test_propose_workstream_persists_to_disk(workspace: Path) -> None:
    """Coordinator propose → metadata / report / result.json / living_document."""
    pid = "test-proj-83-persist"
    proj = _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)

    result = await coord.run(command="propose_workstream", workstream_type="concept_analysis")

    assert "error" not in result
    assert result["status"] == "completed"
    assert result.get("persistence") is not None
    ws_id = result["workstream_id"]
    assert result["persistence"]["workstream_id"] == ws_id

    # metadata.json: workstreams / hypotheses updated
    meta = json.loads((proj / "metadata.json").read_text(encoding="utf-8"))
    assert ws_id in meta["workstreams"]
    assert meta["workstreams"][ws_id]["status"] == "completed"
    assert meta["workstreams"][ws_id]["type"] == "concept_analysis"
    assert isinstance(meta["hypotheses"], list)
    assert meta["status"] == "active"

    # workstreams/*_report.md and *_result.json
    report = proj / "workstreams" / f"{ws_id}_report.md"
    result_json = proj / "workstreams" / f"{ws_id}_result.json"
    assert report.exists(), f"missing report: {report}"
    assert result_json.exists(), f"missing result json: {result_json}"
    payload = json.loads(result_json.read_text(encoding="utf-8"))
    assert payload["workstream_id"] == ws_id
    assert payload["type"] == "concept_analysis"
    assert "result" in payload

    # living_document.md updated with workstream section
    doc = (proj / "living_document.md").read_text(encoding="utf-8")
    assert "Workstream: concept_analysis" in doc
    assert ws_id in doc

    # User-facing message mentions persistence
    assert "Persisted:" in result["message"]


@pytest.mark.asyncio
async def test_propose_workstream_literature_search_persists(
    workspace: Path,
) -> None:
    """literature_search path also writes CLI-equivalent artefacts."""
    pid = "test-proj-83-lit"
    proj = _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)

    result = await coord.run(command="propose_workstream", workstream_type="literature_search")
    assert result["status"] == "completed"
    ws_id = result["workstream_id"]

    meta = json.loads((proj / "metadata.json").read_text(encoding="utf-8"))
    assert ws_id in meta["workstreams"]
    assert (proj / "workstreams" / f"{ws_id}_report.md").exists()
    assert (proj / "workstreams" / f"{ws_id}_result.json").exists()
    doc = (proj / "living_document.md").read_text(encoding="utf-8")
    assert "Workstream: literature_search" in doc


@pytest.mark.asyncio
async def test_persist_failure_does_not_pretend_success(workspace: Path) -> None:
    """When persist_workstream_results raises, status/message report the error."""
    pid = "test-proj-83-fail"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)

    with patch(
        "aicophilosopher.application.orchestration.coordinator.persist_workstream_results",
        side_effect=OSError("disk full"),
    ):
        result = await coord.run(command="propose_workstream", workstream_type="argumentation")

    assert result["status"] == "failed"
    assert "error" in result
    assert "disk full" in result["error"]
    assert "failed to persist" in result["message"].lower()
    # Agent itself succeeded — failure is persistence only
    assert result.get("agent_result") is not None
    assert not result["agent_result"].get("error")
    stored = coord.active_workstreams[result["workstream_id"]]
    assert stored["status"] == "failed"
    assert stored.get("persistence_error") is not None
    assert "disk full" in stored["persistence_error"]


def test_project_dir_uses_config_projects_dir(workspace: Path) -> None:
    pid = "test-proj-dir"
    coord = ProjectCoordinatorAgent(project_id=pid)
    assert coord._project_dir() == workspace / "projects" / pid


# ── Issue #85: OpenCode bridge status surfaced in REPL messages ──────────


def _attach_bridge(coord: ProjectCoordinatorAgent, response: dict[str, Any]) -> MagicMock:
    """Wire a mock external_bridge that returns ``response`` from request()."""
    bridge = MagicMock()
    bridge.request = AsyncMock(return_value=response)
    coord.external_bridge = bridge
    return bridge


@pytest.mark.asyncio
async def test_propose_workstream_surfaces_bridge_success(workspace: Path) -> None:
    """Bridge success shows OpenCode Go response preview in the message."""
    pid = "test-proj-85-success"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)
    _attach_bridge(
        coord,
        {
            "status": "success",
            "data": {
                "status": "completed",
                "output": "Bridge found three relevant sources on free will.",
            },
        },
    )

    result = await coord.run(command="propose_workstream", workstream_type="literature_search")

    assert result["status"] == "completed"
    assert "OpenCode Go response:" in result["message"]
    assert "three relevant sources" in result["message"]
    assert result.get("bridge_result", {}).get("status") == "success"
    stored = coord.active_workstreams[result["workstream_id"]]
    assert stored["bridge_result"]["status"] == "success"


@pytest.mark.asyncio
async def test_propose_workstream_surfaces_bridge_error(workspace: Path) -> None:
    """Outer success wrapping data.status=error must still show the reason."""
    pid = "test-proj-85-error"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)
    _attach_bridge(
        coord,
        {
            "status": "success",
            "data": {
                "status": "error",
                "output": "OpenCode Go exited 1: auth failed",
            },
        },
    )

    result = await coord.run(command="propose_workstream", workstream_type="concept_analysis")

    assert "OpenCode Go: error" in result["message"]
    assert "auth failed" in result["message"]
    # Local agent still completes independently of bridge failure.
    assert result["status"] == "completed"
    assert result.get("bridge_result", {}).get("status") == "success"


@pytest.mark.asyncio
async def test_propose_workstream_surfaces_bridge_timeout(workspace: Path) -> None:
    pid = "test-proj-85-timeout"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)
    _attach_bridge(
        coord,
        {
            "status": "success",
            "data": {
                "status": "timeout",
                "output": "OpenCode Go task timed out (120s).",
            },
        },
    )

    result = await coord.run(command="propose_workstream", workstream_type="argumentation")

    assert "OpenCode Go: timeout" in result["message"]
    assert "timed out" in result["message"]


@pytest.mark.asyncio
async def test_propose_workstream_surfaces_consent_denied(workspace: Path) -> None:
    pid = "test-proj-85-consent"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)
    _attach_bridge(
        coord,
        {
            "status": "consent_denied",
            "data": {},
            "error": "Consent not granted for scope 'workstream_delegation'",
        },
    )

    result = await coord.run(command="propose_workstream", workstream_type="critical_review")

    assert "OpenCode Go: consent_denied" in result["message"]
    assert "workstream_delegation" in result["message"]


@pytest.mark.asyncio
async def test_propose_workstream_surfaces_fallback(workspace: Path) -> None:
    pid = "test-proj-85-fallback"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)
    _attach_bridge(
        coord,
        {
            "status": "fallback",
            "data": {},
            "message": "External bridge 'opencode_go' unavailable.",
            "error": "Bridge 'opencode_go' is disabled",
        },
    )

    result = await coord.run(command="propose_workstream", workstream_type="synthesis")

    assert "OpenCode Go: fallback" in result["message"]
    assert "disabled" in result["message"]


@pytest.mark.asyncio
async def test_propose_workstream_surfaces_bridge_exception(workspace: Path) -> None:
    """Bare exceptions become status=exception and appear in the message."""
    pid = "test-proj-85-exc"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)
    bridge = MagicMock()
    bridge.request = AsyncMock(side_effect=RuntimeError("connection reset"))
    coord.external_bridge = bridge

    result = await coord.run(command="propose_workstream", workstream_type="literature_search")

    assert "OpenCode Go: exception" in result["message"]
    assert "connection reset" in result["message"]
    assert result.get("bridge_result", {}).get("status") == "exception"
    # Local agent still runs despite bridge exception.
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_logs_include_bridge_non_success(workspace: Path) -> None:
    """logs command shows bridge failure text, not only agent summary."""
    pid = "test-proj-85-logs"
    _seed_project(workspace, pid)
    coord = ProjectCoordinatorAgent(project_id=pid)
    await _approve(coord)
    _attach_bridge(
        coord,
        {
            "status": "fallback",
            "data": {},
            "error": "Bridge offline",
            "message": "Fell back to internal execution",
        },
    )

    launch = await coord.run(command="propose_workstream", workstream_type="argumentation")
    ws_id = launch["workstream_id"]

    logs_all = await coord.run(command="logs", workstream_id="")
    assert "OpenCode Go: fallback" in logs_all["summary"]

    logs_one = await coord.run(command="logs", workstream_id=ws_id)
    assert "OpenCode Go: fallback" in logs_one["summary"]
    assert logs_one.get("bridge_result", {}).get("status") == "fallback"


def test_format_bridge_section_none_is_empty() -> None:
    assert ProjectCoordinatorAgent._format_bridge_section(None) == ""


def test_format_bridge_section_status_none() -> None:
    text = ProjectCoordinatorAgent._format_bridge_section({"status": "none", "data": {}})
    assert "OpenCode Go: none" in text
