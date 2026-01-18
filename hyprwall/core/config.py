"""
GUI configuration persistence.
Stores user preferences like default library directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from hyprwall.core import paths

CONFIG_FILE = paths.CONFIG_DIR / "gui_config.json"


def get_default_library_dir() -> Path:
    """
    Get the default library directory for GUI.

    Returns the configured directory if valid, otherwise uses intelligent fallback:
    1. ~/Pictures/wallpapers/Dynamic-Wallpapers/LiveWallpapers/ if exists
    2. ~/Pictures if exists
    3. ~ (home directory)
    """
    # Try to load saved config
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text())
            saved_path = data.get("default_library_dir")
            if saved_path:
                path = Path(saved_path).expanduser().resolve()
                if path.exists() and path.is_dir():
                    return path
    except Exception:
        pass

    # Fallback to intelligent defaults
    home = Path.home()

    # Try preferred path first
    preferred = home / "Pictures" / "wallpapers" / "Dynamic-Wallpapers" / "LiveWallpapers"
    if preferred.exists() and preferred.is_dir():
        return preferred

    # Try Pictures directory
    pictures = home / "Pictures"
    if pictures.exists() and pictures.is_dir():
        return pictures

    # Final fallback: home directory
    return home


def set_default_library_dir(path: Path | str) -> bool:
    """
    Set the default library directory for GUI.

    Args:
        path: Directory path to set as default

    Returns:
        True if saved successfully, False if invalid
    """
    try:
        # Validate path
        path = Path(path).expanduser().resolve()
        if not path.exists():
            return False
        if not path.is_dir():
            return False

        # Ensure config directory exists
        paths.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        config = {}
        if CONFIG_FILE.exists():
            try:
                config = json.loads(CONFIG_FILE.read_text())
            except Exception:
                config = {}

        # Update and save
        config["default_library_dir"] = str(path)
        CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")

        return True
    except Exception:
        return False


def reset_default_library_dir() -> bool:
    """
    Reset the default library directory to fallback behavior.

    Returns:
        True if reset successfully
    """
    try:
        if CONFIG_FILE.exists():
            # Load config
            config = json.loads(CONFIG_FILE.read_text())
            # Remove the setting
            if "default_library_dir" in config:
                del config["default_library_dir"]
            # Save updated config (or delete if empty)
            if config:
                CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")
            else:
                CONFIG_FILE.unlink()
        return True
    except Exception:
        return False