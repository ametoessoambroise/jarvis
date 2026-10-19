"""
Unit tests for unified configuration loader (config.settings).

Tests are offline by default and do not use real secrets.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Import the module under test
from config import settings


class TestSecretPrecedence:
    """Test secret loading precedence: env > .env > error."""

    def test_environment_variable_takes_priority(self, monkeypatch, tmp_path):
        """Environment variable should take priority over .env file."""
        monkeypatch.setenv("TEST_SECRET", "from_env")

        env_file = tmp_path / ".env"
        env_file.write_text("TEST_SECRET=from_file", encoding="utf-8")

        # Create a new Paths instance manually
        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=settings.paths.config_dir,
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=env_file,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            result = settings.get_secret("TEST_SECRET")
            assert result == "from_env"

    def test_env_fallback_when_env_not_set(self, monkeypatch, tmp_path):
        """Should fall back to .env when environment variable is not set."""
        monkeypatch.delenv("TEST_SECRET", raising=False)

        env_file = tmp_path / ".env"
        env_file.write_text("TEST_SECRET=from_file", encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=settings.paths.config_dir,
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=env_file,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            result = settings.get_secret("TEST_SECRET")
            assert result == "from_file"

    def test_missing_secret_raises_error(self, monkeypatch, tmp_path):
        """Should raise RuntimeError when secret is not found."""
        monkeypatch.delenv("TEST_SECRET", raising=False)

        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_SECRET=value", encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=settings.paths.config_dir,
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=env_file,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            with pytest.raises(RuntimeError, match="Secret 'TEST_SECRET' not found"):
                settings.get_secret("TEST_SECRET")

    def test_empty_secret_is_rejected(self, monkeypatch):
        """Should reject empty secret values."""
        monkeypatch.setenv("TEST_SECRET", "")

        with pytest.raises(RuntimeError, match="Secret 'TEST_SECRET' not found"):
            settings.get_secret("TEST_SECRET")


class TestSaveSecret:
    """Test secret saving behavior."""

    def test_save_secret_creates_env(self, tmp_path):
        """save_secret should create .env if it doesn't exist."""
        env_file = tmp_path / ".env"

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=settings.paths.config_dir,
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=env_file,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            settings.save_secret("NEW_SECRET", "new_value")

        assert env_file.exists()
        content = env_file.read_text(encoding="utf-8")
        assert "NEW_SECRET=new_value" in content

    def test_save_secret_preserves_comments(self, tmp_path):
        """save_secret should preserve existing comments."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# This is a comment\nOLD_SECRET=old_value\n", encoding="utf-8"
        )

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=settings.paths.config_dir,
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=env_file,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            settings.save_secret("NEW_SECRET", "new_value")

        content = env_file.read_text(encoding="utf-8")
        assert "# This is a comment" in content
        assert "OLD_SECRET=old_value" in content
        assert "NEW_SECRET=new_value" in content

    def test_save_secret_updates_existing(self, tmp_path):
        """save_secret should update existing secret."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_SECRET=old_value\n", encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=settings.paths.config_dir,
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=env_file,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            settings.save_secret("TEST_SECRET", "new_value")

        content = env_file.read_text(encoding="utf-8")
        assert "TEST_SECRET=new_value" in content
        assert "old_value" not in content


class TestDeleteSecret:
    """Test secret deletion behavior."""

    def test_delete_secret_removes_line(self, tmp_path):
        """delete_secret should remove the secret line."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_SECRET=value\nOTHER_SECRET=other\n", encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=settings.paths.config_dir,
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=env_file,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            settings.delete_secret("TEST_SECRET")

        content = env_file.read_text(encoding="utf-8")
        assert "TEST_SECRET" not in content
        assert "OTHER_SECRET=other" in content


class TestGetSettings:
    """Test settings.json loading."""

    def test_get_settings_returns_dict(self, tmp_path):
        """get_settings should return a dict."""
        settings_file = tmp_path / "config" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text('{"os_system": "windows"}', encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            result = settings.get_settings()
            assert isinstance(result, dict)
            assert result["os_system"] == "windows"

    def test_get_settings_returns_empty_if_missing(self, tmp_path):
        """get_settings should return empty dict if file is missing."""
        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            result = settings.get_settings()
            assert result == {}


class TestSaveSettings:
    """Test settings.json saving."""

    def test_save_settings_creates_file(self, tmp_path):
        """save_settings should create settings.json."""
        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            settings.save_settings({"os_system": "windows"})

        settings_file = tmp_path / "config" / "settings.json"
        assert settings_file.exists()
        content = json.loads(settings_file.read_text(encoding="utf-8"))
        assert content["os_system"] == "windows"

    def test_save_settings_refuses_secret_keys(self, tmp_path):
        """save_settings should refuse keys with secret keywords."""
        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            with pytest.raises(
                ValueError, match="Refusing to write setting with suspicious name"
            ):
                settings.save_settings({"api_key": "value"})


class TestGetOS:
    """Test OS detection from settings."""

    def test_get_os_returns_value_from_settings(self, tmp_path):
        """get_os should return the value from settings.json."""
        settings_file = tmp_path / "config" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text('{"os_system": "mac"}', encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            result = settings.get_os()
            assert result == "mac"

    def test_get_os_defaults_to_windows(self, tmp_path):
        """get_os should default to 'windows' if not configured."""
        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            result = settings.get_os()
            assert result == "windows"

    def test_get_os_validates_value(self, tmp_path):
        """get_os should raise ValueError for invalid values."""
        settings_file = tmp_path / "config" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text('{"os_system": "invalid"}', encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            with pytest.raises(ValueError, match="Invalid os_system"):
                settings.get_os()


class TestPublicCompatibility:
    """Test public config compatibility functions."""

    def test_config_get_os_compatibility(self, tmp_path):
        """config.get_os() should delegate to settings.get_os()."""
        from config import get_os

        settings_file = tmp_path / "config" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text('{"os_system": "linux"}', encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            result = get_os()
            assert result == "linux"

    def test_config_is_windows_compatibility(self, tmp_path):
        """config.is_windows() should work."""
        from config import is_windows

        settings_file = tmp_path / "config" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text('{"os_system": "windows"}', encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            assert is_windows() is True

    def test_config_is_mac_compatibility(self, tmp_path):
        """config.is_mac() should work."""
        from config import is_mac

        settings_file = tmp_path / "config" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text('{"os_system": "mac"}', encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            assert is_mac() is True

    def test_config_is_linux_compatibility(self, tmp_path):
        """config.is_linux() should work."""
        from config import is_linux

        settings_file = tmp_path / "config" / "settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings_file.write_text('{"os_system": "linux"}', encoding="utf-8")

        new_paths = settings.Paths(
            root=settings.paths.root,
            config_dir=tmp_path / "config",
            memory_dir=settings.paths.memory_dir,
            logs_dir=settings.paths.logs_dir,
            secrets_env=settings.paths.secrets_env,
            projects_dir=settings.paths.projects_dir,
        )

        with patch.object(settings, "paths", new_paths):
            assert is_linux() is True
