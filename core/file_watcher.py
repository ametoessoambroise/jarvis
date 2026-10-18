import time
from pathlib import Path
from datetime import datetime
from typing import Callable


class FileWatcher:
    """Simple file watcher that detects changes in Python files."""
    
    def __init__(self, watch_dirs: list[str] = None, ignore_patterns: list[str] = None):
        """
        Initialize the file watcher.
        
        Args:
            watch_dirs: List of directories to watch (default: ['core', 'actions', 'memory', 'ui', 'agent', 'logs'])
            ignore_patterns: List of patterns to ignore (default: ['__pycache__', '.pyc', '.json'])
        """
        self.watch_dirs = watch_dirs or [
            'core', 'actions', 'memory', 'ui', 'agent', 'logs'
        ]
        self.ignore_patterns = ignore_patterns or [
            '__pycache__', '.pyc', '.pyo', '.json', '.git'
        ]
        self.last_mtimes = {}
        self._scan_files()
    
    def _should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored."""
        return any(pattern in path for pattern in self.ignore_patterns)
    
    def _get_all_files(self) -> dict[str, float]:
        """Get all Python files and their modification times."""
        files = {}
        base = Path('.')
        
        for watch_dir in self.watch_dirs:
            dir_path = base / watch_dir
            if not dir_path.exists():
                continue
            for py_file in dir_path.rglob('*.py'):
                if not self._should_ignore(str(py_file)):
                    try:
                        files[str(py_file)] = py_file.stat().st_mtime
                    except (OSError, FileNotFoundError):
                        pass
        
        # Also watch main.py itself
        main_py = base / 'main.py'
        if main_py.exists():
            try:
                files[str(main_py)] = main_py.stat().st_mtime
            except (OSError, FileNotFoundError):
                pass
        
        return files
    
    def _scan_files(self) -> None:
        """Scan all files and update mtimes cache."""
        self.last_mtimes = self._get_all_files()
    
    def check_for_changes(self) -> bool:
        """
        Check if any watched files have changed.
        
        Returns:
            True if changes detected, False otherwise
        """
        current_files = self._get_all_files()
        
        # Check for new or modified files
        for file_path, mtime in current_files.items():
            if file_path not in self.last_mtimes or self.last_mtimes[file_path] != mtime:
                print(f"[WATCH] 📝 File changed: {file_path}")
                self.last_mtimes = current_files
                return True
        
        # Check for deleted files
        for file_path in self.last_mtimes:
            if file_path not in current_files:
                print(f"[WATCH] 🗑️  File deleted: {file_path}")
                self.last_mtimes = current_files
                return True
        
        return False


def watch_and_restart(callback: Callable, check_interval: int = 1) -> None:
    """
    Watch for file changes and call callback when detected.
    
    Args:
        callback: Function to call when changes are detected
        check_interval: Interval in seconds to check for changes
    """
    watcher = FileWatcher()
    print("[WATCH] 👁️  Watch mode activated. Monitoring changes...")
    
    try:
        while True:
            time.sleep(check_interval)
            if watcher.check_for_changes():
                print("[WATCH] 🔄 Changes detected! Restarting...")
                callback()
                print("[WATCH] 👁️  Resuming watch mode...")
    except KeyboardInterrupt:
        print("\n[WATCH] ⛔ Watch mode stopped.")
