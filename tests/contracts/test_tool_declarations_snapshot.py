"""Contract test: tool declarations snapshot must not change unintentionally.

Any intentional change to TOOL_DECLARATIONS must be reflected by updating
tests/fixtures/tool_declarations_snapshot.json via:
    python -c "import json; from core.tools import TOOL_DECLARATIONS; \
               open('tests/fixtures/tool_declarations_snapshot.json','w').write(json.dumps(TOOL_DECLARATIONS, indent=2))"
"""

import json
from pathlib import Path

import pytest

SNAPSHOT_PATH = Path(__file__).parent.parent / "fixtures" / "tool_declarations_snapshot.json"


@pytest.mark.contract
def test_tool_declarations_count():
    """There must be exactly 26 tool declarations."""
    from core.tools import TOOL_DECLARATIONS

    assert len(TOOL_DECLARATIONS) == 26, (
        f"Expected 26 tool declarations, got {len(TOOL_DECLARATIONS)}. "
        "Update snapshot if a tool was intentionally added/removed."
    )


@pytest.mark.contract
def test_tool_declarations_match_snapshot():
    """Live TOOL_DECLARATIONS must match the committed snapshot."""
    from core.tools import TOOL_DECLARATIONS

    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    live_names = sorted(d["name"] for d in TOOL_DECLARATIONS)
    snap_names = sorted(d["name"] for d in snapshot)

    assert live_names == snap_names, (
        f"Tool names differ.\n  Live only: {set(live_names) - set(snap_names)}\n"
        f"  Snapshot only: {set(snap_names) - set(live_names)}"
    )

    # Build dicts keyed by name for easier comparison
    live_by_name = {d["name"]: d for d in TOOL_DECLARATIONS}
    snap_by_name = {d["name"]: d for d in snapshot}

    mismatches = []
    for name in live_names:
        if live_by_name[name] != snap_by_name[name]:
            mismatches.append(name)

    assert not mismatches, (
        f"Tool declarations differ for: {mismatches}. "
        "Regenerate the snapshot if the change is intentional."
    )


@pytest.mark.contract
def test_all_tools_have_required_fields():
    """Every declaration must have name, description, and parameters."""
    from core.tools import TOOL_DECLARATIONS

    for decl in TOOL_DECLARATIONS:
        name = decl.get("name", "<unknown>")
        assert "name" in decl, f"Tool missing 'name' field: {decl}"
        assert "description" in decl, f"Tool '{name}' missing 'description'"
        assert "parameters" in decl, f"Tool '{name}' missing 'parameters'"
        assert isinstance(decl["description"], str) and decl["description"].strip(), (
            f"Tool '{name}' has empty description"
        )
