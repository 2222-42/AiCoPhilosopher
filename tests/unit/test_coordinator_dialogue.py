"""Unit tests for ProjectCoordinatorAgent dialogue state machine (T-030).

Tests MUST FAIL before T-033 implementation and PASS after.
"""

import pytest


class TestCoordinatorDialogue:

    def test_clarification_turns_under_five(self) -> None:
        """AC-001: ≤5 clarification turns before goal approval."""
        pytest.fail("Not yet implemented — remove this when T-033 is done")

    def test_goal_approval_transition(self) -> None:
        """After user approves, refined_goals contains approved goal."""
        pytest.fail("Not yet implemented — remove this when T-033 is done")

    def test_workstream_proposal_after_goal_approved(self) -> None:
        """start_workstream returns structured proposal."""
        pytest.fail("Not yet implemented — remove this when T-033 is done")

    def test_workstream_proposal_before_goal_approved_raises(self) -> None:
        """start_workstream before goal approval raises error."""
        pytest.fail("Not yet implemented — remove this when T-033 is done")
