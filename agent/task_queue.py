import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any

from agent.execution_types import ExecutionResult, ExecutionStatus

# Maximum number of terminal tasks to keep in _tasks before evicting oldest.
_MAX_TASKS = 100


class TaskStatus(Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"  # alias/compat — equivalent to SUCCEEDED
    FAILED     = "failed"
    ABORTED    = "aborted"    # V1: step-level abort decision
    PARTIAL    = "partial"    # V1: some non-critical steps failed/skipped
    CANCELLED  = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.ABORTED,
            TaskStatus.PARTIAL,
            TaskStatus.CANCELLED,
        )


class TaskPriority(Enum):
    LOW    = 3
    NORMAL = 2
    HIGH   = 1


@dataclass(order=True)
class Task:
    priority:    int
    created_at:  float = field(compare=False)
    task_id:     str   = field(compare=False)
    goal:        str   = field(compare=False)
    status:      TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    result:      Any        = field(compare=False, default=None)
    error:       str        = field(compare=False, default="")
    steps:       list       = field(compare=False, default_factory=list)
    speak:       Any        = field(compare=False, default=None)
    on_complete: Any        = field(compare=False, default=None)
    cancel_flag: threading.Event = field(compare=False, default_factory=threading.Event)


class TaskQueue:
    def __init__(self, max_concurrent: int = 1):
        self._queue:         list[Task]       = []
        self._lock:          threading.Lock   = threading.Lock()
        self._condition:     threading.Condition = threading.Condition(self._lock)
        self._tasks:         dict[str, Task]  = {}
        self._running:       bool             = False
        self._worker_thread: threading.Thread | None = None
        self._max_concurrent = max_concurrent
        self._active_count   = 0
        self._executor       = None

    def _get_executor(self):
        if self._executor is None:
            from agent.executor import AgentExecutor
            self._executor = AgentExecutor()
        return self._executor

    def start(self) -> None:
        if self._running:
            return
        self._running       = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="AgentTaskQueue"
        )
        self._worker_thread.start()
        print("[TaskQueue] ✅ Started")

    def stop(self) -> None:
        self._running = False
        with self._condition:
            self._condition.notify_all()
        print("[TaskQueue] 🔴 Stopped")

    def submit(
        self,
        goal:        str,
        priority:    TaskPriority = TaskPriority.NORMAL,
        speak:       Callable | None = None,
        on_complete: Callable | None = None,
    ) -> str:
        task_id = str(uuid.uuid4())[:8]
        task = Task(
            priority    = priority.value,
            created_at  = time.time(),
            task_id     = task_id,
            goal        = goal,
            speak       = speak,
            on_complete = on_complete,
        )

        with self._condition:
            self._queue.append(task)
            self._queue.sort(key=lambda t: (t.priority, t.created_at))
            self._tasks[task_id] = task
            self._evict_if_needed()
            self._condition.notify()

        print(f"[TaskQueue] 📥 Task queued: [{task_id}] {goal[:60]}")
        return task_id

    def _evict_if_needed(self) -> None:
        """Evict oldest tasks when _tasks exceeds _MAX_TASKS.

        Must be called under self._lock.
        Prefers terminal tasks; if none or not enough, evicts oldest tasks.
        """
        if len(self._tasks) <= _MAX_TASKS:
            return
        terminal_ids = [
            (t.created_at, tid)
            for tid, t in self._tasks.items()
            if t.status.is_terminal
        ]
        terminal_ids.sort()  # oldest first
        to_remove = len(self._tasks) - _MAX_TASKS
        for _, tid in terminal_ids[:to_remove]:
            del self._tasks[tid]

        # If still exceeding _MAX_TASKS (e.g. all pending in unit tests), evict oldest remaining
        if len(self._tasks) > _MAX_TASKS:
            excess = len(self._tasks) - _MAX_TASKS
            all_oldest = sorted((t.created_at, tid) for tid, t in self._tasks.items())
            for _, tid in all_oldest[:excess]:
                del self._tasks[tid]

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status.is_terminal:
                return False

            task.cancel_flag.set()
            task.status = TaskStatus.CANCELLED

            # Remove from the pending queue so the worker doesn't pick it up
            try:
                self._queue.remove(task)
            except ValueError:
                pass

            print(f"[TaskQueue] 🚫 Task cancelled: [{task_id}]")
            return True

    def get_status(self, task_id: str) -> dict | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            return {
                "task_id": task.task_id,
                "goal":    task.goal,
                "status":  task.status.value,
                "result":  task.result,
                "error":   task.error,
                "steps":   task.steps,
            }

    def get_all_statuses(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "task_id": t.task_id,
                    "goal":    t.goal[:50],
                    "status":  t.status.value,
                }
                for t in self._tasks.values()
            ]

    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._queue if t.status == TaskStatus.PENDING)

    def _worker_loop(self) -> None:
        while self._running:
            task = None

            with self._condition:
                while self._running and not self._next_task():
                    self._condition.wait(timeout=1.0)
                task = self._next_task()
                if task:
                    task.status = TaskStatus.RUNNING
                    self._active_count += 1
                    try:
                        self._queue.remove(task)
                    except ValueError:
                        pass

            if task:
                threading.Thread(
                    target=self._run_task,
                    args=(task,),
                    daemon=True,
                    name=f"AgentTask-{task.task_id}"
                ).start()

    def _next_task(self) -> Task | None:
        if self._active_count >= self._max_concurrent:
            return None
        for task in self._queue:
            if task.status == TaskStatus.PENDING and not task.cancel_flag.is_set():
                return task
        return None

    def _run_task(self, task: Task) -> None:
        print(f"[TaskQueue] ▶️ Running: [{task.task_id}] {task.goal[:60]}")
        try:
            executor = self._get_executor()
            result: ExecutionResult | str = executor.execute(
                goal        = task.goal,
                speak       = task.speak,
                cancel_flag = task.cancel_flag,
            )

            with self._lock:
                if task.cancel_flag.is_set():
                    task.status = TaskStatus.CANCELLED
                elif isinstance(result, ExecutionResult):
                    # Map ExecutionStatus → TaskStatus
                    mapping = {
                        ExecutionStatus.SUCCEEDED: TaskStatus.COMPLETED,
                        ExecutionStatus.PARTIAL:   TaskStatus.PARTIAL,
                        ExecutionStatus.FAILED:    TaskStatus.FAILED,
                        ExecutionStatus.ABORTED:   TaskStatus.ABORTED,
                        ExecutionStatus.CANCELLED: TaskStatus.CANCELLED,
                    }
                    task.status = mapping.get(result.status, TaskStatus.FAILED)
                    task.result = result.summary
                    task.error  = result.error or ""
                    task.steps  = list(result.steps)
                else:
                    # Legacy: executor returned a plain string
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                self._active_count -= 1

            if task.on_complete and not task.cancel_flag.is_set():
                try:
                    task.on_complete(task.task_id, task.result)
                except Exception as e:
                    print(f"[TaskQueue] ⚠️ on_complete callback error: {e}")

            print(f"[TaskQueue] ✅ Done [{task.task_id}] status={task.status.value}")

        except Exception as e:
            with self._lock:
                task.status = TaskStatus.FAILED
                task.error  = str(e)
                self._active_count -= 1
            print(f"[TaskQueue] ❌ Failed: [{task.task_id}] {e}")

        with self._condition:
            self._condition.notify()


_queue         = TaskQueue()
_queue_started = False
_queue_lock    = threading.Lock()


def get_queue() -> TaskQueue:
    global _queue_started
    with _queue_lock:
        if not _queue_started:
            _queue.start()
            _queue_started = True
    return _queue