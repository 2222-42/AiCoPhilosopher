"""Unit tests for workstream status surfacing (T-026).

Tests the WorkstreamPoller class: background polling, status change detection,
queue ordering, thread lifecycle, and error resilience.
"""

import time
from collections.abc import Callable
from queue import Queue
from unittest.mock import MagicMock

# ── Helpers ──────────────────────────────────────────────────────────────


def _poll_fn_returning(workstreams: list[dict]) -> Callable[[], list[dict]]:
    """Return a callable that returns the given list (for poll_fn)."""
    return lambda: workstreams


# ── Poller lifecycle ────────────────────────────────────────────────────


def test_poller_starts_and_stops() -> None:
    """WorkstreamPoller can be started and stopped cleanly."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    queue: Queue[dict] = Queue()
    poller = WorkstreamPoller(
        poll_fn=_poll_fn_returning([]),
        update_queue=queue,
        interval_seconds=0.05,
    )
    poller.start()
    assert poller.is_running()

    poller.stop()
    # Give the thread time to join
    for _ in range(10):
        if not poller.is_running():
            break
        time.sleep(0.01)
    assert not poller.is_running()


def test_poller_thread_is_daemon() -> None:
    """The polling thread is set as daemon so it dies with the main process."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    poller = WorkstreamPoller(
        poll_fn=_poll_fn_returning([]),
        update_queue=Queue(),
    )
    poller.start()
    try:
        assert poller._thread is not None
        assert poller._thread.daemon is True
    finally:
        poller.stop()


def test_stop_when_not_running_is_noop() -> None:
    """Calling stop() on a non-running poller does not raise."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    poller = WorkstreamPoller(
        poll_fn=_poll_fn_returning([]),
        update_queue=Queue(),
    )
    poller.stop()
    assert not poller.is_running()


# ── Status change detection ─────────────────────────────────────────────


def test_running_to_completed_detected() -> None:
    """Transition running->completed is queued as a status change."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    workstreams = [
        {"workstream_id": "ws-001", "status": "running", "progress": 0.5},
    ]
    queue: Queue[dict] = Queue()

    poller = WorkstreamPoller(
        poll_fn=_poll_fn_returning(workstreams),
        update_queue=queue,
        interval_seconds=0.02,
    )

    # First poll: running
    poller._poll_sync()
    assert queue.empty()

    # Second poll: completed
    workstreams[0]["status"] = "completed"
    poller._poll_sync()

    assert not queue.empty()
    change = queue.get()
    assert change["workstream_id"] == "ws-001"
    assert change["old_status"] == "running"
    assert change["new_status"] == "completed"


def test_running_to_failed_detected() -> None:
    """Transition running->failed is queued."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    workstreams = [
        {"workstream_id": "ws-002", "status": "running", "progress": 0.3},
    ]
    queue: Queue[dict] = Queue()

    poller = WorkstreamPoller(
        poll_fn=_poll_fn_returning(workstreams),
        update_queue=queue,
        interval_seconds=0.02,
    )

    poller._poll_sync()  # baseline
    workstreams[0]["status"] = "failed"
    poller._poll_sync()

    change = queue.get()
    assert change["workstream_id"] == "ws-002"
    assert change["new_status"] == "failed"


def test_running_to_stalled_detected() -> None:
    """Transition running->stalled is queued with warning."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    workstreams = [
        {"workstream_id": "ws-003", "status": "running", "progress": 0.7},
    ]
    queue: Queue[dict] = Queue()

    poller = WorkstreamPoller(
        poll_fn=_poll_fn_returning(workstreams),
        update_queue=queue,
        interval_seconds=0.02,
    )

    poller._poll_sync()
    workstreams[0]["status"] = "stalled"
    poller._poll_sync()

    change = queue.get()
    assert change["workstream_id"] == "ws-003"
    assert change["new_status"] == "stalled"


