"""Unit tests for PhilosophicalQueryStrategy (T-048)."""

import pytest

from aicophilosopher.ports.llm_port import GenerationResult
from aicophilosopher.ports.query_port import _BULLET_PATTERN, PhilosophicalQueryStrategy


class _MockLLM:
    def __init__(self, response_text: str = "") -> None:
        self.response_text = response_text
        self.generate_calls: list[dict[str, object]] = []

    async def generate(self, prompt: str, **kwargs: object) -> GenerationResult:
        self.generate_calls.append({"prompt": prompt, "kwargs": kwargs})
        return GenerationResult(text=self.response_text, model="mock")

    async def embed(self, text: str, **kwargs: object) -> list[float]:
        return [0.1] * 10


class _FailingLLM:
    def __init__(self, exc: type[BaseException] = OSError) -> None:
        self.exc = exc

    async def generate(self, prompt: str, **kwargs: object) -> GenerationResult:
        raise self.exc("unavailable")

    async def embed(self, text: str, **kwargs: object) -> list[float]:
        raise self.exc("unavailable")


QUERY = "moving sofa problem"
BULLET_RESPONSE = "- PhilMath view on {q}\n- Logical analysis of {q}\n1. Epistemology of {q}".format  # noqa: P101


@pytest.fixture
def mock_llm() -> _MockLLM:
    return _MockLLM(response_text=BULLET_RESPONSE(q=QUERY))


@pytest.fixture
def strategy(mock_llm: _MockLLM) -> PhilosophicalQueryStrategy:
    return PhilosophicalQueryStrategy(mock_llm)


class TestDetectDomains:
    def test_detects_known_domain(self, strategy: PhilosophicalQueryStrategy) -> None:
        domains = strategy.detect_domains(QUERY)
        assert len(domains) > 0
        assert domains[0]["key"] == "philosophy_of_mathematics"

    def test_empty_for_unknown_query(self, strategy: PhilosophicalQueryStrategy) -> None:
        domains = strategy.detect_domains("xyzzy fnoord")
        assert domains == []

    def test_returns_match_strength_sorted(self, strategy: PhilosophicalQueryStrategy) -> None:
        domains = strategy.detect_domains("science and technology")
        assert len(domains) >= 2
        assert domains[0]["match_strength"] >= domains[1]["match_strength"]


class TestResolveRoutingKeys:
    def test_returns_structured_dict(self, strategy: PhilosophicalQueryStrategy) -> None:
        routing = strategy.resolve_routing_keys(QUERY)
        assert "domains" in routing
        assert "sub_traditions" in routing
        assert isinstance(routing["domains"], list)
        assert isinstance(routing["sub_traditions"], list)

    def test_includes_sub_traditions(self, strategy: PhilosophicalQueryStrategy) -> None:
        routing = strategy.resolve_routing_keys(QUERY)
        assert len(routing["sub_traditions"]) > 0
        assert "logicism" in routing["sub_traditions"]

    def test_empty_for_unknown_query(self, strategy: PhilosophicalQueryStrategy) -> None:
        routing = strategy.resolve_routing_keys("xyzzy")
        assert routing == {"domains": [], "sub_traditions": []}


class TestExpand:
    @pytest.mark.asyncio
    async def test_happy_path_with_llm(self, mock_llm: _MockLLM) -> None:
        strategy = PhilosophicalQueryStrategy(mock_llm)
        expanded = await strategy.expand(QUERY)
        assert len(expanded) > 0
        assert any("PhilMath" in q for q in expanded)
        assert len(mock_llm.generate_calls) == 1

    @pytest.mark.asyncio
    async def test_fallback_on_llm_failure(self) -> None:
        strategy = PhilosophicalQueryStrategy(_FailingLLM())
        expanded = await strategy.expand(QUERY, max_queries=3)
        assert len(expanded) >= 1
        assert QUERY in expanded[0]

    @pytest.mark.asyncio
    async def test_fallback_on_connection_error(self) -> None:
        strategy = PhilosophicalQueryStrategy(_FailingLLM(ConnectionError))
        expanded = await strategy.expand(QUERY)
        assert len(expanded) > 0

    @pytest.mark.asyncio
    async def test_empty_domains_still_invokes_llm(self) -> None:
        llm = _MockLLM(response_text="- one\n- two")
        strategy = PhilosophicalQueryStrategy(llm)
        expanded = await strategy.expand("xyzzy no keywords")
        assert len(expanded) >= 1
        assert len(llm.generate_calls) >= 1

    @pytest.mark.asyncio
    async def test_fallback_on_empty_llm_response(self) -> None:
        llm = _MockLLM(response_text="No results found.")
        strategy = PhilosophicalQueryStrategy(llm)
        expanded = await strategy.expand(QUERY)
        assert len(expanded) >= 1
        assert QUERY in expanded[0]

    @pytest.mark.asyncio
    async def test_max_queries_respected(self, mock_llm: _MockLLM) -> None:
        strategy = PhilosophicalQueryStrategy(mock_llm)
        expanded = await strategy.expand(QUERY, max_queries=2)
        assert len(expanded) <= 2

    @pytest.mark.asyncio
    async def test_max_queries_zero_clamped(self, mock_llm: _MockLLM) -> None:
        strategy = PhilosophicalQueryStrategy(mock_llm)
        expanded = await strategy.expand(QUERY, max_queries=0)
        assert len(expanded) >= 1


