"""Unit tests for actions/file_controller.py — path resolution and safety.

Focuses on _is_safe_path and _resolve_path without touching the filesystem.
Side-effect actions (copy, move, delete) are NOT tested here (sidefx marker).
"""

import pytest
from pathlib import Path
from unittest.mock import patch

# We import the internals under test directly
from actions.file_controller import _is_safe_path, _resolve_path


class TestIsSafePath:
    """_is_safe_path must reject anything outside Path.home()."""

    def test_home_itself_is_safe(self):
        assert _is_safe_path(Path.home()) is True

    def test_child_of_home_is_safe(self):
        assert _is_safe_path(Path.home() / "Documents" / "report.pdf") is True

    def test_deeply_nested_in_home_is_safe(self):
        assert _is_safe_path(Path.home() / "a" / "b" / "c" / "d.txt") is True

    def test_system_root_is_rejected(self):
        assert _is_safe_path(Path("C:/Windows/System32")) is False

    def test_temp_dir_is_rejected(self):
        assert _is_safe_path(Path("C:/Windows/Temp")) is False

    def test_path_traversal_attempt(self):
        # A crafted path that looks like it starts inside home but escapes
        evil = Path.home() / ".." / ".." / "Windows" / "System32"
        assert _is_safe_path(evil) is False


class TestResolvePath:
    """_resolve_path must expand known shortcuts and fall back to raw Path."""

    def test_shortcut_desktop(self):
        result = _resolve_path("desktop")
        # Must be an absolute path under home or XDG
        assert result.is_absolute() or str(result).startswith(str(Path.home()))

    def test_shortcut_downloads(self):
        result = _resolve_path("downloads")
        assert isinstance(result, Path)

    def test_shortcut_documents(self):
        result = _resolve_path("documents")
        assert isinstance(result, Path)

    def test_shortcut_pictures(self):
        result = _resolve_path("pictures")
        assert isinstance(result, Path)

    def test_shortcut_music(self):
        result = _resolve_path("music")
        assert isinstance(result, Path)

    def test_shortcut_videos(self):
        result = _resolve_path("videos")
        assert isinstance(result, Path)

    def test_shortcut_home(self):
        result = _resolve_path("home")
        assert result == Path.home()

    def test_shortcut_case_insensitive(self):
        """Shortcuts are matched lowercase."""
        result_lower = _resolve_path("desktop")
        result_upper = _resolve_path("Desktop")
        assert result_lower == result_upper

    def test_raw_absolute_path_returned_as_is(self):
        raw = str(Path.home() / "myfile.txt")
        result = _resolve_path(raw)
        assert result == Path(raw).expanduser()

    def test_tilde_expanded(self):
        result = _resolve_path("~/Documents")
        assert not str(result).startswith("~")

    def test_unknown_shortcut_treated_as_literal(self):
        result = _resolve_path("nonexistent_shortcut_xyz")
        # Should not raise; returns a Path object
        assert isinstance(result, Path)
