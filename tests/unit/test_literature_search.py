"""Unit tests for LiteratureSearchAgent and search source-status honesty (#68)."""

from __future__ import annotations

from typing import Any

import pytest

from aicophilosopher.infrastructure.adapters.search_adapter import (
    SOURCE_STATUS_LIVE,
    SOURCE_STATUS_OFFLINE,
    SOURCE_STATUS_STUB,
    SOURCE_STATUS_UNIMPLEMENTED,
    SearchTool,
)


@pytest.fixture
def offline_search_tool() -> SearchTool:
    """Default: external search disabled (consent + config off)."""
    return SearchTool(allow_external=False)


@pytest.fixture
def agent(offline_search_tool: SearchTool) -> Any:
    from aicophilosopher.application.agents.literature_search import (
        LiteratureSearchAgent,
    )

    return LiteratureSearchAgent(agent_id="test-lit-001", search_tool=offline_search_tool)


class TestSourceStatusHonesty:
    """#68 (b): disclose live / stub / offline / unimplemented; no fake SEP URLs."""

    def test_source_statuses_offline_mode(self, offline_search_tool: SearchTool) -> None:
        statuses = offline_search_tool.get_source_statuses()
        assert statuses["semantic_scholar"] == SOURCE_STATUS_OFFLINE
        assert statuses["arxiv"] == SOURCE_STATUS_OFFLINE
        assert statuses["philpapers"] == SOURCE_STATUS_STUB
        assert statuses["sep"] == SOURCE_STATUS_STUB
        assert statuses["iep"] == SOURCE_STATUS_UNIMPLEMENTED

    def test_source_statuses_when_external_allowed(self) -> None:
        tool = SearchTool(allow_external=True)
        statuses = tool.get_source_statuses()
        assert statuses["semantic_scholar"] == SOURCE_STATUS_LIVE
        assert statuses["arxiv"] == SOURCE_STATUS_LIVE
        assert statuses["philpapers"] == SOURCE_STATUS_STUB
        assert statuses["sep"] == SOURCE_STATUS_STUB
        assert statuses["iep"] == SOURCE_STATUS_UNIMPLEMENTED

    @pytest.mark.asyncio
    async def test_sep_does_not_return_fabricated_plato_urls(
        self, offline_search_tool: SearchTool
    ) -> None:
        results = await offline_search_tool.query_sep("consciousness")
        assert results == []
        for item in results:
            url = str(item.get("url", ""))
            assert "plato.stanford.edu" not in url, (
                f"SEP must not fabricate plato.stanford.edu URLs, got {url!r}"
            )

    @pytest.mark.asyncio
    async def test_sep_empty_even_with_external_consent(self) -> None:
        tool = SearchTool(allow_external=True)
        results = await tool.query_sep("free will")
        assert results == []
        for item in results:
            assert "plato.stanford.edu" not in str(item.get("url", ""))

    @pytest.mark.asyncio
    async def test_philpapers_is_empty_stub(self, offline_search_tool: SearchTool) -> None:
        results = await offline_search_tool.query_philpapers("intentionality")
        assert results == []
        assert offline_search_tool.get_source_statuses()["philpapers"] == SOURCE_STATUS_STUB

    @pytest.mark.asyncio
    async def test_offline_search_results_mark_source_status(
        self, offline_search_tool: SearchTool
    ) -> None:
        results = await offline_search_tool.search("abstraction")
        assert len(results) >= 1
        for r in results:
            assert r.get("source") == "offline"
            assert r.get("source_status") == SOURCE_STATUS_OFFLINE
            assert "plato.stanford.edu" not in str(r.get("url", ""))


class TestLiteratureSearchAgent:
    @pytest.mark.asyncio
    async def test_agent_exposes_source_statuses(self, agent: Any) -> None:
        result = await agent.run("abstraction", traditions=["analytic", "continental"])
        assert "source_statuses" in result
        statuses = result["source_statuses"]
        assert statuses["philpapers"] == SOURCE_STATUS_STUB
        assert statuses["sep"] == SOURCE_STATUS_STUB
        assert statuses["iep"] == SOURCE_STATUS_UNIMPLEMENTED
        assert statuses["semantic_scholar"] == SOURCE_STATUS_OFFLINE
        assert statuses["arxiv"] == SOURCE_STATUS_OFFLINE

    @pytest.mark.asyncio
    async def test_bibliography_entries_include_source_status(self, agent: Any) -> None:
        result = await agent.run("truth", traditions=["analytic"])
        assert result["result_count"] >= 1
        for entry in result["bibliography"]:
            assert "source" in entry
            assert "source_status" in entry
            assert entry["source_status"] in {
                SOURCE_STATUS_LIVE,
                SOURCE_STATUS_STUB,
                SOURCE_STATUS_OFFLINE,
                SOURCE_STATUS_UNIMPLEMENTED,
            }
            assert "plato.stanford.edu" not in str(entry.get("url", ""))

    @pytest.mark.asyncio
    async def test_offline_fallback(self, agent: Any) -> None:
        result = await agent.run("consciousness")
        assert "bibliography" in result
        assert result["result_count"] >= 1
        assert all(e.get("source") == "offline" for e in result["bibliography"])

    @pytest.mark.asyncio
    async def test_bridge_note_generation(self, agent: Any) -> None:
        """≥1 bridge note per cross-traditional query (AC-002)."""
        result = await agent.run(
            "mind",
            traditions=["analytic", "continental"],
        )
        assert len(result.get("bridge_notes", [])) >= 1

    @pytest.mark.asyncio
    async def test_bibliography_relevance_scores(self, agent: Any) -> None:
        result = await agent.run("computation", traditions=["analytic"])
        for entry in result["bibliography"]:
            score = entry.get("relevance_score")
            assert isinstance(score, (int, float))
            assert 0.0 <= float(score) <= 1.0
