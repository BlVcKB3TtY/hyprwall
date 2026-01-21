"""Common CLI utilities: colors, printing, helpers."""

import shutil
import subprocess
import sys
import time
from pathlib import Path


# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Basic colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


def print_separator(char="─", width=60):
    """Print a horizontal separator line"""
    print(f"{Colors.DIM}{char * width}{Colors.RESET}")


def print_info(label: str, value: str, indent: int = 0):
    """Print formatted info line"""
    spaces = "  " * indent
    print(f"{spaces}{Colors.CYAN}{label}:{Colors.RESET} {Colors.BRIGHT_WHITE}{value}{Colors.RESET}")


def print_success(message: str):
    """Print success message with checkmark"""
    print(f"{Colors.BRIGHT_GREEN}✓{Colors.RESET} {message}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.BRIGHT_YELLOW}!{Colors.RESET} {message}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.BRIGHT_RED}✗{Colors.RESET} {message}")


def print_header(text: str):
    """Print a header"""
    print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{text}{Colors.RESET}")
    print_separator()


def animate_progress(text: str, duration: float = 0.5):
    """Simple progress animation"""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        frame = frames[i % len(frames)]
        sys.stdout.write(f"\r{Colors.CYAN}{frame}{Colors.RESET} {text}")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write(f"\r{' ' * (len(text) + 3)}\r")
    sys.stdout.flush()


def print_banner():
    if shutil.which("figlet"):
        subprocess.run(["figlet", "-f", "standard", "HyprWall"], check=False)
        print(f"{Colors.DIM}Wallpaper Manager for Hyprland{Colors.RESET}")
    else:
        print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}╔═══════════════════════════════════╗")
        print(f"║          H Y P R W A L L          ║")
        print(f"╚═══════════════════════════════════╝{Colors.RESET}")
        print(f"{Colors.DIM}Wallpaper Manager for Hyprland{Colors.RESET}")
        print(f"{Colors.DIM}(Tip: install 'figlet' for ASCII art banner){Colors.RESET}")


def cache_size_bytes(root: Path) -> int:
    total = 0
    if not root.exists():
        return 0
    for p in root.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def human_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n)
    for u in units:
        if x < 1024.0:
            return f"{x:.1f}{u}"
        x /= 1024.0
    return f"{x:.1f}PB"