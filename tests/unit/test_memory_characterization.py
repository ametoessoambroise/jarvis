"""Characterization tests for memory/memory_manager.py.

These tests capture the *current observed behaviour* of the memory manager.
They use a temporary directory (via monkeypatching) so they never touch
the real user memory on disk.

Known defect R-O13 (no re-entrant lock / corrupt JSON recovery) is documented
as xfail(strict=True).
"""

import json
import pytest
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def mem_dir(tmp_path, monkeypatch):
    """Redirect all memory_manager I/O to a fresh temp directory.

    memory_manager sets MEMORY_PATH / MEMORY_DIR at import time from
    settings.paths.memory_dir, so we cannot use an env-var + reload approach.
    Instead we directly monkeypatch the module-level globals.
    """
    import memory.memory_manager as mm

    new_dir  = tmp_path / "memory"
    new_dir.mkdir()
    new_path = new_dir / "long_term.json"

    monkeypatch.setattr(mm, "MEMORY_DIR",  new_dir)
    monkeypatch.setattr(mm, "MEMORY_PATH", new_path)

    yield new_dir, mm


# ─────────────────────────────────────────────────────────────────────────────
# _empty_memory / load_memory
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadMemory:
    def test_returns_empty_dict_when_file_missing(self, mem_dir):
        _dir, mm = mem_dir
        result = mm.load_memory()
        assert isinstance(result, dict)
        # All 9 expected categories must be present
        expected_cats = {
            "identity", "preferences", "projects", "routines",
            "context", "skills", "relationships", "wishes", "notes",
        }
        assert set(result.keys()) == expected_cats

    def test_loads_valid_json(self, mem_dir):
        _dir, mm = mem_dir
        data = mm._empty_memory()
        data["identity"]["name"] = {"value": "Alice", "updated": "2024-01-01"}
        mm.MEMORY_PATH.write_text(json.dumps(data), encoding="utf-8")

        loaded = mm.load_memory()
        assert loaded["identity"]["name"]["value"] == "Alice"

    def test_returns_empty_on_corrupt_json(self, mem_dir):
        _dir, mm = mem_dir
        mm.MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        mm.MEMORY_PATH.write_text("NOT JSON {{{{", encoding="utf-8")

        result = mm.load_memory()
        # Must not raise; returns empty structure
        assert isinstance(result, dict)
        assert "identity" in result

    def test_missing_categories_backfilled(self, mem_dir):
        _dir, mm = mem_dir
        partial = {"identity": {"name": {"value": "Bob", "updated": "2024-01-01"}}}
        mm.MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        mm.MEMORY_PATH.write_text(json.dumps(partial), encoding="utf-8")

        loaded = mm.load_memory()
        # All 9 categories must be present even if not in file
        assert "preferences" in loaded
        assert "notes" in loaded


# ─────────────────────────────────────────────────────────────────────────────
# save_memory / atomic write
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveMemory:
    def test_save_creates_file(self, mem_dir):
        _dir, mm = mem_dir
        data = mm._empty_memory()
        mm.save_memory(data)
        assert mm.MEMORY_PATH.exists()

    def test_save_then_load_roundtrip(self, mem_dir):
        _dir, mm = mem_dir
        data = mm._empty_memory()
        data["notes"]["reminder"] = {"value": "buy milk", "updated": "2024-06-01"}
        mm.save_memory(data)

        loaded = mm.load_memory()
        assert loaded["notes"]["reminder"]["value"] == "buy milk"

    def test_save_creates_backup(self, mem_dir):
        _dir, mm = mem_dir
        data = mm._empty_memory()
        mm.save_memory(data)  # first save
        mm.save_memory(data)  # second save should create .bak
        bak = mm.MEMORY_PATH.with_suffix(".json.bak")
        assert bak.exists()

    def test_no_tmp_file_left_after_save(self, mem_dir):
        _dir, mm = mem_dir
        data = mm._empty_memory()
        mm.save_memory(data)
        tmp_file = mm.MEMORY_PATH.with_suffix(".json.tmp")
        assert not tmp_file.exists()

    def test_save_ignores_non_dict(self, mem_dir):
        mem_directory, mm = mem_dir
        # Should not raise
        mm.save_memory("not a dict")  # type: ignore
        mm.save_memory(None)          # type: ignore
        # MEMORY_PATH should not have been created by invalid inputs
        assert not mm.MEMORY_PATH.exists()


