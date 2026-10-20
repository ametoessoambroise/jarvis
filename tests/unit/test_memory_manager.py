"""Unit tests for memory/memory_manager.py (Phase 6 — R-O13 & R-O27 fixed).

All tests run isolated in temporary directories and never access real user memory.
"""

import json
import os
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

import memory.memory_manager as mm


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def mem_env(tmp_path, monkeypatch):
    """Provide an isolated test environment via JARVIS_MEMORY_DIR."""
    test_dir = tmp_path / "test_memory"
    test_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("JARVIS_MEMORY_DIR", str(test_dir))
    monkeypatch.setattr(mm, "MEMORY_DIR", test_dir)
    monkeypatch.setattr(mm, "MEMORY_PATH", test_dir / "long_term.json")
    yield test_dir


# ─────────────────────────────────────────────────────────────────────────────
# Concurrency: 50 concurrent update_memory calls
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrentUpdates:
    def test_50_concurrent_updates_no_loss(self, mem_env):
        """50 concurrent threads updating distinct keys must all succeed without data loss."""
        num_threads = 50
        barrier = threading.Barrier(num_threads)
        errors = []

        def worker(thread_idx: int):
            try:
                barrier.wait(timeout=10)
                update = {
                    "notes": {
                        f"thread_{thread_idx}": {
                            "value": f"result_{thread_idx}"
                        }
                    }
                }
                mm.update_memory(update)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=worker, args=(i,))
            for i in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        assert not errors, f"Errors encountered during concurrent updates: {errors}"

        # Verify all 50 entries exist in the saved memory
        loaded = mm.load_memory()
        notes = loaded.get("notes", {})
        for i in range(num_threads):
            key = f"thread_{i}"
            assert key in notes, f"Missing key {key} after concurrent updates"
            assert notes[key]["value"] == f"result_{i}"


# ─────────────────────────────────────────────────────────────────────────────
# Corruption & Backup Protection (R-O13)
# ─────────────────────────────────────────────────────────────────────────────

class TestCorruptionHandling:
    def test_corrupt_file_quarantined_and_restored(self, mem_env):
        """When long_term.json is corrupt:
        1. It is quarantined to long_term.json.corrupt-<timestamp>
        2. It is restored from a valid .bak
        """
        # Step 1: Save valid data twice so .bak is created
        initial_data = mm._empty_memory()
        initial_data["identity"]["name"] = {"value": "Tony Stark", "updated": "2026-01-01"}
        mm.save_memory(initial_data)
        mm.save_memory(initial_data)

        bak_file = mm._get_memory_path().with_suffix(".json.bak")
        assert bak_file.exists()

        # Step 2: Corrupt the main file
        main_file = mm._get_memory_path()
        main_file.write_text("MALFORMED JSON {{{{{", encoding="utf-8")

        # Step 3: Load memory
        loaded = mm.load_memory()

        # Step 4: Verify recovery from backup
        assert loaded["identity"]["name"]["value"] == "Tony Stark"

        # Step 5: Verify quarantine file was created
        corrupt_files = list(mem_env.glob("long_term.json.corrupt-*"))
        assert len(corrupt_files) == 1
        assert "MALFORMED" in corrupt_files[0].read_text(encoding="utf-8")

    def test_corrupt_file_never_overwrites_good_backup(self, mem_env):
        """If long_term.json is corrupt, a subsequent save_memory must NOT copy it to .bak."""
        # 1. Establish valid .bak
        good_data = mm._empty_memory()
        good_data["notes"]["key"] = {"value": "safe_backup_value", "updated": "2026-01-01"}
        mm.save_memory(good_data)
        mm.save_memory(good_data)

        bak_file = mm._get_memory_path().with_suffix(".json.bak")
        assert "safe_backup_value" in bak_file.read_text(encoding="utf-8")

        # 2. Corrupt main file
        main_file = mm._get_memory_path()
        main_file.write_text("CORRUPTED JUNK", encoding="utf-8")

        # 3. Call save_memory with fresh data
        new_data = mm._empty_memory()
        new_data["notes"]["key"] = {"value": "new_value", "updated": "2026-01-02"}
        mm.save_memory(new_data)

        # 4. .bak must still contain valid JSON, NOT 'CORRUPTED JUNK'
        bak_content = bak_file.read_text(encoding="utf-8")
        assert "CORRUPTED JUNK" not in bak_content
        parsed = json.loads(bak_content)
        assert isinstance(parsed, dict)

    def test_corrupt_both_falls_back_to_empty(self, mem_env):
        """If both main file and .bak are corrupt, return empty memory without crashing."""
        main_file = mm._get_memory_path()
        bak_file = main_file.with_suffix(".json.bak")

        main_file.write_text("CORRUPT 1", encoding="utf-8")
        bak_file.write_text("CORRUPT 2", encoding="utf-8")

        loaded = mm.load_memory()
        assert isinstance(loaded, dict)
        assert set(loaded.keys()) == mm.VALID_CATEGORIES


