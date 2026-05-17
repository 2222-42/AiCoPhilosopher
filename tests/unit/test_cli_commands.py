"""CLI command tests for T-035.

Exercises all Click command definitions with CliRunner.
"""

from click.testing import CliRunner

from aicophilosopher.presentation.commands import cli

runner = CliRunner()


def test_new_project() -> None:
    result = runner.invoke(cli, ["new-project", "Test Project"])
    assert result.exit_code == 0
    assert "Project created" in result.output


def test_new_project_with_question() -> None:
    result = runner.invoke(cli, ["new-project", "Free Will", "-q", "Do we have free will?"])
    assert result.exit_code == 0
    assert "Free Will" in result.output


def test_list_projects() -> None:
    result = runner.invoke(cli, ["list-projects"])
    assert result.exit_code == 0


def test_open_project() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["new-project", "TestOpen"])
        assert result.exit_code == 0
        # Extract project ID from output
        import re
        m = re.search(r"ID: (proj-\w+)", result.output)
        if m:
            result = runner.invoke(cli, ["open-project", m.group(1)])
            assert result.exit_code == 0
            assert "Opened project" in result.output


def test_archive_project() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["new-project", "ToArchive"])
        assert result.exit_code == 0
        import re
        m = re.search(r"ID: (proj-\w+)", result.output)
        if m:
            result = runner.invoke(cli, ["archive-project", m.group(1)], input="y\n")
            assert result.exit_code == 0


def test_refine_goal() -> None:
    # Create a project first so refine-goal has context
    runner.invoke(cli, ["new-project", "Test"])
    result = runner.invoke(cli, ["refine-goal"], input="analytic\nepistemology\nPlato\nclear argument\n")
    assert result.exit_code == 0
    assert "refine" in result.output.lower() or "Refine" in result.output


def test_start_workstream() -> None:
    # Create a project first so start-workstream has context
    runner.invoke(cli, ["new-project", "Test"])
    result = runner.invoke(cli, ["start-workstream", "literature_search"])
    assert result.exit_code == 0
    assert "literature_search" in result.output


def test_start_workstream_invalid_type() -> None:
    result = runner.invoke(cli, ["start-workstream", "invalid_type"])
    assert result.exit_code != 0


def test_pause_resume() -> None:
    result = runner.invoke(cli, ["pause", "ws-001"])
    assert result.exit_code == 0
    result = runner.invoke(cli, ["resume", "ws-001"])
    assert result.exit_code == 0


def test_steer() -> None:
    result = runner.invoke(cli, ["steer", "ws-001", "Focus on compatibilism"])
    assert result.exit_code == 0
    assert "Focus" in result.output


def test_show_hypotheses() -> None:
    result = runner.invoke(cli, ["show-hypotheses"])
    assert result.exit_code == 0


def test_show_hypotheses_filter() -> None:
    result = runner.invoke(cli, ["show-hypotheses", "--status", "active"])
    assert result.exit_code == 0


def test_show_hypotheses_invalid_filter() -> None:
    result = runner.invoke(cli, ["show-hypotheses", "--status", "invalid"])
    assert result.exit_code != 0


def test_show_dead_ends() -> None:
    result = runner.invoke(cli, ["show-dead-ends"])
    assert result.exit_code == 0
    assert "dead" in result.output.lower()


def test_add_note() -> None:
    result = runner.invoke(cli, ["add-note", "Important insight", "--attach-to", "hyp-001"])
    assert result.exit_code == 0
    assert "hyp-001" in result.output
    assert "note-" in result.output


def test_compare_traditions() -> None:
    result = runner.invoke(cli, ["compare-traditions", "mind"])
    assert result.exit_code == 0
    assert "mind" in result.output


def test_status() -> None:
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "Project:" in result.output or "Status:" in result.output


def test_show_document() -> None:
    result = runner.invoke(cli, ["show-document"])
    assert result.exit_code == 0


def test_config_no_args() -> None:
    result = runner.invoke(cli, ["config"])
    assert result.exit_code == 0
    assert "configuration" in result.output.lower()


def test_config_with_args() -> None:
    result = runner.invoke(cli, ["config", "llm.backend", "claude"])
    assert result.exit_code == 0


def test_request_help() -> None:
    result = runner.invoke(cli, ["request-help"])
    assert result.exit_code == 0


def test_help() -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
