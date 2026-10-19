"""Architecture / layering tests for JARVIS.

These tests use AST-level import analysis (no actual module execution)
to enforce architectural boundaries between layers.

All rules that cannot yet be satisfied — because the refactoring is planned
for P4 / P7 — are marked xfail(strict=True). When a phase cleans up the
violation, remove the corresponding xfail marker and the test will pass.

Layers enforced here:
  - core/ must not import from actions/
  - core/ must not import from ui/ (except via the future ui_port protocol)
  - domain modules must not import PyQt6 directly

Reference:
  DEVELOPMENT_PHASES.md § P2 (architecture rules)
  DEVELOPMENT_PHASES.md § P4 (planned cleanup)
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

# Repo root = parent of tests/
REPO_ROOT = Path(__file__).parent.parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _collect_imports(source_path: Path) -> list[str]:
    """Return a list of all top-level module names imported in *source_path*.

    Handles both ``import foo`` and ``from foo import bar``.
    Works at AST level — no import execution.
    """
    try:
        src = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        src = source_path.read_text(encoding="cp1252", errors="replace")

    try:
        tree = ast.parse(src, filename=str(source_path))
    except SyntaxError:
        return []

    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def _files_in(directory: str) -> list[Path]:
    """Return all .py files directly under *directory* (non-recursive)."""
    return list((REPO_ROOT / directory).glob("*.py"))


def _any_file_imports_prefix(directory: str, prefix: str) -> list[str]:
    """Return a list of '<file>: <module>' strings where files in *directory*
    import any module starting with *prefix*."""
    violations = []
    for py_file in _files_in(directory):
        imports = _collect_imports(py_file)
        bad = [m for m in imports if m == prefix or m.startswith(prefix + ".")]
        for m in bad:
            violations.append(f"{py_file.name}: {m}")
    return violations


# ─────────────────────────────────────────────────────────────────────────────
# Network-guard sanity check (always green — P2 criterion)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.architecture
def test_network_is_blocked_in_tests():
    """Attempting a real TCP connection must raise RuntimeError.

    This validates that the conftest block_network fixture is active.
    """
    import socket

    with pytest.raises((RuntimeError, OSError)):
        s = socket.socket()
        s.connect(("8.8.8.8", 53))


# ─────────────────────────────────────────────────────────────────────────────
# Rule 1: core/ must not import from actions/
# (xfail: violation exists in core/jarvis_live.py — planned fix in P4)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.architecture
@pytest.mark.xfail(
    strict=True,
    reason=(
        "P4 target: core/jarvis_live.py currently imports directly from actions/ "
        "(open_app, weather_report, reminder, etc.). "
        "These will be replaced by dispatcher calls in P3/P4. "
        "Remove xfail once core/ has zero direct action imports."
    ),
)
def test_core_does_not_import_actions():
    """core/ modules must not import from actions/ (layering rule)."""
    violations = _any_file_imports_prefix("core", "actions")
    assert not violations, (
        "core/ imports actions/ — violates layering:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 2: core/ must not import from ui/ (except via ui_port)
# (xfail: core/jarvis_live.py imports ui.screen_overlay, ui.tray_indicator)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.architecture
@pytest.mark.xfail(
    strict=True,
    reason=(
        "P4 target: core/jarvis_live.py imports from ui/ directly. "
        "UiPort protocol will replace these in P4. "
        "Remove xfail once all ui imports in core/ go through ui_port."
    ),
)
def test_core_does_not_import_ui():
    """core/ modules must not import from ui/ directly (use UiPort instead)."""
    violations = []
    for py_file in _files_in("core"):
        # ui_port.py itself is allowed (it defines the protocol)
        if py_file.name == "ui_port.py":
            continue
        imports = _collect_imports(py_file)
        bad = [m for m in imports if m == "ui" or m.startswith("ui.")]
        for m in bad:
            violations.append(f"{py_file.name}: {m}")

    assert not violations, (
        "core/ imports ui/ directly — violates layering:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 3: domain modules (actions/, agent/, memory/) must not import PyQt6
# (xfail: verify current state — may already be clean)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.architecture
def test_domain_does_not_import_pyqt6():
    """actions/, agent/, memory/ must not import PyQt6.

    PyQt6 belongs only in ui/ and main.py.
    This rule is expected to be ALREADY SATISFIED — no xfail.
    """
    violations: list[str] = []
    for domain in ("actions", "agent", "memory"):
        violations.extend(_any_file_imports_prefix(domain, "PyQt6"))

    assert not violations, (
        "Domain layer imports PyQt6 directly:\n"
        + "\n".join(f"  {v}" for v in violations)
    )
