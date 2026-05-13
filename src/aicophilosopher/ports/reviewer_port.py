from typing import Protocol


class ReviewerPort(Protocol):
    async def request_review(self, workstream_id: str, report_path: str, **kwargs: object) -> str:
        ...

    async def submit_verdict(self, review_request_id: str, verdict: dict[str, object]) -> bool:
        ...