# ─────────────────────────────────────────────────────────────────────────────
# Category Validation (VALID_CATEGORIES)
# ─────────────────────────────────────────────────────────────────────────────

class TestCategoryValidation:
    def test_valid_categories_are_accepted(self, mem_env):
        for cat in mm.VALID_CATEGORIES:
            mm.update_memory({cat: {"sample_key": "sample_val"}})
            loaded = mm.load_memory()
            assert loaded[cat]["sample_key"]["value"] == "sample_val"

    def test_invalid_category_routes_to_notes(self, mem_env, capsys):
        """An unknown category must be routed to 'notes' with an explicit warning."""
        mm.update_memory({"unknown_custom_cat": {"custom_key": "custom_val"}})
        out = capsys.readouterr().out
        assert "Unknown memory category 'unknown_custom_cat' — routing to 'notes'" in out

        loaded = mm.load_memory()
        assert "notes" in loaded
        assert "unknown_custom_cat_custom_key" in loaded["notes"]
        assert loaded["notes"]["unknown_custom_cat_custom_key"]["value"] == "custom_val"

    def test_remember_function_validates_category(self, mem_env, capsys):
        msg = mm.remember("my_key", "my_val", category="non_existent_category")
        out = capsys.readouterr().out
        assert "Unknown category 'non_existent_category' in remember() — fallback to 'notes'" in out
        assert "Remembered: notes/my_key = my_val" in msg

        loaded = mm.load_memory()
        assert loaded["notes"]["my_key"]["value"] == "my_val"


# ─────────────────────────────────────────────────────────────────────────────
# Trimming & Limits
# ─────────────────────────────────────────────────────────────────────────────

class TestTrimmingAndLimits:
    def test_value_length_truncated_at_380(self, mem_env):
        long_text = "z" * 500
        mm.update_memory({"notes": {"long_k": long_text}})
        loaded = mm.load_memory()
        val = loaded["notes"]["long_k"]["value"]
        assert len(val) <= mm.MAX_VALUE_LENGTH + 1
        assert val.endswith("…")

    def test_trim_to_limit_logs_removed_keys(self, mem_env, capsys):
        """When memory exceeds MEMORY_MAX_CHARS, oldest keys are trimmed and logged."""
        data = mm._empty_memory()
        for i in range(80):
            data["notes"][f"key_{i:03d}"] = {
                "value": "x" * 200,
                "updated": f"2020-01-{(i % 28) + 1:02d}",
            }
        mm.save_memory(data)
        out = capsys.readouterr().out
        assert "Trimmed" in out
        assert "old entries to stay under limit" in out

        # Verify final memory size is within bounds
        loaded_memory = mm.load_memory()
        assert len(json.dumps(loaded_memory, ensure_ascii=False)) <= mm.MEMORY_MAX_CHARS


# ─────────────────────────────────────────────────────────────────────────────
# Prompt Formatting & Markdown Exports
# ─────────────────────────────────────────────────────────────────────────────

class TestPromptFormattingAndDocs:
    def test_format_memory_for_prompt_bounded_at_2000(self, mem_env):
        """format_memory_for_prompt must never exceed 2 000 characters."""
        data = mm._empty_memory()
        for cat in mm.VALID_CATEGORIES:
            for i in range(10):
                data[cat][f"item_{i}"] = {
                    "value": f"Value {i} for {cat} describing something in great detail to take space",
                    "updated": "2026-01-01",
                }

        formatted = mm.format_memory_for_prompt(data)
        assert len(formatted) <= 2000
        assert formatted.startswith("[WHAT YOU KNOW ABOUT THIS PERSON")
        if len(formatted) == 2000:
            assert formatted.endswith("…\n")

    def test_markdown_docs_generated_on_save(self, mem_env):
        """Saving memory should generate all 7 Markdown doc files."""
        data = mm._empty_memory()
        data["identity"]["name"] = {"value": "Bruce Wayne", "updated": "2026-01-01"}
        data["preferences"]["car"] = {"value": "Batmobile", "updated": "2026-01-01"}
        mm.save_memory(data)

        for cat, filename in mm.MEMORY_DOC_FILES.items():
            doc_path = mem_env / filename
            assert doc_path.exists(), f"Expected markdown doc {filename} to exist"

        identity_doc = (mem_env / "USER_IDENTITY.md").read_text(encoding="utf-8")
        assert "Bruce Wayne" in identity_doc
