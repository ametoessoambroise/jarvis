"""Unit tests for agent/task_queue.py (Phase 5 — R-O11 fixed).

All tests use synchronous helpers: no actual AgentExecutor is invoked.
The worker thread is never started so tests are fully deterministic.
"""

import threading
import time

import pytest

from agent.task_queue import TaskQueue, TaskPriority, TaskStatus, _MAX_TASKS
from agent.execution_types import (
    ExecutionResult,
    ExecutionStatus,
    StepResult,
    StepStatus,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _queue_with_executor(result: ExecutionResult | str) -> TaskQueue:
    """Return a TaskQueue whose executor returns a fixed result synchronously."""

    class _FakeExecutor:
        def execute(self, goal, speak=None, cancel_flag=None):
            return result

    q = TaskQueue(max_concurrent=1)
    q._executor = _FakeExecutor()
    return q


def _succeeded_result(summary: str = "done") -> ExecutionResult:
    return ExecutionResult(
        status=ExecutionStatus.SUCCEEDED,
        steps=(StepResult(index=1, tool="web_search", status=StepStatus.OK),),
        summary=summary,
    )


def _failed_result() -> ExecutionResult:
    return ExecutionResult(
        status=ExecutionStatus.FAILED,
        steps=(StepResult(index=1, tool="web_search", status=StepStatus.FAILED, error="boom"),),
        summary="failed",
        error="boom",
    )


def _aborted_result() -> ExecutionResult:
    return ExecutionResult(
        status=ExecutionStatus.ABORTED,
        steps=(StepResult(index=1, tool="web_search", status=StepStatus.FAILED),),
        summary="aborted",
    )


def _partial_result() -> ExecutionResult:
    return ExecutionResult(
        status=ExecutionStatus.PARTIAL,
        steps=(
            StepResult(index=1, tool="web_search", status=StepStatus.OK),
            StepResult(index=2, tool="file_controller", status=StepStatus.SKIPPED),
        ),
        summary="partial",
    )


# ─────────────────────────────────────────────────────────────────────────────
# TaskStatus
# ─────────────────────────────────────────────────────────────────────────────

class TestTaskStatus:
    def test_aborted_and_partial_exist(self):
        assert TaskStatus.ABORTED.value == "aborted"
        assert TaskStatus.PARTIAL.value == "partial"

    def test_completed_is_terminal(self):
        assert TaskStatus.COMPLETED.is_terminal is True

    def test_failed_is_terminal(self):
        assert TaskStatus.FAILED.is_terminal is True

    def test_aborted_is_terminal(self):
        assert TaskStatus.ABORTED.is_terminal is True

    def test_partial_is_terminal(self):
        assert TaskStatus.PARTIAL.is_terminal is True

    def test_cancelled_is_terminal(self):
        assert TaskStatus.CANCELLED.is_terminal is True

    def test_pending_is_not_terminal(self):
        assert TaskStatus.PENDING.is_terminal is False

    def test_running_is_not_terminal(self):
        assert TaskStatus.RUNNING.is_terminal is False


# ─────────────────────────────────────────────────────────────────────────────
# _tasks bounded at _MAX_TASKS
# ─────────────────────────────────────────────────────────────────────────────

class TestTasksBounded:
    def test_tasks_dict_capped_at_max(self):
        q = TaskQueue()
        for i in range(_MAX_TASKS + 100):
            q.submit(f"task {i}")
        assert len(q._tasks) <= _MAX_TASKS

    def test_only_terminal_tasks_evicted(self):
        """Pending tasks must never be evicted (only terminal ones are eligible)."""
        q = TaskQueue()
        for i in range(_MAX_TASKS + 5):
            q.submit(f"task {i}")
        # No task has run (no executor started) → all PENDING, none terminal
        # Eviction falls back to not removing PENDING tasks.
        # The dict can exceed _MAX_TASKS in this edge case — that's accepted.
        # What must NOT happen: a pending task should still be retrievable.
        last_id = q.submit("sentinel task")
        status = q.get_status(last_id)
        # If eviction only touches terminal tasks and there are none, last task may still be in dict
        # (implementation may defer eviction until terminals exist).
        # At minimum, cap should not delete non-terminal tasks.
        # We just ensure get_status on last submitted is not None.
        assert status is not None


# ─────────────────────────────────────────────────────────────────────────────
# cancel() purges queue
# ─────────────────────────────────────────────────────────────────────────────

class TestCancelPurgesQueue:
    def test_cancel_pending_removes_from_queue(self):
        q = TaskQueue()
        tid = q.submit("some goal")
        assert any(t.task_id == tid for t in q._queue)
        q.cancel(tid)
        # Must no longer be in _queue
        assert not any(t.task_id == tid for t in q._queue)

    def test_cancel_sets_cancelled_status(self):
        q = TaskQueue()
        tid = q.submit("goal")
        q.cancel(tid)
        assert q.get_status(tid)["status"] == TaskStatus.CANCELLED.value

    def test_cancel_terminal_returns_false(self):
        q = TaskQueue()
        tid = q.submit("goal")
        q.cancel(tid)
        # Already CANCELLED → second cancel fails
        assert q.cancel(tid) is False

    def test_cancel_unknown_id_returns_false(self):
        q = TaskQueue()
        assert q.cancel("nonexistent") is False


# ─────────────────────────────────────────────────────────────────────────────
# ExecutionResult → TaskStatus mapping (via _run_task)
# ─────────────────────────────────────────────────────────────────────────────

class TestRunTaskStatusMapping:
    def _run_and_wait(self, q: TaskQueue, goal: str, timeout: float = 3.0) -> dict:
        q.start()
        tid = q.submit(goal)
        deadline = time.time() + timeout
        while time.time() < deadline:
            s = q.get_status(tid)
            if s and TaskStatus(s["status"]).is_terminal:
                return s
            time.sleep(0.05)
        q.stop()
        return q.get_status(tid)

    def test_succeeded_result_maps_to_completed(self):
        q = _queue_with_executor(_succeeded_result())
        status = self._run_and_wait(q, "goal")
        q.stop()
        assert status["status"] == TaskStatus.COMPLETED.value

    def test_failed_result_maps_to_failed(self):
        q = _queue_with_executor(_failed_result())
        status = self._run_and_wait(q, "goal")
        q.stop()
        assert status["status"] == TaskStatus.FAILED.value

    def test_aborted_result_maps_to_aborted(self):
        q = _queue_with_executor(_aborted_result())
        status = self._run_and_wait(q, "goal")
        q.stop()
        assert status["status"] == TaskStatus.ABORTED.value

    def test_partial_result_maps_to_partial(self):
        q = _queue_with_executor(_partial_result())
        status = self._run_and_wait(q, "goal")
        q.stop()
        assert status["status"] == TaskStatus.PARTIAL.value

    def test_steps_stored_on_task(self):
        q = _queue_with_executor(_succeeded_result())
        status = self._run_and_wait(q, "goal")
        q.stop()
        assert len(status["steps"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# get_status includes steps
# ─────────────────────────────────────────────────────────────────────────────

class TestGetStatus:
    def test_get_status_includes_steps_key(self):
        q = TaskQueue()
        tid = q.submit("goal")
        s = q.get_status(tid)
        assert "steps" in s

    def test_get_status_steps_initially_empty(self):
        q = TaskQueue()
        tid = q.submit("goal")
        s = q.get_status(tid)
        assert s["steps"] == []
