"""Unit tests for agent/error_handler.py (Phase 5 — R-O12 fixed).

Tests use a fake Gemini response so no real API call is made.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from agent.error_handler import analyze_error, ErrorDecision


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _step(tool: str = "web_search", critical: bool = False) -> dict:
    return {
        "step": 1,
        "tool": tool,
        "description": "Test step",
        "parameters": {"query": "test"},
        "critical": critical,
    }


def _fake_model(decision: str, reason: str = "test reason") -> MagicMock:
    response_text = json.dumps({
        "decision": decision,
        "reason": reason,
        "fix_suggestion": "try something else",
        "max_retries": 1,
        "user_message": "Adjusting, sir.",
    })
    model = MagicMock()
    model.generate_content.return_value = MagicMock(text=response_text)
    return model


# ─────────────────────────────────────────────────────────────────────────────
# max_attempts = 3 (R-O12 fix)
# ─────────────────────────────────────────────────────────────────────────────

class TestMaxAttempts:
    def test_default_max_attempts_is_3(self):
        """analyze_error must force replan only at attempt >= 3 (not 2)."""
        import inspect
        sig = inspect.signature(analyze_error)
        assert sig.parameters["max_attempts"].default == 3

    def test_attempt_2_does_not_force_replan_if_max_is_3(self):
        """At attempt=2 with max_attempts=3 the LLM is still consulted."""
        with (
            patch("agent.error_handler._get_api_key", return_value="fake"),
            patch("agent.error_handler.genai") as mock_genai,
        ):
            mock_genai.GenerativeModel.return_value = _fake_model("retry")
            result = analyze_error(_step(), "some error", attempt=2, max_attempts=3)

        # Should get the LLM decision (RETRY), not a forced REPLAN
        assert result["decision"] == ErrorDecision.RETRY

    def test_attempt_3_forces_replan_without_llm(self):
        """At attempt=3 with max_attempts=3 the function short-circuits to REPLAN."""
        # No mock needed — the function must return before touching the LLM
        result = analyze_error(_step(), "some error", attempt=3, max_attempts=3)
        assert result["decision"] == ErrorDecision.REPLAN

    def test_attempt_beyond_max_forces_replan(self):
        result = analyze_error(_step(), "some error", attempt=5, max_attempts=3)
        assert result["decision"] == ErrorDecision.REPLAN


# ─────────────────────────────────────────────────────────────────────────────
# Decision mapping
# ─────────────────────────────────────────────────────────────────────────────

class TestDecisionMapping:
    def _call(self, decision_str: str, critical: bool = False) -> dict:
        with (
            patch("agent.error_handler._get_api_key", return_value="fake"),
            patch("agent.error_handler.genai") as mock_genai,
        ):
            mock_genai.GenerativeModel.return_value = _fake_model(decision_str)
            return analyze_error(_step(critical=critical), "error", attempt=1, max_attempts=3)

    def test_retry_decision(self):
        assert self._call("retry")["decision"] == ErrorDecision.RETRY

    def test_skip_decision(self):
        assert self._call("skip")["decision"] == ErrorDecision.SKIP

    def test_replan_decision(self):
        assert self._call("replan")["decision"] == ErrorDecision.REPLAN

    def test_abort_decision(self):
        assert self._call("abort")["decision"] == ErrorDecision.ABORT

    def test_unknown_decision_defaults_to_replan(self):
        assert self._call("nonsense")["decision"] == ErrorDecision.REPLAN


# ─────────────────────────────────────────────────────────────────────────────
# Critical step: SKIP must escalate to REPLAN
# ─────────────────────────────────────────────────────────────────────────────

class TestCriticalSkipEscalation:
    def test_skip_on_critical_step_becomes_replan(self):
        with (
            patch("agent.error_handler._get_api_key", return_value="fake"),
            patch("agent.error_handler.genai") as mock_genai,
        ):
            mock_genai.GenerativeModel.return_value = _fake_model("skip")
            result = analyze_error(_step(critical=True), "error", attempt=1, max_attempts=3)

        assert result["decision"] == ErrorDecision.REPLAN

    def test_skip_on_non_critical_stays_skip(self):
        with (
            patch("agent.error_handler._get_api_key", return_value="fake"),
            patch("agent.error_handler.genai") as mock_genai,
        ):
            mock_genai.GenerativeModel.return_value = _fake_model("skip")
            result = analyze_error(_step(critical=False), "error", attempt=1, max_attempts=3)

        assert result["decision"] == ErrorDecision.SKIP


# ─────────────────────────────────────────────────────────────────────────────
# LLM failure fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestLLMFailureFallback:
    def test_llm_exception_defaults_to_replan(self):
        with (
            patch("agent.error_handler._get_api_key", return_value="fake"),
            patch("agent.error_handler.genai") as mock_genai,
        ):
            mock_genai.GenerativeModel.return_value = MagicMock(
                generate_content=MagicMock(side_effect=RuntimeError("API down"))
            )
            result = analyze_error(_step(), "error", attempt=1, max_attempts=3)

        assert result["decision"] == ErrorDecision.REPLAN

    def test_bad_json_defaults_to_replan(self):
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text="not json at all")
        with (
            patch("agent.error_handler._get_api_key", return_value="fake"),
            patch("agent.error_handler.genai") as mock_genai,
        ):
            mock_genai.GenerativeModel.return_value = model
            result = analyze_error(_step(), "error", attempt=1, max_attempts=3)

        assert result["decision"] == ErrorDecision.REPLAN


# ─────────────────────────────────────────────────────────────────────────────
# generate_fix removed
# ─────────────────────────────────────────────────────────────────────────────

def test_generate_fix_removed():
    """generate_fix must not exist in error_handler after P5."""
    import agent.error_handler as eh
    assert not hasattr(eh, "generate_fix"), (
        "generate_fix was supposed to be removed in P5 but still exists."
    )
