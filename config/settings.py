"""
Unified configuration loader for JARVIS.

Secrets are stored in .env (never committed).
Non-secret settings are stored in settings.json.

Priority for secrets:
1. Environment variable (highest priority)
2. .env file (project root)
3. .env file (profile directory, if frozen)
4. Error (CONFIG_MISSING)
"""

import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Paths:
    """Centralized path configuration for the application."""

    root: Path
    config_dir: Path
    memory_dir: Path
    logs_dir: Path
    secrets_env: Path
    projects_dir: Path


def _get_paths() -> Paths:
    """Determine paths based on whether the app is frozen (installed) or running from source."""
    if getattr(sys, "frozen", False):
        # Installed/frozen mode (e.g., PyInstaller)
        root = Path(sys.executable).parent
        config_dir = root / "config"
        # In frozen mode, secrets go to user profile
        secrets_env = Path.home() / ".jarvis" / ".env"
    else:
        # Development mode
        root = Path(__file__).resolve().parent.parent
        config_dir = root / "config"
        secrets_env = root / ".env"

    # Common subdirectories
    memory_dir = root / "memory"
    logs_dir = root / "logs"
    projects_dir = Path.home() / "Desktop" / "JarvisProjects"

    return Paths(
        root=root,
        config_dir=config_dir,
        memory_dir=memory_dir,
        logs_dir=logs_dir,
        secrets_env=secrets_env,
        projects_dir=projects_dir,
    )


# Global paths instance
paths = _get_paths()


def get_secret(name: str) -> str:
    """
    Return a secret value from environment or .env file.

    Priority:
    1. Environment variable (highest)
    2. .env file (project root)
    3. .env file (profile directory, if frozen)

    Raises:
        RuntimeError: If the secret is not found or is empty.
    """
    # Check environment variable first
    value = os.environ.get(name, "").strip()
    if value:
        return value

    # Check .env file
    env_file = paths.secrets_env
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    if key.strip() == name:
                        value = val.strip()
                        if value:
                            return value
        except Exception:
            pass  # Fall through to error

    raise RuntimeError(
        f"Secret '{name}' not found. "
        f"Set the {name} environment variable or add it to {env_file}."
    )


def save_secret(name: str, value: str) -> None:
    """
    Save a secret to the .env file.

    - Preserves existing lines and comments
    - Atomic write (tmp -> replace)
    - Tolerates Windows CRLF line endings
    - Allows descriptive names like GEMINI_API_KEY
    """
    env_file = paths.secrets_env
    lines = []
    updated = False

    # Read existing .env if it exists
    if env_file.exists():
        existing_content = env_file.read_text(encoding="utf-8")
        # Handle both CRLF and LF
        lines = existing_content.replace("\r\n", "\n").splitlines()

    # Update or add the secret
    new_line = f"{name}={value}"
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{name}="):
            lines[i] = new_line
            updated = True
            break
    else:
        lines.append(new_line)
        updated = True

    # Atomic write using temp file
    content = "\n".join(lines) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, dir=env_file.parent, suffix=".tmp"
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        tmp_path.replace(env_file)
    except Exception:
        tmp_path.unlink()
        raise


def delete_secret(name: str) -> None:
    """
    Delete a secret from the .env file.

    Preserves other lines and comments.
    """
    env_file = paths.secrets_env
    if not env_file.exists():
        return

    lines = []
    if env_file.exists():
        existing_content = env_file.read_text(encoding="utf-8")
        lines = existing_content.replace("\r\n", "\n").splitlines()

    # Remove the secret line
    lines = [line for line in lines if not line.strip().startswith(f"{name}=")]

    # Write back
    content = "\n".join(lines) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, dir=env_file.parent, suffix=".tmp"
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        tmp_path.replace(env_file)
    except Exception:
        tmp_path.unlink()
        raise


def get_settings() -> dict[str, Any]:
    """
    Load non-secret settings from settings.json.

    Returns empty dict if file is missing or corrupted.
    Logs a warning if corrupted.
    """
    settings_file = paths.config_dir / "settings.json"

    if not settings_file.exists():
        return {}

    try:
        return json.loads(settings_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Warning: settings.json is corrupted: {e}. Using defaults.")
        return {}
    except Exception as e:
        print(f"Warning: Could not read settings.json: {e}. Using defaults.")
        return {}


def save_settings(settings: dict[str, Any]) -> None:
    """
    Save non-secret settings to settings.json.

    - Atomic write (tmp -> replace)
    - Refuses keys containing key/secret/password (security check)
    """
    # Security check: refuse to write keys with suspicious names
    suspicious_keywords = ["key", "secret", "token", "password"]
    for key in settings.keys():
        if any(kw in key.lower() for kw in suspicious_keywords):
            raise ValueError(
                f"Refusing to write setting with suspicious name '{key}'. "
                "Secrets belong in .env, not settings.json."
            )
    settings_file = paths.config_dir / "settings.json"
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write
    content = json.dumps(settings, indent=2)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        delete=False,
        dir=settings_file.parent,
        suffix=".tmp",
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        tmp_path.replace(settings_file)
    except Exception:
        tmp_path.unlink()
        raise


def get_os() -> str:
    """
    Get the operating system from settings.

    Returns:
        "windows", "mac", or "linux"

    Defaults to "windows" if not configured.
    Raises ValueError if the value is invalid.
    """
    settings = get_settings()
    os_value = settings.get("os_system", "windows").lower()

    valid_os = {"windows", "mac", "linux"}
    if os_value not in valid_os:
        raise ValueError(f"Invalid os_system '{os_value}'. Must be one of: {valid_os}")

    return os_value
