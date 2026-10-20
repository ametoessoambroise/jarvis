"""Unit tests for agent/executor.py (Phase 5).

Uses fake planner and fake tool-call machinery — no network, no real Gemini.
"""

import threading
from typing import Callable
from unittest.mock import MagicMock, patch

import pytest

from agent.execution_types import ExecutionResult, ExecutionStatus, StepStatus


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / Fakes
# ─────────────────────────────────────────────────────────────────────────────

def _single_step_plan(tool: str = "web_search", critical: bool = False) -> dict:
    return {
        "goal": "test goal",
        "steps": [
            {
                "step": 1,
                "tool": tool,
                "description": "Test step",
                "parameters": {"query": "test"},
                "critical": critical,
            }
        ],
    }


def _empty_plan() -> dict:
    return {"goal": "empty goal", "steps": []}


# ─────────────────────────────────────────────────────────────────────────────
# Test: execute returns ExecutionResult
# ─────────────────────────────────────────────────────────────────────────────

class TestExecuteReturnsExecutionResult:
    def test_success_returns_execution_result(self):
        """A successful single-step plan should return ExecutionResult with SUCCEEDED."""
        from agent.executor import AgentExecutor

        with (
            patch("agent.executor.create_plan", return_value=_single_step_plan()),
            patch("agent.executor._call_tool", return_value="ok result"),
            patch("agent.executor._build_summary", return_value="done"),
        ):
            executor = AgentExecutor()
            result = executor.execute("test goal")

        assert isinstance(result, ExecutionResult)
        assert result.status == ExecutionStatus.SUCCEEDED

    def test_result_has_steps(self):
        from agent.executor import AgentExecutor

        with (
            patch("agent.executor.create_plan", return_value=_single_step_plan()),
            patch("agent.executor._call_tool", return_value="ok"),
            patch("agent.executor._build_summary", return_value="done"),
        ):
            executor = AgentExecutor()
            result = executor.execute("test goal")

        assert len(result.steps) == 1
        assert result.steps[0].tool == "web_search"
        assert result.steps[0].status == StepStatus.OK


class TestEmptyPlanFails:
    def test_empty_plan_returns_failed(self):
        from agent.executor import AgentExecutor

        with patch("agent.executor.create_plan", return_value=_empty_plan()):
            executor = AgentExecutor()
            result = executor.execute("empty goal")

        assert isinstance(result, ExecutionResult)
        assert result.status == ExecutionStatus.FAILED


# ─────────────────────────────────────────────────────────────────────────────
# Test: SKIP is not treated as success
# ─────────────────────────────────────────────────────────────────────────────

class TestSkipIsNotSuccess:
    def test_skipped_step_status_is_skipped(self):
        """When error_handler returns SKIP, the step status must be SKIPPED, not OK."""
        from agent.executor import AgentExecutor
        from agent.error_handler import ErrorDecision

        skip_decision = {
            "decision": ErrorDecision.SKIP,
            "reason": "not critical",
            "fix_suggestion": "",
            "max_retries": 0,
            "user_message": "Skipping, sir.",
        }

        with (
            patch("agent.executor.create_plan", return_value=_single_step_plan(critical=False)),
            patch("agent.executor._call_tool", side_effect=Exception("tool error")),
            patch("agent.executor.analyze_error", return_value=skip_decision),
            patch("agent.executor._build_summary", return_value="partial done"),
        ):
            executor = AgentExecutor()
            result = executor.execute("test goal")

        assert result.steps[0].status == StepStatus.SKIPPED

    def test_skipped_step_leads_to_partial_status(self):
        """A plan where only step is SKIPPED should yield PARTIAL, not SUCCEEDED."""
        from agent.executor import AgentExecutor
        from agent.error_handler import ErrorDecision

        skip_decision = {
            "decision": ErrorDecision.SKIP,
            "reason": "not critical",
            "fix_suggestion": "",
            "max_retries": 0,
            "user_message": "Skipping, sir.",
        }

        with (
            patch("agent.executor.create_plan", return_value=_single_step_plan(critical=False)),
            patch("agent.executor._call_tool", side_effect=Exception("tool error")),
            patch("agent.executor.analyze_error", return_value=skip_decision),
            patch("agent.executor._build_summary", return_value="partial"),
        ):
            executor = AgentExecutor()
            result = executor.execute("test goal")

        assert result.status == ExecutionStatus.PARTIAL


# ─────────────────────────────────────────────────────────────────────────────
# Test: ABORT decision → ABORTED result
# ─────────────────────────────────────────────────────────────────────────────

class TestAbortDecision:
    def test_abort_returns_aborted_result(self):
        from agent.executor import AgentExecutor
        from agent.error_handler import ErrorDecision

        abort_decision = {
            "decision": ErrorDecision.ABORT,
            "reason": "impossible",
            "fix_suggestion": "",
            "max_retries": 0,
            "user_message": "Aborting, sir.",
        }

        with (
            patch("agent.executor.create_plan", return_value=_single_step_plan(critical=True)),
            patch("agent.executor._call_tool", side_effect=Exception("fatal")),
            patch("agent.executor.analyze_error", return_value=abort_decision),
        ):
            executor = AgentExecutor()
            result = executor.execute("test goal")

        assert result.status == ExecutionStatus.ABORTED


# ─────────────────────────────────────────────────────────────────────────────
# Test: cancel_flag stops execution
# ─────────────────────────────────────────────────────────────────────────────

class TestCancelFlag:
    def test_cancel_flag_set_before_execute_returns_cancelled(self):
        from agent.executor import AgentExecutor

        flag = threading.Event()
        flag.set()  # pre-cancelled

        with patch("agent.executor.create_plan", return_value=_single_step_plan()):
            executor = AgentExecutor()
            result = executor.execute("test goal", cancel_flag=flag)

        assert result.status == ExecutionStatus.CANCELLED


# ─────────────────────────────────────────────────────────────────────────────
# Test: no generate_fix (code gen removed from error loop)
# ─────────────────────────────────────────────────────────────────────────────

class TestNoGenerateFix:
    def test_generate_fix_not_imported_in_executor(self):
        """generate_fix must not be imported by executor (P5 removes it)."""
        import agent.executor as executor_module
        assert not hasattr(executor_module, "generate_fix"), (
            "generate_fix should not exist in executor module after P5"
        )

    def test_error_module_has_no_generate_fix(self):
        """generate_fix must be removed from error_handler module (P5)."""
        import agent.error_handler as eh
        assert not hasattr(eh, "generate_fix"), (
            "generate_fix should not exist in error_handler after P5"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers that may be patched
# ─────────────────────────────────────────────────────────────────────────────

def _build_summary(*args, **kwargs) -> str:
    return "summary"