# ─────────────────────────────────────────────────────────────────────────────
# update_memory / _recursive_update
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateMemory:
    def test_update_adds_new_key(self, mem_dir):
        _dir, mm = mem_dir
        mm.update_memory({"identity": {"name": "Charlie"}})
        loaded = mm.load_memory()
        assert loaded["identity"]["name"]["value"] == "Charlie"

    def test_update_overwrites_existing_key(self, mem_dir):
        _dir, mm = mem_dir
        mm.update_memory({"identity": {"name": "Alice"}})
        mm.update_memory({"identity": {"name": "Bob"}})
        loaded = mm.load_memory()
        assert loaded["identity"]["name"]["value"] == "Bob"

    def test_update_does_not_remove_unrelated_keys(self, mem_dir):
        _dir, mm = mem_dir
        mm.update_memory({"identity": {"name": "Alice"}})
        mm.update_memory({"preferences": {"theme": "dark"}})
        loaded = mm.load_memory()
        assert loaded["identity"]["name"]["value"] == "Alice"
        assert loaded["preferences"]["theme"]["value"] == "dark"

    def test_empty_update_returns_current_memory(self, mem_dir):
        _dir, mm = mem_dir
        mm.update_memory({"identity": {"name": "Alice"}})
        result = mm.update_memory({})
        assert result["identity"]["name"]["value"] == "Alice"

    def test_long_value_is_truncated(self, mem_dir):
        _dir, mm = mem_dir
        long_val = "x" * 500
        mm.update_memory({"notes": {"big": long_val}})
        loaded = mm.load_memory()
        saved_val = loaded["notes"]["big"]["value"]
        assert len(saved_val) <= mm.MAX_VALUE_LENGTH + 1  # +1 for ellipsis char


# ─────────────────────────────────────────────────────────────────────────────
# _trim_to_limit
# ─────────────────────────────────────────────────────────────────────────────

class TestTrimToLimit:
    def test_small_memory_unchanged(self, mem_dir):
        _dir, mm = mem_dir
        data = mm._empty_memory()
        data["notes"]["k"] = {"value": "small", "updated": "2024-01-01"}
        original = json.dumps(data)
        result = mm._trim_to_limit(data)
        assert json.dumps(result) == original

    def test_oversized_memory_gets_trimmed(self, mem_dir):
        _dir, mm = mem_dir
        data = mm._empty_memory()
        for i in range(100):
            data["notes"][f"key_{i:03d}"] = {
                "value": "a" * 200,
                "updated": f"2024-01-{(i % 28) + 1:02d}",
            }
        result = mm._trim_to_limit(data)
        assert len(json.dumps(result, ensure_ascii=False)) <= mm.MEMORY_MAX_CHARS


# ─────────────────────────────────────────────────────────────────────────────
# Known defect — R-O13 (no reentrant lock, no corrupt-JSON recovery path)
# ─────────────────────────────────────────────────────────────────────────────

def test_lock_is_reentrant(mem_dir):
    """The lock should be an RLock so the same thread can acquire it twice (P6 fix for R-O13)."""
    _dir, mm = mem_dir
    import threading
    # RLock can be acquired twice from the same thread; plain Lock deadlocks
    assert isinstance(mm._lock, type(threading.RLock())), (
        "_lock is a plain Lock — must be RLock to avoid reentrant deadlocks (R-O13)"
    )


def test_corrupt_json_restored_from_backup(mem_dir):
    """When long_term.json is corrupt, a valid .bak should be restored (P6 fix for R-O13)."""
    _dir, mm = mem_dir

    # Create a valid save first (produces .bak on second save)
    good_data = mm._empty_memory()
    good_data["notes"]["key"] = {"value": "important", "updated": "2024-01-01"}
    mm.save_memory(good_data)
    mm.save_memory(good_data)  # second save → creates .bak

    # Corrupt the main file
    mm.MEMORY_PATH.write_text("CORRUPTED {{{{", encoding="utf-8")

    loaded = mm.load_memory()
    # Should have restored from .bak and returned the good data
    assert loaded["notes"]["key"]["value"] == "important", (
        "Expected backup restoration, got empty memory (R-O13 not fixed yet)"
    )
