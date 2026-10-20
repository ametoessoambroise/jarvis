"""Characterization tests for agent/task_queue.py.

These tests capture the *current observed behaviour* of TaskQueue, including
known defects. Defects are marked xfail(strict=True) so that:
  - The test passes as long as the defect exists (expected failure).
  - The test FAILS (turns into XPASS) if the defect is accidentally fixed,
    reminding us to remove the xfail marker and update docs.

R-O11 reference: TaskQueue does not cap its _tasks dict, which can grow
without bound during a long session.
"""

import threading
import time
import uuid
import pytest

from agent.task_queue import TaskQueue, TaskStatus, TaskPriority


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _noop_executor_queue() -> TaskQueue:
    """Return a TaskQueue wired to a synchronous no-op executor (no threads)."""
    q = TaskQueue(max_concurrent=1)
    # Inject a fake executor that immediately returns "ok"
    class _FakeExecutor:
        def execute(self, goal, speak=None, cancel_flag=None):
            return f"done: {goal}"
    q._executor = _FakeExecutor()
    return q


# ─────────────────────────────────────────────────────────────────────────────
# submit / get_status / pending_count
# ─────────────────────────────────────────────────────────────────────────────

class TestSubmit:
    def test_submit_returns_task_id(self):
        q = TaskQueue()
        task_id = q.submit("test goal")
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    def test_submit_increments_pending(self):
        q = TaskQueue()
        assert q.pending_count() == 0
        q.submit("goal 1")
        q.submit("goal 2")
        assert q.pending_count() == 2

    def test_get_status_returns_dict(self):
        q = TaskQueue()
        task_id = q.submit("my goal")
        status = q.get_status(task_id)
        assert status is not None
        assert status["task_id"] == task_id
        assert status["goal"] == "my goal"
        assert status["status"] == TaskStatus.PENDING.value

    def test_get_status_unknown_id_returns_none(self):
        q = TaskQueue()
        assert q.get_status("nonexistent-id") is None

    def test_get_all_statuses_returns_list(self):
        q = TaskQueue()
        q.submit("a")
        q.submit("b")
        all_s = q.get_all_statuses()
        assert len(all_s) == 2
        assert all("task_id" in s and "status" in s for s in all_s)


# ─────────────────────────────────────────────────────────────────────────────
# cancel
# ─────────────────────────────────────────────────────────────────────────────

class TestCancel:
    def test_cancel_pending_task_returns_true(self):
        q = TaskQueue()
        task_id = q.submit("to cancel")
        result = q.cancel(task_id)
        assert result is True

    def test_cancel_sets_status_cancelled(self):
        q = TaskQueue()
        task_id = q.submit("to cancel")
        q.cancel(task_id)
        status = q.get_status(task_id)
        assert status["status"] == TaskStatus.CANCELLED.value

    def test_cancel_unknown_id_returns_false(self):
        q = TaskQueue()
        assert q.cancel("does-not-exist") is False

    def test_cancel_already_cancelled_returns_false(self):
        q = TaskQueue()
        task_id = q.submit("goal")
        q.cancel(task_id)
        # Second cancel should fail — task is already CANCELLED
        assert q.cancel(task_id) is False


# ─────────────────────────────────────────────────────────────────────────────
# Priority ordering
# ─────────────────────────────────────────────────────────────────────────────

class TestPriority:
    def test_high_priority_queued_before_low(self):
        q = TaskQueue()
        low_id  = q.submit("low priority task",  priority=TaskPriority.LOW)
        high_id = q.submit("high priority task", priority=TaskPriority.HIGH)

        # The internal _queue is sorted: smaller value = higher priority
        with q._lock:
            queue_ids = [t.task_id for t in q._queue]

        assert queue_ids.index(high_id) < queue_ids.index(low_id)


# ─────────────────────────────────────────────────────────────────────────────
# start / stop lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestLifecycle:
    def test_start_is_idempotent(self):
        """Calling start() twice must not spawn two worker threads."""
        q = _noop_executor_queue()
        q.start()
        first_thread = q._worker_thread
        q.start()
        second_thread = q._worker_thread
        assert first_thread is second_thread
        q.stop()

    def test_stop_sets_running_false(self):
        q = _noop_executor_queue()
        q.start()
        q.stop()
        assert q._running is False


# ─────────────────────────────────────────────────────────────────────────────
# Known defects (xfail strict=True) — R-O11
# ─────────────────────────────────────────────────────────────────────────────

def test_tasks_dict_is_bounded():
    """The _tasks registry is capped at 100 (P5 fix for R-O11).

    Submit 200 tasks and verify that _tasks never exceeds 100 entries.
    """
    q = TaskQueue()
    for i in range(200):
        q.submit(f"task {i}")
    assert len(q._tasks) <= 100, (
        f"Expected _tasks capped at 100, got {len(q._tasks)}"
    )
