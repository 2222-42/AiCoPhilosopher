"""Regression tests: PhilPapers/SEP stubs must not mislead (#68)."""

from __future__ import annotations

import pytest

from aicophilosopher.infrastructure.adapters.search_adapter import (
    SOURCE_CAPABILITIES,
    SOURCE_STATUS_LIVE,
    SOURCE_STATUS_OFFLINE,
    SOURCE_STATUS_STUB,
    SOURCE_STATUS_UNIMPLEMENTED,
    SearchTool,
)


@pytest.mark.asyncio
async def test_query_sep_never_emits_plato_urls() -> None:
    for allow in (False, True):
        tool = SearchTool(allow_external=allow)
        results = await tool.query_sep("the hard problem of consciousness")
        assert isinstance(results, list)
        assert results == [], "SEP stub must return empty results, not fabricated entries"
        for item in results:
            url = str(item.get("url", ""))
            assert not url.startswith("https://plato.stanford.edu/"), url
            assert "plato.stanford.edu" not in url


@pytest.mark.asyncio
async def test_query_philpapers_returns_empty_stub() -> None:
    tool = SearchTool(allow_external=True)
    results = await tool.query_philpapers("qualia")
    assert results == []


def test_source_capabilities_document_stub_vs_live() -> None:
    assert SOURCE_CAPABILITIES["semantic_scholar"] == SOURCE_STATUS_LIVE
    assert SOURCE_CAPABILITIES["arxiv"] == SOURCE_STATUS_LIVE
    assert SOURCE_CAPABILITIES["philpapers"] == SOURCE_STATUS_STUB
    assert SOURCE_CAPABILITIES["sep"] == SOURCE_STATUS_STUB
    assert SOURCE_CAPABILITIES["iep"] == SOURCE_STATUS_UNIMPLEMENTED


def test_offline_mode_flips_live_sources_to_offline() -> None:
    tool = SearchTool(allow_external=False)
    statuses = tool.get_source_statuses()
    assert statuses["semantic_scholar"] == SOURCE_STATUS_OFFLINE
    assert statuses["arxiv"] == SOURCE_STATUS_OFFLINE
    # Stubs stay stubs even offline — they are not "offline live APIs".
    assert statuses["philpapers"] == SOURCE_STATUS_STUB
    assert statuses["sep"] == SOURCE_STATUS_STUB
