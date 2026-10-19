"""Contract test for tool registry (P3 / BACKEND_SCHEMA.md §2.2 / TRD.md)."""

import json
import sys
from pathlib import Path

import pytest

from core.tool_registry import _REGISTRY, ToolRegistry, ToolSpec

SNAPSHOT_PATH = Path(__file__).parent.parent / "fixtures" / "tool_declarations_snapshot.json"


@pytest.mark.contract
def test_all_26_tools_registered():
    """Exactly 26 tools must be registered in the central registry."""
    assert len(_REGISTRY) == 26


@pytest.mark.contract
def test_declaration_to_handler_mapping():
    """(a) For each of the 26 names: declaration <=> handler is defined."""
    for spec in _REGISTRY.all():
        assert spec.name, "ToolSpec must have a non-empty name"
        assert spec.handler, f"ToolSpec '{spec.name}' must have a handler"
        decl = spec.to_declaration()
        assert decl["name"] == spec.name
        assert decl["description"] == spec.description
        assert decl["parameters"] == spec.parameters


@pytest.mark.contract
def test_declarations_match_json_snapshot():
    """(b) Declarations reconstructed from registry match committed snapshot."""
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    declarations = _REGISTRY.declarations()

    live_by_name = {d["name"]: d for d in declarations}
    snap_by_name = {d["name"]: d for d in snapshot}

    assert sorted(live_by_name.keys()) == sorted(snap_by_name.keys())

    mismatches = []
    for name in live_by_name:
        if live_by_name[name] != snap_by_name[name]:
            mismatches.append(name)

    assert not mismatches, f"Mismatched declarations: {mismatches}"


@pytest.mark.contract
def test_import_tool_registry_does_not_import_actions():
    """(f) Importing core.tool_registry imports ZERO actions/* modules."""
    # Run in a clean subprocess to ensure isolated module state
    import subprocess
    cmd = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "import core.tool_registry; "
            "actions = [m for m in sys.modules if m.startswith('actions')]; "
            "assert not actions, f'Actions imported: {actions}'; "
            "print('OK')"
        ),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Subprocess failed:\nSTDOUT: {res.stdout}\nSTDERR: {res.stderr}"
    assert "OK" in res.stdout


@pytest.mark.contract
def test_executor_and_tools_use_same_registry():
    """(g) core.tools and agent.executor both use _REGISTRY."""
    from core.tools import TOOL_DECLARATIONS
    from agent.executor import _call_tool

    # TOOL_DECLARATIONS was built from _REGISTRY
    assert len(TOOL_DECLARATIONS) == len(_REGISTRY)
    assert [d["name"] for d in TOOL_DECLARATIONS] == [s.name for s in _REGISTRY.all()]


@pytest.mark.contract
def test_planner_tools_flag():
    """All planner tools have planner=True and are 16 in total."""
    planner_tools = _REGISTRY.planner_tools()
    assert len(planner_tools) == 16
    for t in planner_tools:
        assert t.planner is True
