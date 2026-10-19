# config/__init__.py
# Compatibility shim delegating to unified configuration loader
from config.settings import get_settings, get_os as _get_os


def get_config() -> dict:
    """Compatibility function: delegates to unified settings loader."""
    return get_settings()


def get_os() -> str:
    """Returns: 'windows' | 'mac' | 'linux'"""
    return _get_os()


def is_windows() -> bool:
    return get_os() == "windows"


def is_mac() -> bool:
    return get_os() == "mac"


def is_linux() -> bool:
    return get_os() == "linux"
