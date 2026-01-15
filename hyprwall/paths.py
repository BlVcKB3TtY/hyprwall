from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "hyprwall"
CACHE_DIR = Path.home() / ".cache" / "hyprwall"
STATE_DIR = CACHE_DIR / "state"

STATE_FILE = STATE_DIR / "state.json"
LOG_FILE = STATE_DIR / "hyprwall.log"

def ensure_directories():
    for d in (CONFIG_DIR, CACHE_DIR, STATE_DIR):
        d.mkdir(parents=True, exist_ok=True)