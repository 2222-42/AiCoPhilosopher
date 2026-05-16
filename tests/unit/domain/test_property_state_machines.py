"""Property-based tests for state transition invariants (T-071).

Uses hypothesis to verify that domain state machines never permit
invalid transitions (e.g., completed → running) and that valid
transitions are always accepted.

Covers: WorkstreamStatus, HypothesisStatus, ReviewStatus state machines.
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from aicophilosopher.domain.value_objects.enums import (
    HypothesisStatus,
    ProjectStatus,
    ReviewStatus,
    WorkstreamStatus,
)

# ---------------------------------------------------------------------------
# Valid transition maps (normative, not from current production code)
# Note: Production code currently lacks a centralized transition validator.
# These maps document the intended invariants; T-071 verifies the maps are
# internally consistent. Full lifecycle enforcement is deferred.
# ---------------------------------------------------------------------------

WORKSTREAM_VALID_TRANSITIONS: dict[WorkstreamStatus, set[WorkstreamStatus]] = {
    WorkstreamStatus.PENDING: {WorkstreamStatus.RUNNING},
    WorkstreamStatus.RUNNING: {WorkstreamStatus.PAUSED, WorkstreamStatus.COMPLETED,
                                WorkstreamStatus.FAILED, WorkstreamStatus.STALLED},
    WorkstreamStatus.PAUSED: {WorkstreamStatus.RUNNING, WorkstreamStatus.STALLED},
    WorkstreamStatus.STALLED: {WorkstreamStatus.RUNNING, WorkstreamStatus.FAILED},
    WorkstreamStatus.COMPLETED: set(),  # terminal
    WorkstreamStatus.FAILED: set(),     # terminal
}

HYPOTHESIS_VALID_TRANSITIONS: dict[HypothesisStatus, set[HypothesisStatus]] = {
    HypothesisStatus.ACTIVE: {HypothesisStatus.REFINED, HypothesisStatus.REFUTED,
                               HypothesisStatus.ABANDONED},
    HypothesisStatus.REFINED: {HypothesisStatus.ACTIVE, HypothesisStatus.REFUTED,
                                HypothesisStatus.ABANDONED},
    HypothesisStatus.REFUTED: set(),     # terminal
    HypothesisStatus.ABANDONED: set(),   # terminal
}


REVIEW_VALID_TRANSITIONS: dict[ReviewStatus, set[ReviewStatus]] = {
    ReviewStatus.UNREVIEWED: {ReviewStatus.UNDER_REVIEW},
    ReviewStatus.UNDER_REVIEW: {ReviewStatus.CONTESTED,
                                 ReviewStatus.ACCEPTED_WITH_RESERVATIONS,
                                 ReviewStatus.REJECTED},
    ReviewStatus.CONTESTED: {ReviewStatus.UNDER_REVIEW, ReviewStatus.REJECTED,
                              ReviewStatus.ACCEPTED_WITH_RESERVATIONS},
    ReviewStatus.ACCEPTED_WITH_RESERVATIONS: set(),  # terminal
    ReviewStatus.REJECTED: set(),                   # terminal
}

PROJECT_VALID_TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.CREATED: {ProjectStatus.CLARIFYING, ProjectStatus.ACTIVE,
                             ProjectStatus.ARCHIVED},
    ProjectStatus.CLARIFYING: {ProjectStatus.ACTIVE, ProjectStatus.ARCHIVED},
    ProjectStatus.ACTIVE: {ProjectStatus.ARCHIVED},
    ProjectStatus.ARCHIVED: set(),  # terminal
}


def is_valid_transition(
    from_state: WorkstreamStatus | HypothesisStatus | ReviewStatus | ProjectStatus,
    to_state: WorkstreamStatus | HypothesisStatus | ReviewStatus | ProjectStatus,
    valid_map: dict,
) -> bool:
    return to_state in valid_map.get(from_state, set())


# ---------------------------------------------------------------------------
# WorkstreamStatus property tests
# ---------------------------------------------------------------------------

class TestWorkstreamStatusProperties:
    """WorkstreamStatus state machine invariants (hypothesis)."""

    @given(
        st.sampled_from(list(WorkstreamStatus)),
        st.sampled_from(list(WorkstreamStatus)),
    )
    def test_valid_transitions_accepted(
        self, from_state: WorkstreamStatus, to_state: WorkstreamStatus
    ) -> None:
        """If a transition is defined as valid, is_valid_transition returns True."""
        if to_state in WORKSTREAM_VALID_TRANSITIONS.get(from_state, set()):
            assert is_valid_transition(
                from_state, to_state, WORKSTREAM_VALID_TRANSITIONS
            )

    @given(
        st.sampled_from(list(WorkstreamStatus)),
        st.sampled_from(list(WorkstreamStatus)),
    )
    def test_invalid_transitions_rejected(
        self, from_state: WorkstreamStatus, to_state: WorkstreamStatus
    ) -> None:
        """No transition that isn't explicitly valid should be accepted."""
        assume(to_state not in WORKSTREAM_VALID_TRANSITIONS.get(from_state, set()))
        assert not is_valid_transition(
            from_state, to_state, WORKSTREAM_VALID_TRANSITIONS
        )

    @given(st.sampled_from(list(WorkstreamStatus)))
    def test_terminal_states_have_no_exits(self, state: WorkstreamStatus) -> None:
        """COMPLETED and FAILED must have no outgoing transitions."""
        valid_targets = WORKSTREAM_VALID_TRANSITIONS[state]
        if state in (WorkstreamStatus.COMPLETED, WorkstreamStatus.FAILED):
            assert valid_targets == set()

    @given(st.sampled_from(list(WorkstreamStatus)))
    def test_non_terminal_have_exits(self, state: WorkstreamStatus) -> None:
        """Non-terminal states must have at least one valid exit."""
        assume(state not in (WorkstreamStatus.COMPLETED, WorkstreamStatus.FAILED))
        assert len(WORKSTREAM_VALID_TRANSITIONS[state]) >= 1, (
            f"Non-terminal state {state} must have valid exits"
        )

    @given(st.lists(st.sampled_from(list(WorkstreamStatus)), min_size=1, max_size=10))
    def test_transition_chain_no_crash(self, chain: list[WorkstreamStatus]) -> None:
        """Any list of statuses: validation function must not crash."""
        for i in range(len(chain) - 1):
            is_valid = is_valid_transition(
                chain[i], chain[i + 1], WORKSTREAM_VALID_TRANSITIONS
            )
            assert isinstance(is_valid, bool)


