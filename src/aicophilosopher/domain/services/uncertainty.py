from typing import Any

from aicophilosopher.domain.entities.uncertainty import UncertaintyRecord
from aicophilosopher.domain.exceptions import ValidationError
from aicophilosopher.domain.value_objects.enums import ReviewStatus


class UncertaintyLifecycle:
    def __init__(self) -> None:
        self._records: dict[str, UncertaintyRecord] = {}

    def track(self, claim: str, **kwargs: object) -> dict[str, Any]:
        claim_id = str(kwargs.get("claim_id", f"claim-{len(self._records) + 1}"))
        confidence_val = kwargs.get("confidence_score", 0.5)
        timestamp = str(kwargs.get("timestamp", ""))

        record = UncertaintyRecord(
            claim_id=claim_id,
            claim_text=claim,
            confidence_score=float(confidence_val),  # type: ignore[arg-type]
            review_status=ReviewStatus.UNREVIEWED,
            last_updated=timestamp,
        )
        self._records[record.claim_id] = record
        return record.model_dump()

    def manage(self, claim_id: str, updates: dict[str, object]) -> dict[str, Any]:
        if claim_id not in self._records:
            raise ValidationError(f"Unknown claim: {claim_id}")
        record = self._records[claim_id]
        if "confidence_score" in updates:
            record.confidence_score = float(updates["confidence_score"])  # type: ignore[arg-type]
        if "counter_argument_strength" in updates:
            record.counter_argument_strength = float(updates["counter_argument_strength"])  # type: ignore[arg-type]
        if "review_status" in updates:
            new_status = str(updates["review_status"])
            if new_status in ReviewStatus._value2member_map_:
                record.review_status = ReviewStatus(new_status)
        if "last_updated" in updates:
            record.last_updated = str(updates["last_updated"])
        return record.model_dump()

    def communicate(self, claim_id: str) -> str:
        if claim_id not in self._records:
            return ""
        record = self._records[claim_id]
        return (
            f"Source: {record.claim_id} | "
            f"Confidence: {record.confidence_score:.2f} | "
            f"Review status: {record.review_status.value} | "
            f"Counter-argument strength: {record.counter_argument_strength:.2f}"
        )

    def reject_claim(self, claim_id: str) -> dict[str, Any]:
        if claim_id not in self._records:
            raise ValidationError(f"Unknown claim: {claim_id}")
        record = self._records[claim_id]
        record.review_status = ReviewStatus.REJECTED
        stalled = record.stalled_sections
        return {"claim_id": claim_id, "stalled_sections": stalled}
