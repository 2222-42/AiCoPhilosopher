import uuid
from datetime import UTC, datetime
from typing import Any

from aicophilosopher.domain.exceptions import ReviewDeadlockError

METHODOLOGICAL_LENSES = [
    "analytic_logician",
    "phenomenological_critic",
    "continental_hermeneut",
    "buddhist_epistemologist",
    "confucian_ethicist",
]


class ReviewProcess:
    def __init__(self, workstream_id: str, min_reviewers: int = 2, max_rounds: int = 5) -> None:
        self.workstream_id = workstream_id
        self.min_reviewers = min_reviewers
        self.max_rounds = max_rounds
        self.current_round = 0
        self._rounds: dict[int, dict[str, Any]] = {}
        self._status = "pending"
        self._reviewer_lenses: list[str] = []
        self._verdicts: dict[int, list[dict[str, Any]]] = {}

    async def start_review(self, lenses: list[str] | None = None) -> str:
        self.current_round = 1
        self._status = "in_progress"
        self._reviewer_lenses = lenses or METHODOLOGICAL_LENSES[:self.min_reviewers]
        round_id = f"rev-{uuid.uuid4().hex[:8]}"
        self._rounds[self.current_round] = {
            "round_id": round_id,
            "round_number": self.current_round,
            "status": "in_progress",
            "lenses": self._reviewer_lenses,
            "started_at": datetime.now(UTC).isoformat(),
        }
        return round_id

    async def submit_verdict(self, round_number: int, verdict: dict[str, object]) -> bool:
        if round_number not in self._rounds:
            return False
        verdict_status = str(verdict.get("status", ""))
        if verdict_status not in ("approved", "approved_with_reservations", "rejected"):
            return False
        if round_number not in self._verdicts:
            self._verdicts[round_number] = []
        self._verdicts[round_number].append({
            "reviewer_id": str(verdict.get("reviewer_id", "")),
            "lens": str(verdict.get("lens", "")),
            "status": verdict_status,
            "comments": str(verdict.get("comments", "")),
            "confidence": float(str(verdict.get("confidence", 0.5))),
            "submitted_at": datetime.now(UTC).isoformat(),
        })
        return True

    async def check_completion(self) -> dict[str, Any]:
        rd = self._rounds.get(self.current_round)
        if not rd:
            return {"status": "not_started", "workstream_id": self.workstream_id}
        if self.current_round > self.max_rounds:
            rd["status"] = "escalated"
            raise ReviewDeadlockError(
                workstream_id=self.workstream_id,
                round_number=self.current_round,
                message=f"Review exceeded max rounds ({self.max_rounds}) in workstream {self.workstream_id}",
            )
        verdicts = self._verdicts.get(self.current_round, [])
        all_submitted = len(verdicts) >= self.min_reviewers
        if not all_submitted:
            return {
                "status": "in_progress",
                "current_round": self.current_round,
                "verdicts_received": len(verdicts),
                "verdicts_needed": self.min_reviewers,
                "workstream_id": self.workstream_id,
            }
        all_approved = all(
            v["status"] in ("approved", "approved_with_reservations")
            for v in verdicts
        )
        if all_approved:
            return {
                "status": "completed",
                "current_round": self.current_round,
                "verdicts": verdicts,
                "workstream_id": self.workstream_id,
            }
        if self.current_round >= self.max_rounds:
            rd["status"] = "escalated"
            raise ReviewDeadlockError(
                workstream_id=self.workstream_id,
                round_number=self.current_round,
                message=f"Review deadlocked after {self.current_round} rounds in workstream {self.workstream_id}",
            )
        self.current_round += 1
        new_round_id = f"rev-{uuid.uuid4().hex[:8]}"
        self._rounds[self.current_round] = {
            "round_id": new_round_id,
            "round_number": self.current_round,
            "status": "in_progress",
            "lenses": self._reviewer_lenses,
            "started_at": datetime.now(UTC).isoformat(),
        }
        return {
            "status": "new_round",
            "current_round": self.current_round,
            "previous_verdicts": verdicts,
            "round_id": new_round_id,
            "workstream_id": self.workstream_id,
        }

    async def escalate(self, reason: str) -> dict[str, Any]:
        if self._rounds:
            self._rounds[self.current_round]["status"] = "escalated"
        return {
            "status": "escalated",
            "workstream_id": self.workstream_id,
            "total_rounds": self.current_round,
            "reason": reason,
            "stalled": True,
        }