class TestParseExpandedQueries:
    def test_parses_dash_prefix(self) -> None:
        result = PhilosophicalQueryStrategy(_MockLLM())._parse_expanded_queries(
            "- query one\n- query two", 5
        )
        assert len(result) == 2

    def test_parses_star_prefix(self) -> None:
        result = PhilosophicalQueryStrategy(_MockLLM())._parse_expanded_queries(
            "* query one\n* query two", 5
        )
        assert len(result) == 2

    def test_parses_numbered_list(self) -> None:
        result = PhilosophicalQueryStrategy(_MockLLM())._parse_expanded_queries(
            "1. query one\n2. query two\n3) query three", 5
        )
        assert len(result) == 3

    def test_parses_bullet_with_extra_whitespace(self) -> None:
        result = PhilosophicalQueryStrategy(_MockLLM())._parse_expanded_queries(
            "-   spaced\n-    more spaces", 5
        )
        assert len(result) == 2
        assert result[0] == "spaced"

    def test_respects_max_queries(self) -> None:
        result = PhilosophicalQueryStrategy(_MockLLM())._parse_expanded_queries(
            "- a\n- b\n- c\n- d", 2
        )
        assert len(result) == 2

    def test_skips_duplicates(self) -> None:
        result = PhilosophicalQueryStrategy(_MockLLM())._parse_expanded_queries(
            "- dup\n- dup\n- unique", 5
        )
        assert len(result) == 2

    def test_ignores_garbage_lines(self) -> None:
        result = PhilosophicalQueryStrategy(_MockLLM())._parse_expanded_queries(
            "Here is text\n- real query\nMore text", 5
        )
        assert result == ["real query"]


class TestFallbackExpand:
    def test_includes_original_query(self) -> None:
        result = PhilosophicalQueryStrategy(_MockLLM())._fallback_expand("test", [], 3)
        assert result[0] == "test"

    def test_max_queries_single(self) -> None:
        result = PhilosophicalQueryStrategy(_MockLLM())._fallback_expand(
            "test", [{"display_name": "PhilMath"}, {"display_name": "Logic"}], 1
        )
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_no_domains_returns_only_query(self) -> None:
        strategy = PhilosophicalQueryStrategy(_FailingLLM())
        expanded = await strategy.expand("xyzzy")  # no domains detected
        assert expanded == ["xyzzy"]


class TestPlanPipeline:
    @pytest.mark.asyncio
    async def test_returns_expected_keys(self, mock_llm: _MockLLM) -> None:
        strategy = PhilosophicalQueryStrategy(mock_llm)
        plan = await strategy.plan_pipeline(QUERY)
        for k in (
            "original_query",
            "detected_domains",
            "routing_keys",
            "expanded_queries",
            "stages",
        ):
            assert k in plan

    @pytest.mark.asyncio
    async def test_stages_have_input_output(self, mock_llm: _MockLLM) -> None:
        strategy = PhilosophicalQueryStrategy(mock_llm)
        plan = await strategy.plan_pipeline(QUERY)
        s1 = plan["stages"]["stage1_expansion"]
        s2 = plan["stages"]["stage2_analysis"]
        assert "input" in s1 and "output" in s1
        assert "input" in s2

    @pytest.mark.asyncio
    async def test_stage1_output_is_stage2_input(self, mock_llm: _MockLLM) -> None:
        strategy = PhilosophicalQueryStrategy(mock_llm)
        plan = await strategy.plan_pipeline(QUERY)
        s1_out = plan["stages"]["stage1_expansion"]["output"]
        s2_in = plan["stages"]["stage2_analysis"]["input"]
        assert s1_out == s2_in


class TestBulletPattern:
    def test_matches_dash(self) -> None:
        assert _BULLET_PATTERN.match("- hello")

    def test_matches_star(self) -> None:
        assert _BULLET_PATTERN.match("* hello")

    def test_matches_bullet(self) -> None:
        assert _BULLET_PATTERN.match("• hello")

    def test_matches_numbered(self) -> None:
        assert _BULLET_PATTERN.match("1. hello")
        assert _BULLET_PATTERN.match("42) hello")

    def test_matches_leading_whitespace(self) -> None:
        assert _BULLET_PATTERN.match("   - hello")

    def test_rejects_plain_text(self) -> None:
        assert _BULLET_PATTERN.match("plain text") is None

    def test_extracts_content(self) -> None:
        m = _BULLET_PATTERN.match("- the content here")
        assert m is not None
        assert m.group(1) == "the content here"
