"""Unit tests for tool dispatcher (P3 / BACKEND_SCHEMA.md §2.3-2.5 / TRD.md)."""

import time
import pytest

from core.tool_registry import ToolSpec
from core.tool_dispatcher import (
    dispatch,
    ErrorCode,
    ResultStatus,
    ToolResult,
)


def _dummy_action_success(parameters, player=None, **kwargs):
    return f"Success with {parameters.get('query')}"


def _dummy_action_empty(parameters, player=None, **kwargs):
    return None


def _dummy_action_raise(parameters, player=None, **kwargs):
    raise RuntimeError("Sensitive internal database path: /var/secret/db.sqlite")


def _dummy_action_slow(parameters, player=None, **kwargs):
    time.sleep(1.0)
    return "Finished late"


@pytest.fixture
def base_spec(monkeypatch):
    """Spec using dummy function via monkeypatched resolver."""
    spec = ToolSpec(
        name="test_tool",
        description="A test tool",
        parameters={
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query"},
            },
            "required": ["query"],
        },
        handler="tests.unit.test_tool_dispatcher:_dummy_action_success",
        timeout_s=5.0,
    )
    return spec


def test_successful_dispatch(base_spec):
    """Action returns string -> OK status and message."""
    res = dispatch(base_spec, {"query": "hello"})
    assert res.status == ResultStatus.OK
    assert "Success with hello" in res.message
    assert res.error is None
    assert res.duration_ms >= 0


def test_missing_required_parameter_validation_failed(base_spec):
    """(c) Missing required parameter -> VALIDATION_FAILED without calling action."""
    res = dispatch(base_spec, {})
    assert res.status == ResultStatus.ERROR
    assert res.error == ErrorCode.VALIDATION_FAILED
    assert "Paramètres requis manquants" in res.message


def test_action_exception_action_failed_safe_message(base_spec):
    """(d) Exception in action -> ACTION_FAILED with safe message, no internal leak."""
    failing_spec = ToolSpec(
        name="failing_tool",
        description="Fails",
        parameters={"type": "OBJECT", "properties": {}, "required": []},
        handler="tests.unit.test_tool_dispatcher:_dummy_action_raise",
        timeout_s=5.0,
    )
    res = dispatch(failing_spec, {})
    assert res.status == ResultStatus.ERROR
    assert res.error == ErrorCode.ACTION_FAILED
    assert "a échoué" in res.message
    # Verification that message is truncated/safe
    assert len(res.message) <= 4000


def test_timeout_returns_timeout_error(base_spec):
    """(e) Action exceeding timeout_s -> TIMEOUT error."""
    slow_spec = ToolSpec(
        name="slow_tool",
        description="Slow",
        parameters={"type": "OBJECT", "properties": {}, "required": []},
        handler="tests.unit.test_tool_dispatcher:_dummy_action_slow",
        timeout_s=0.1,  # Short timeout for fast test
    )
    res = dispatch(slow_spec, {})
    assert res.status == ResultStatus.ERROR
    assert res.error == ErrorCode.TIMEOUT
    assert "dépassé le délai" in res.message


def test_empty_result_returns_unverified():
    """Empty or None result -> UNVERIFIED with 'terminé, non vérifié'."""
    empty_spec = ToolSpec(
        name="empty_tool",
        description="Empty",
        parameters={"type": "OBJECT", "properties": {}, "required": []},
        handler="tests.unit.test_tool_dispatcher:_dummy_action_empty",
        timeout_s=2.0,
    )
    res = dispatch(empty_spec, {})
    assert res.status == ResultStatus.UNVERIFIED
    assert res.message == "terminé, non vérifié"


def test_internal_handler_guard():
    """Internal handlers cannot be called directly via dispatch()."""
    internal_spec = ToolSpec(
        name="internal_tool",
        description="Internal",
        parameters={"type": "OBJECT", "properties": {}, "required": []},
        handler="__internal__",
    )
    res = dispatch(internal_spec, {})
    assert res.status == ResultStatus.ERROR
    assert res.error == ErrorCode.INTERNAL


def test_invalid_handler_returns_dependency_missing():
    """Unresolvable handler path -> DEPENDENCY_MISSING error."""
    bad_spec = ToolSpec(
        name="bad_tool",
        description="Bad",
        parameters={"type": "OBJECT", "properties": {}, "required": []},
        handler="actions.non_existent_module_xyz:some_func",
    )
    res = dispatch(bad_spec, {})
    assert res.status == ResultStatus.ERROR
    assert res.error == ErrorCode.DEPENDENCY_MISSING


def test_tool_result_to_model_response():
    """to_model_response() returns retro-compatible dict with result and status."""
    tr = ToolResult(status=ResultStatus.OK, message="Action done")
    resp = tr.to_model_response()
    assert resp["result"] == "Action done"
    assert resp["status"] == "ok"
