import argparse
import shutil
import subprocess
from pathlib import Path

import hyprwall.paths as paths
import hyprwall.detect as detect

from hyprwall import runner
from hyprwall import hypr

def print_banner():
    if shutil.which("figlet"):
        subprocess.run(["figlet", "HyprWall"], check=False)
    else:
        print("HyprWall\nWallpaper Manager for Hyprland\n(Tip: install `figlet` for an ASCII banner)")

def parse_arguments():
    parser = argparse.ArgumentParser(
        prog="hyprwall",
        description="HyprWall - Wallpaper Manager for Hyprland",
        epilog="Enjoy managing your wallpapers!"
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Print extra debug info")
    parser.add_argument("--no-banner", action="store_true", help="Disable banner output")

    sub = parser.add_subparsers(dest="command", required=True)

    # Set commands parser
    set_cmd = sub.add_parser("set", help="Set a wallpaper (file or directory)")
    set_cmd.add_argument("path", type=str, help="Path to the image/video file OR directory")
    set_cmd.add_argument("--monitor", type=str, default=None, help="Monitor name (ex: eDP-1). Default: focused.")
    set_cmd.add_argument(
        "--mode",
        choices=["auto", "fit", "cover", "stretch"],
        default="auto",
        help="Rendering mode: auto (image->cover, video->fit), fit (letterbox), cover (crop), stretch (distort).",
    )

    # Status commands parser
    sub.add_parser("status", help="Show current mpvpaper status")

    # Stop commands parser
    sub.add_parser("stop", help="Stop current wallpaper (mpvpaper)")

    # Cache commands parser
    cache_cmd = sub.add_parser("cache", help="Cache operations")
    cache_cmd.add_argument("action", nargs="?", default="size", choices=["clear", "size"],
    help="Action to run (default: size)")

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

    paths.ensure_directories()

    if args.verbose:
        print(f"Config: {paths.CONFIG_DIR}")
        print(f"Cache:  {paths.CACHE_DIR}")
        print(f"State:  {paths.STATE_DIR}")
        print(f"State file: {paths.STATE_FILE}")
        print(f"Log file:   {paths.LOG_FILE}")

    try:
        if args.command == "set":
            valid_path = detect.validate_wallpaper(args.path)

            monitor = args.monitor or hypr.default_monitor_name()
            if args.verbose:
                print(f"Using monitor: {monitor}")
                print(f"Selected file: {valid_path}")
                print(f"Mode: {args.mode}")

            runner.stop()
            state = runner.start(
                monitor,
                valid_path,
                extra_args=[],
                mode=args.mode,
            )

            print(
                f"Wallpaper set (mode={state.mode}) via mpvpaper "
                f"(PID={state.pid}, PGID={state.pgid}) on {state.monitor}"
            )

        elif args.command == "status":
            st = runner.status()
            if not st.get("running"):
                print("Status: not running")
                if args.verbose:
                    print(st)
                return

            print(f"Status: running (PID={st['pid']}, PGID={st['pgid']})")
            print(f"Monitor: {st.get('monitor')}")
            print(f"File: {st.get('file')}")
            print(f"Mode: {st.get('mode', 'auto')}")

            if args.verbose:
                print(f"State file: {st.get('state_file')}")
                print(f"Log file:   {st.get('log_file')}")
                print(f"exists={st.get('exists')} is_mpvpaper={st.get('is_mpvpaper')}")

        elif args.command == "stop":
            runner.stop()
            print("Stopped.")

        elif args.command == "cache":
            if args.action == "clear":
                if paths.CACHE_DIR.exists():
                    for p in paths.CACHE_DIR.iterdir():
                        if p.is_dir():
                            shutil.rmtree(p, ignore_errors=True)
                        else:
                            try:
                                p.unlink()
                            except OSError:
                                pass
                paths.ensure_directories()
                print("Cache cleared.")
            else:
                n = cache_size_bytes(paths.CACHE_DIR)
                print(f"Cache size: {human_size(n)} ({n} bytes)")

    except Exception as e:
        print(f"Error: {e}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()