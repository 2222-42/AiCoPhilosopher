"""Coverage-boosting tests for domain services (T-070).

Targets LogicEngine, TraditionManager, CoreDomains, exceptions
to achieve ≥80% coverage on core domain logic.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aicophilosopher.domain.exceptions import (
    AICoPhilosopherError,
    ConfigurationError,
    IncommensurabilityError,
    ReviewDeadlockError,
    WorkstreamError,
)
from aicophilosopher.domain.services.core_domains import CoreDomains
from aicophilosopher.domain.services.logic_engine import LogicEngine
from aicophilosopher.domain.services.tradition_manager import DEFAULT_DOMAINS, TraditionManager


class TestLogicEngineCoverage:
    def test_check_validity_empty_premises(self) -> None:
        engine = LogicEngine()
        result = engine.check_validity([], "Socrates is mortal")
        assert result["is_valid"] is False
        assert "No premises" in result["counter_model"]

    def test_check_validity_barbara_syllogism(self) -> None:
        engine = LogicEngine()
        result = engine.check_validity(
            ["All M are P", "All S are M"], "All S are P"
        )
        assert result["is_valid"] is True

    def test_check_validity_invalid_syllogism(self) -> None:
        engine = LogicEngine()
        result = engine.check_validity(
            ["All P are M", "All S are M"], "All S are P"
        )
        assert result["is_valid"] is False

    def test_check_validity_non_syllogism(self) -> None:
        engine = LogicEngine()
        result = engine.check_validity(
            ["It is raining", "If it rains the ground is wet"],
            "The ground is wet",
        )
        assert result["is_valid"] is False

    def test_detect_contradiction_single_formula(self) -> None:
        engine = LogicEngine()
        result = engine.detect_contradiction(["All A are B"])
        assert result["has_contradiction"] is False

    def test_detect_contradiction_syllogistic(self) -> None:
        engine = LogicEngine()
        result = engine.detect_contradiction(["All A are B", "No A are B"])
        assert result["has_contradiction"] is True

    def test_detect_contradiction_negation_pair(self) -> None:
        engine = LogicEngine()
        result = engine.detect_contradiction(["It is raining", "Not it is raining"])
        assert result["has_contradiction"] is True

    def test_detect_contradiction_no_contradiction(self) -> None:
        engine = LogicEngine()
        result = engine.detect_contradiction(["It is raining", "The ground is wet"])
        assert result["has_contradiction"] is False

    def test_parse_no_form(self) -> None:
        engine = LogicEngine()
        result = engine._parse_syllogism_form("Some weird text")
        assert result is None

    def test_parse_some_form(self) -> None:
        engine = LogicEngine()
        result = engine._parse_syllogism_form("Some S are P")
        assert result == ("some", "S", "P")

    def test_z3_contradiction_no_z3(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When z3 is not importable, fall back gracefully."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "z3":
                raise ImportError("no z3")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        engine = LogicEngine()
        result = engine._check_z3_contradiction(["p", "not p"])
        assert result["has_contradiction"] is False
        assert result["confidence"] == 0.0


class TestTraditionManagerCoverage:
    def test_load_nonexistent_dir(self, tmp_path: Path) -> None:
        tm = TraditionManager(traditions_dir=tmp_path / "missing")
        profiles = tm.load_traditions()
        assert profiles == {}

    def test_validate_unknown_tradition(self) -> None:
        tm = TraditionManager()
        violations = tm.validate_argument("some text", "nonexistent")
        assert "Unknown tradition" in violations[0]

    def test_check_incommensurability_no_match(self) -> None:
        tm = TraditionManager()
        is_incomm, msg = tm.check_incommensurability("foo", "bar")
        assert is_incomm is False
        assert msg == ""

    def test_get_nonexistent_profile(self) -> None:
        tm = TraditionManager()
        profile = tm.get_tradition_profile("nonexistent")
        assert profile is None

    def test_default_domains_list(self) -> None:
        assert "analytic" in DEFAULT_DOMAINS
        assert "continental" in DEFAULT_DOMAINS
        assert "philosophy_of_technology" in DEFAULT_DOMAINS
        assert "philosophy_of_mathematics" in DEFAULT_DOMAINS
        assert "software_architecture" in DEFAULT_DOMAINS
        assert len(DEFAULT_DOMAINS) >= 5


class TestCoreDomainsCoverage:
    def test_get_unknown_domain(self) -> None:
        result = CoreDomains.get("nonexistent")
        assert result is None

    def test_get_known_domain(self) -> None:
        result = CoreDomains.get("philosophy_of_mathematics")
        assert result is not None
        assert result["key"] == "philosophy_of_mathematics"
        assert "sub_traditions" in result
        assert "expansion_terms" in result

    def test_list_all(self) -> None:
        domains = CoreDomains.list_all()
        assert len(domains) >= 4  # at minimum core domains present
        keys = {d["key"] for d in domains}
        assert "philosophy_of_mathematics" in keys
        assert "logic" in keys
        # Sorted by priority descending
        assert domains[0]["priority"] >= domains[-1]["priority"]

    def test_get_expansion_terms_unknown(self) -> None:
        terms = CoreDomains.get_expansion_terms("nonexistent")
        assert terms == []

    def test_get_expansion_terms_known(self) -> None:
        terms = CoreDomains.get_expansion_terms("logic")
        assert len(terms) > 0

    def test_get_sub_traditions_unknown(self) -> None:
        subs = CoreDomains.get_sub_traditions("nonexistent")
        assert subs == []

    def test_get_sub_traditions_known(self) -> None:
        subs = CoreDomains.get_sub_traditions("philosophy_of_mathematics")
        assert "logicism" in subs
        assert "formalism" in subs

    def test_get_all_keywords(self) -> None:
        keywords = CoreDomains.get_all_keywords()
        assert "mathematics" in keywords
        assert "logic" in keywords
        assert len(keywords) > 20

    def test_detect_no_match(self) -> None:
        results = CoreDomains.detect("xyzzy fnoord blarg")
        assert results == []

    def test_detect_math_query(self) -> None:
        results = CoreDomains.detect("What is a theorem in set theory?")
        assert len(results) > 0
        keys = {r["key"] for r in results}
        assert "philosophy_of_mathematics" in keys


class TestExceptions:
    def test_aico_philosopher_error(self) -> None:
        err = AICoPhilosopherError("base error")
        assert str(err) == "base error"

    def test_workstream_error(self) -> None:
        WorkstreamError("ws error")  # verify construction does not raise

    def test_review_deadlock_error(self) -> None:
        err = ReviewDeadlockError(
            workstream_id="ws-2", round_number=5, message="deadlocked"
        )
        assert err.workstream_id == "ws-2"
        assert err.round_number == 5

    def test_incommensurability_error(self) -> None:
        err = IncommensurabilityError("incomm")
        assert isinstance(err, AICoPhilosopherError)

    def test_configuration_error(self) -> None:
        err = ConfigurationError("bad config")
        assert isinstance(err, AICoPhilosopherError)
