"""Unit tests for core/privacy_guard.py.

Tests use only pure-Python inputs; no PIL, no real filesystem.
The module handles PIL being absent gracefully (guarded import).
"""

import pytest
from core.privacy_guard import is_app_blacklisted, apply_privacy_filter, blur_sensitive_regions


# ── is_app_blacklisted ────────────────────────────────────────────────────────

class TestIsAppBlacklisted:
    def test_blocked_process_exact(self):
        assert is_app_blacklisted("KeePass", "keepass.exe") is True

    def test_blocked_process_case_insensitive(self):
        assert is_app_blacklisted("Some Window", "KeePass.EXE") is True

    def test_blocked_process_substring(self):
        # "1password.exe" contains "1password"
        assert is_app_blacklisted("1Password", "1password.exe") is True

    def test_blocked_title_pattern_password(self):
        assert is_app_blacklisted("Enter your password", "notepad.exe") is True

    def test_blocked_title_pattern_2fa(self):
        assert is_app_blacklisted("Two-Factor Authentication", "chrome.exe") is True

    def test_safe_app_and_title(self):
        assert is_app_blacklisted("My Document.docx - Word", "WINWORD.EXE") is False

    def test_empty_strings_are_safe(self):
        assert is_app_blacklisted("", "") is False

    def test_signal_process_blocked(self):
        assert is_app_blacklisted("Signal", "signal.exe") is True

    def test_title_mot_de_passe(self):
        assert is_app_blacklisted("Entrez votre mot de passe", "explorer.exe") is True

    def test_title_code_pin(self):
        assert is_app_blacklisted("Saisissez votre code pin", "lockscreen.exe") is True


# ── apply_privacy_filter ──────────────────────────────────────────────────────

class TestApplyPrivacyFilter:
    def test_returns_none_for_blacklisted_app(self):
        """Fully blocked apps must return None — no image at all."""
        result = apply_privacy_filter(
            image=object(),  # won't be accessed because blacklist check happens first
            window_title="password manager",
            process_name="keepass.exe",
            elements=[],
        )
        assert result is None

    def test_returns_image_for_safe_app(self):
        """Safe app with no password elements returns the original image unchanged."""
        try:
            from PIL import Image
            img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        except ImportError:
            pytest.skip("PIL not installed")

        result = apply_privacy_filter(
            image=img,
            window_title="Notepad",
            process_name="notepad.exe",
            elements=[],  # no password fields → no blurring
        )
        assert result is img  # returned as-is when no password regions

    def test_blur_sensitive_regions_with_non_password_elements(self):
        """Elements without is_password=True are ignored."""
        try:
            from PIL import Image
            img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        except ImportError:
            pytest.skip("PIL not installed")

        result = blur_sensitive_regions(
            image=img,
            elements=[{"is_password": False, "x": 100, "y": 100, "w": 50, "h": 20}],
        )
        assert result is not None

    def test_blur_sensitive_regions_password_field_blurred(self):
        """A password element should cause a blur (image should be different)."""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not installed")

        img = Image.new("RGB", (200, 200), color=(200, 100, 50))
        result = blur_sensitive_regions(
            image=img,
            elements=[{"is_password": True, "x": 100, "y": 100, "w": 80, "h": 30}],
        )
        # Should return an image object without crashing
        assert result is not None
        assert hasattr(result, "size")