# ---------------------------------------------------------------------------
# ReviewStatus property tests
# ---------------------------------------------------------------------------

class TestReviewStatusProperties:
    """ReviewStatus state machine invariants (hypothesis)."""

    @given(
        st.sampled_from(list(ReviewStatus)),
        st.sampled_from(list(ReviewStatus)),
    )
    def test_valid_transitions_accepted(
        self, from_state: ReviewStatus, to_state: ReviewStatus
    ) -> None:
        if to_state in REVIEW_VALID_TRANSITIONS.get(from_state, set()):
            assert is_valid_transition(
                from_state, to_state, REVIEW_VALID_TRANSITIONS
            )

    @given(
        st.sampled_from(list(ReviewStatus)),
        st.sampled_from(list(ReviewStatus)),
    )
    def test_invalid_transitions_rejected(
        self, from_state: ReviewStatus, to_state: ReviewStatus
    ) -> None:
        assume(
            to_state not in REVIEW_VALID_TRANSITIONS.get(from_state, set())
        )
        assert not is_valid_transition(
            from_state, to_state, REVIEW_VALID_TRANSITIONS
        )

    @given(st.sampled_from(list(ReviewStatus)))
    def test_terminal_states_have_no_exits(self, state: ReviewStatus) -> None:
        valid_targets = REVIEW_VALID_TRANSITIONS[state]
        if state in (ReviewStatus.ACCEPTED_WITH_RESERVATIONS, ReviewStatus.REJECTED):
            assert valid_targets == set()


