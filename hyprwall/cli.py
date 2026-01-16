import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

import hyprwall.paths as paths
import hyprwall.detect as detect

from hyprwall import runner
from hyprwall import hypr
from hyprwall import optimize

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

def parse_arguments():
    parser = argparse.ArgumentParser(
        prog="hyprwall",
        description="HyprWall - Lightweight Wallpaper Manager for Hyprland",
        epilog=f"{Colors.DIM}Project: https://github.com/TheOnlyChou/hyprwall{Colors.RESET}",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Print extra debug info")
    parser.add_argument("--no-banner", action="store_true", help="Disable banner output")

    sub = parser.add_subparsers(dest="command", required=True)

    # Set commands parser
    set_cmd = sub.add_parser(
        "set",
        help="Set a wallpaper (file or directory)",
        description="""Set a wallpaper on your Hyprland desktop.
        
Supports images (jpg, png, gif, webp) and videos (mp4, mkv, webm, avi, mov).
When pointing to a directory, the most recent file will be used.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    set_cmd.add_argument("path", type=str, help="Path to the image/video file OR directory")
    set_cmd.add_argument(
        "--monitor",
        type=str,
        default=None,
        metavar="NAME",
        help="Monitor name (e.g., eDP-1, HDMI-A-1). Default: focused monitor"
    )
    set_cmd.add_argument(
        "--mode",
        choices=["auto", "fit", "cover", "stretch"],
        default="auto",
        metavar="MODE",
        help="""Rendering mode (default: auto)
  • auto    - Images use 'cover', videos use 'fit'
  • fit     - Letterbox: keep aspect ratio, add black bars
  • cover   - Fill screen, crop edges if needed
  • stretch - Fill screen completely, may distort image""",
    )
    set_cmd.add_argument(
        "--profile",
        choices=["eco", "balanced", "quality", "av1", "off"],
        default="balanced",
        metavar="PROFILE",
        help="""Optimization profile for videos (default: balanced)
  • eco      - 24fps, H.264, CRF 28, veryfast (lowest CPU/battery usage)
  • balanced - 30fps, H.264, CRF 24, veryfast (recommended)
  • quality  - 30fps, H.264, CRF 20, fast (best visual quality)
  • av1      - 24fps, AV1 VAAPI, QP 28 (hardware encode, AMD/Intel only)
  • off      - No optimization, use source file directly""",
    )
    set_cmd.add_argument(
        "--encoder",
        choices=["auto", "cpu", "vaapi", "nvenc"],
        default="auto",
        metavar="ENC",
        help="""Encoding backend (default: auto)
  • auto  - Prefer NVENC > VAAPI > CPU (may fallback on error)
  • cpu   - libx264 CPU encoder (no hardware acceleration)
  • vaapi - Intel/AMD hardware encode (strict, no fallback)
  • nvenc - NVIDIA hardware encode (strict, no fallback)""",
    )

    # Status commands parser
    sub.add_parser(
        "status",
        help="Show current wallpaper status",
        description="Display information about the currently running wallpaper (if any)."
    )

    # Stop commands parser
    sub.add_parser(
        "stop",
        help="Stop current wallpaper",
        description="Stop the currently running wallpaper (mpvpaper process)."
    )

    # Cache commands parser
    cache_cmd = sub.add_parser(
        "cache",
        help="Manage optimization cache",
        description="""Manage the wallpaper optimization cache.
        
The cache stores optimized video files to avoid re-encoding on every run.
Cache location: ~/.cache/hyprwall/""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    cache_cmd.add_argument(
        "action",
        nargs="?",
        default="size",
        choices=["clear", "size"],
        help="""Cache action (default: size)
  • size  - Show current cache size
  • clear - Delete all cached files"""
    )

    # List of commands
    args = parser.parse_args()

    return args

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

def main():
    args = parse_arguments()

    if not args.no_banner and args.command == "set":
        print_banner()
        print()

    paths.ensure_directories()

    if args.verbose:
        print_header("Debug Information")
        print_info("Config directory", str(paths.CONFIG_DIR))
        print_info("Cache directory", str(paths.CACHE_DIR))
        print_info("State directory", str(paths.STATE_DIR))
        print_info("State file", str(paths.STATE_FILE))
        print_info("Log file", str(paths.LOG_FILE))
        print()

    try:
        if args.command == "set":
            # Validate wallpaper path
            animate_progress("Validating wallpaper path", 0.3)
            valid_path = detect.validate_wallpaper(args.path)
            print_success(f"Wallpaper found: {Colors.DIM}{valid_path.name}{Colors.RESET}")

            # Detect monitor
            animate_progress("Detecting monitor configuration", 0.3)
            monitor = args.monitor or hypr.default_monitor_name()
            w, h = hypr.monitor_resolution(monitor)
            print_success(f"Target monitor: {Colors.BRIGHT_WHITE}{monitor}{Colors.RESET} ({w}×{h})")

            # Display configuration
            print_header("Configuration")
            print_info("Source", str(valid_path))
            print_info("Mode", args.mode)
            print_info("Profile", args.profile if args.profile != "off" else "off (no optimization)")
            print_info("Encoder", args.encoder)

            if args.verbose:
                print_info("Resolution", f"{w}×{h}")
            print()

            # Optimization phase
            file_to_play = valid_path
            if args.profile != "off":
                prof = {
                    "eco": optimize.ECO,
                    "balanced": optimize.BALANCED,
                    "quality": optimize.QUALITY,
                    "av1": optimize.AV1_ECO,
                }[args.profile]

                # Force VAAPI encoder for AV1 profile
                encoder_to_use = args.encoder
                if args.profile == "av1" and args.encoder == "auto":
                    encoder_to_use = "vaapi"
                    if args.verbose:
                        print_info("Encoder", "vaapi (forced for AV1)", indent=1)

                print_header("Optimization")
                animate_progress(f"Optimizing with '{args.profile}' profile", 0.5)

                res = optimize.ensure_optimized(
                    valid_path,
                    width=w,
                    height=h,
                    profile=prof,
                    mode=args.mode,
                    encoder=encoder_to_use,
                    verbose=args.verbose,
                )

                file_to_play = res.path

                # Display truthful information about what happened
                if res.cache_hit:
                    print_success(f"Cache hit: reusing optimized file")
                    if args.verbose:
                        print_info("Encoder used", res.used, indent=1)
                else:
                    if res.used == res.chosen:
                        print_success(f"Encoded with {res.used.upper()}")
                    else:
                        print_warning(f"{res.chosen.upper()} failed, fallback to {res.used.upper()} (auto mode)")

                if args.verbose:
                    print_info("Optimized file", str(file_to_play), indent=1)
                    if res.requested != res.chosen:
                        print_info("Encoder selection", f"requested={res.requested}, chosen={res.chosen}, used={res.used}", indent=1)
                print()

            # Stop existing wallpaper
            animate_progress("Stopping existing wallpaper", 0.3)
            runner.stop()

            # Start new wallpaper
            print_info("Playing", str(file_to_play))
            animate_progress("Starting wallpaper", 0.5)
            state = runner.start(
                monitor=monitor,
                file=file_to_play,
                extra_args=[],
                mode=args.mode,
            )

            print_header("Success!")
            print_success(f"Wallpaper set on monitor {Colors.BRIGHT_WHITE}{state.monitor}{Colors.RESET}")
            print_info("Rendering mode", state.mode, indent=1)
            print_info("Process ID", f"PID={state.pid}, PGID={state.pgid}", indent=1)
            print()

        elif args.command == "status":
            print_header("Wallpaper Status")
            st = runner.status()

            if not st.get("running"):
                print_warning("No wallpaper is currently running")
                if args.verbose:
                    print()
                    print(f"{Colors.DIM}Raw state: {st}{Colors.RESET}")
                return

            print_info("Status", f"{Colors.BRIGHT_GREEN}Running{Colors.RESET}")
            print_info("Monitor", st.get('monitor', 'unknown'))
            print_info("File", st.get('file', 'unknown'))
            print_info("Mode", st.get('mode', 'auto'))
            print_info("Process", f"PID={st['pid']}, PGID={st['pgid']}")

            if args.verbose:
                print()
                print_separator()
                print_info("State file", st.get('state_file', 'unknown'))
                print_info("Log file", st.get('log_file', 'unknown'))
                print_info("Process exists", str(st.get('exists', False)))
                print_info("Is mpvpaper", str(st.get('is_mpvpaper', False)))
            print()

        elif args.command == "stop":
            animate_progress("Stopping wallpaper", 0.5)
            was_stopped = runner.stop()

            if was_stopped:
                print_success("Wallpaper stopped successfully")
            else:
                print_warning("No wallpaper process was running")
            print()

        elif args.command == "cache":
            if args.action == "clear":
                print_header("Cache Management")
                animate_progress("Clearing cache", 0.5)

                count = 0
                if paths.CACHE_DIR.exists():
                    for p in paths.CACHE_DIR.iterdir():
                        # Skip state directory to preserve state.json
                        if p.name == "state":
                            continue

                        if p.is_dir():
                            shutil.rmtree(p, ignore_errors=True)
                            count += 1
                        else:
                            try:
                                p.unlink()
                                count += 1
                            except OSError:
                                pass

                paths.ensure_directories()
                print_success(f"Cache cleared successfully ({count} items removed)")
                print_info("State preserved", str(paths.STATE_DIR), indent=1)
                print()

            # Always show cache info for both "size" and after "clear"
            print_header("Cache Information")
            n = cache_size_bytes(paths.CACHE_DIR)
            print_info("Cache location", str(paths.CACHE_DIR))
            print_info("Cache size", f"{human_size(n)} ({n:,} bytes)")
            print()

    except KeyboardInterrupt:
        print()
        print_warning("Operation cancelled by user")
        raise SystemExit(130)
    except Exception as e:
        print()
        print_error(f"Error: {e}")
        if args.verbose:
            import traceback
            print()
            print(f"{Colors.DIM}{traceback.format_exc()}{Colors.RESET}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()