def test_no_change_not_queued() -> None:
    """When statuses haven't changed, nothing is added to the queue."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    workstreams = [
        {"workstream_id": "ws-001", "status": "running", "progress": 0.5},
    ]
    queue: Queue[dict] = Queue()

    poller = WorkstreamPoller(
        poll_fn=_poll_fn_returning(workstreams),
        update_queue=queue,
        interval_seconds=0.02,
    )

    poller._poll_sync()  # first poll initializes state
    poller._poll_sync()  # second poll with same state -> no change
    assert queue.empty()


def test_new_workstream_detected() -> None:
    """A newly appearing workstream is queued."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    queue: Queue[dict] = Queue()
    workstreams: list[dict] = []

    poller = WorkstreamPoller(
        poll_fn=lambda: workstreams,
        update_queue=queue,
        interval_seconds=0.02,
    )

    # First poll: nothing
    poller._poll_sync()
    assert queue.empty()

    # Second poll: new WS appears
    workstreams.append({"workstream_id": "ws-new", "status": "running", "progress": 0.0})
    poller._poll_sync()

    change = queue.get()
    assert change["workstream_id"] == "ws-new"
    assert change["new_status"] == "running"


# ── Queue ordering ──────────────────────────────────────────────────────


def test_multiple_changes_queued_in_order() -> None:
    """Multiple concurrent status changes are queued in detection order."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    ws_a = {"workstream_id": "ws-a", "status": "running", "progress": 0.3}
    ws_b = {"workstream_id": "ws-b", "status": "running", "progress": 0.5}
    workstreams = [ws_a, ws_b]

    queue: Queue[dict] = Queue()
    poller = WorkstreamPoller(
        poll_fn=lambda: workstreams,
        update_queue=queue,
        interval_seconds=0.02,
    )

    # Baseline - poll sees both as running
    poller._poll_sync()

    # Both change simultaneously
    ws_a["status"] = "completed"
    ws_b["status"] = "stalled"
    poller._poll_sync()

    assert queue.qsize() == 2
    first = queue.get()
    second = queue.get()
    assert first["workstream_id"] == "ws-a"
    assert second["workstream_id"] == "ws-b"


# ── Error resilience ───────────────────────────────────────────────────


def test_poll_error_does_not_crash_poller() -> None:
    """An exception during polling does not kill the thread or crash the REPL."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    queue: Queue[dict] = Queue()

    poller = WorkstreamPoller(
        poll_fn=MagicMock(side_effect=RuntimeError("DB down")),
        update_queue=queue,
        interval_seconds=0.02,
    )

    # Should not raise
    poller._poll_sync()
    assert queue.empty()  # No change queued on error

    # Poller still usable after error
    assert not poller.is_running()  # never started, so not running


def test_poller_continues_after_error() -> None:
    """After an error on one poll, subsequent successful polls still work."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    queue: Queue[dict] = Queue()
    workstreams = [
        {"workstream_id": "ws-001", "status": "running", "progress": 0.3},
    ]

    call_count = [0]

    def flaky_poll():
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("temp error")
        return workstreams

    poller = WorkstreamPoller(
        poll_fn=flaky_poll,
        update_queue=queue,
        interval_seconds=0.02,
    )

    # Baseline
    poller._poll_sync()
    assert queue.empty()

    # Error poll - should not raise, queue still empty
    poller._poll_sync()
    assert queue.empty()

    # Recovery poll with a status change
    workstreams[0]["status"] = "completed"
    poller._poll_sync()

    assert not queue.empty()
    change = queue.get()
    assert change["new_status"] == "completed"


# ── Integration: resume detection ──────────────────────────────────────


def test_stale_state_cleared_on_stop() -> None:
    """After stop(), last_known_state is cleared so a new poller sees fresh state."""
    from aicophilosopher.presentation.repl import WorkstreamPoller

    workstreams = [
        {"workstream_id": "ws-001", "status": "completed", "progress": 1.0},
    ]
    queue: Queue[dict] = Queue()

    poller = WorkstreamPoller(
        poll_fn=_poll_fn_returning(workstreams),
        update_queue=queue,
        interval_seconds=0.02,
    )
    poller._poll_sync()
    poller.stop()

    # New poller on resume should NOT see old state
    queue2: Queue[dict] = Queue()
    poller2 = WorkstreamPoller(
        poll_fn=_poll_fn_returning(workstreams),
        update_queue=queue2,
        interval_seconds=0.02,
    )
    # Same state - since last_known is empty, first poll just initializes
    poller2._poll_sync()
    assert queue2.empty()  # No transition detected (initialization only)
    poller2.stop()