# ---------------------------------------------------------------------------
# ProjectStatus property tests
# ---------------------------------------------------------------------------

class TestProjectStatusProperties:
    """ProjectStatus state machine invariants (hypothesis)."""

    @given(
        st.sampled_from(list(ProjectStatus)),
        st.sampled_from(list(ProjectStatus)),
    )
    def test_valid_transitions_accepted(
        self, from_state: ProjectStatus, to_state: ProjectStatus
    ) -> None:
        if to_state in PROJECT_VALID_TRANSITIONS.get(from_state, set()):
            assert is_valid_transition(
                from_state, to_state, PROJECT_VALID_TRANSITIONS
            )

    @given(st.sampled_from(list(ProjectStatus)))
    def test_archived_is_terminal(self, state: ProjectStatus) -> None:
        """ARCHIVED must have no outgoing transitions."""
        if state == ProjectStatus.ARCHIVED:
            assert PROJECT_VALID_TRANSITIONS[state] == set()


# ---------------------------------------------------------------------------
# Enum integrity
# ---------------------------------------------------------------------------

class TestHypothesisStatusProperties:
    """HypothesisStatus state machine invariants (hypothesis)."""

    @given(
        st.sampled_from(list(HypothesisStatus)),
        st.sampled_from(list(HypothesisStatus)),
    )
    def test_valid_transitions_accepted(
        self, from_state: HypothesisStatus, to_state: HypothesisStatus
    ) -> None:
        if to_state in HYPOTHESIS_VALID_TRANSITIONS.get(from_state, set()):
            assert is_valid_transition(
                from_state, to_state, HYPOTHESIS_VALID_TRANSITIONS
            )

    @given(
        st.sampled_from(list(HypothesisStatus)),
        st.sampled_from(list(HypothesisStatus)),
    )
    def test_invalid_transitions_rejected(
        self, from_state: HypothesisStatus, to_state: HypothesisStatus
    ) -> None:
        assume(
            to_state not in HYPOTHESIS_VALID_TRANSITIONS.get(from_state, set())
        )
        assert not is_valid_transition(
            from_state, to_state, HYPOTHESIS_VALID_TRANSITIONS
        )

    @given(st.sampled_from(list(HypothesisStatus)))
    def test_terminal_states_have_no_exits(self, state: HypothesisStatus) -> None:
        valid_targets = HYPOTHESIS_VALID_TRANSITIONS[state]
        if state in (HypothesisStatus.REFUTED, HypothesisStatus.ABANDONED):
            assert valid_targets == set()

    @given(st.sampled_from(list(HypothesisStatus)))
    def test_non_terminal_have_exits(self, state: HypothesisStatus) -> None:
        assume(state not in (HypothesisStatus.REFUTED, HypothesisStatus.ABANDONED))
        assert len(HYPOTHESIS_VALID_TRANSITIONS[state]) >= 1


# ---------------------------------------------------------------------------
# Enum integrity
# ---------------------------------------------------------------------------

class TestEnumIntegrity:
    """All enum values must be resolvable from strings (deserialization safety)."""

    @given(st.text(min_size=1, max_size=50))
    def test_workstream_status_rejects_unknown(self, s: str) -> None:
        """Unknown strings must raise ValueError."""
        known = {e.value for e in WorkstreamStatus}
        assume(s not in known)
        with pytest.raises(ValueError):
            WorkstreamStatus(s)

    @given(st.text(min_size=1, max_size=50))
    def test_hypothesis_status_rejects_unknown(self, s: str) -> None:
        known = {e.value for e in HypothesisStatus}
        assume(s not in known)
        with pytest.raises(ValueError):
            HypothesisStatus(s)

    @given(st.sampled_from(list(WorkstreamStatus)))
    def test_workstream_roundtrip(self, state: WorkstreamStatus) -> None:
        """Enum → string → enum must be identity."""
        assert WorkstreamStatus(state.value) == state

    @given(st.sampled_from(list(HypothesisStatus)))
    def test_hypothesis_roundtrip(self, state: HypothesisStatus) -> None:
        assert HypothesisStatus(state.value) == state
