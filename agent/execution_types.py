from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        pass


class StepStatus(StrEnum):
    OK = "ok"
    UNVERIFIED = "unverified"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class StepResult:
    index: int
    tool: str
    status: StepStatus
    attempts: int = 1
    outputs: Mapping[str, Any] = field(default_factory=dict)
    message: str = ""
    error: str | None = None
    verification: str = "not_applicable"
    started_at: str = ""
    duration_ms: int = 0


class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    ABORTED = "aborted"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    steps: tuple[StepResult, ...]
    summary: str
    error: str | None = None
    replans: int = 0
