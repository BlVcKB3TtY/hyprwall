"""HyprWall CLI - Main orchestrator."""

import argparse

from hyprwall.core import paths, runner
from hyprwall.cli import cli_auto, cli_cache, cli_profile, cli_set, cli_status, cli_tldr
from hyprwall.cli.cli_common import (
    print_banner,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
    Colors,
)


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

    # TLDR command parser
    sub.add_parser(
        "tldr",
        help="Quick project overview (Too Long; Didn't Read)",
        description="Display a quick overview of what HyprWall is and what it does."
    )

    # Set commands parser
    set_cmd = sub.add_parser(
        "set",
        help="Set a wallpaper (file or directory)",
        description="""Set a wallpaper on all monitors.
        
Supports images (jpg, png, gif, webp) and videos (mp4, mkv, webm).
When pointing to a directory, the most recent file will be used.
Wallpaper is applied to ALL active monitors.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    set_cmd.add_argument("path", type=str, help="Path to the image/video file OR directory")
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
        choices=["eco", "eco_strict", "balanced", "quality", "off"],
        default="balanced",
        metavar="PROFILE",
        help="""Optimization profile for videos (default: balanced)
  • eco        - 24fps, Quality 28, veryfast preset (low CPU/battery usage)
  • eco_strict - 18fps, Quality 30, veryfast preset (lowest CPU/battery usage)
  • balanced   - 30fps, Quality 24, veryfast preset (recommended)
  • quality    - 30fps, Quality 20, fast preset (best visual quality)
  • off        - No optimization, use source file directly""",
    )
    set_cmd.add_argument(
        "--codec",
        choices=["h264", "av1", "vp9"],
        default="h264",
        metavar="CODEC",
        help="""Video codec for encoding (default: h264)
  • h264 - H.264/AVC codec, outputs MP4 (widely compatible)
  • av1  - AV1 codec, outputs MKV (modern, efficient, requires VAAPI)
  • vp9  - VP9 codec, outputs WebM (open format, CPU only)""",
    )
    set_cmd.add_argument(
        "--encoder",
        choices=["auto", "cpu", "vaapi", "nvenc"],
        default="auto",
        metavar="ENC",
        help="""Encoding backend (default: auto)
  • auto  - Smart selection: NVENC > CPU for H.264, VAAPI for AV1, CPU for VP9
  • cpu   - Software encoding (libx264/libvpx-vp9, no hardware acceleration)
  • vaapi - Intel/AMD hardware encode (strict, no fallback) - AV1 only
  • nvenc - NVIDIA hardware encode (strict, no fallback) - H.264 only""",
    )

    set_cmd.add_argument(
        "--auto-power",
        action="store_true",
        help="Enable dynamic profile switching based on battery/AC state"
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
        help="Stop all wallpapers",
        description="Stop all currently running wallpapers (mpvpaper processes)."
    )

    # Auto commands parser
    auto_cmd = sub.add_parser(
        "auto",
        help="Run auto power-aware profile switching daemon",
        description="""Run the automatic power-aware profile switching daemon.

This daemon monitors your power status (AC/battery) and battery level to automatically
switch between optimization profiles. Requires a session created with --auto-power.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    auto_cmd.add_argument(
        "--once",
        action="store_true",
        help="Run one evaluation cycle and exit (no daemon loop)"
    )
    auto_cmd.add_argument(
        "--status",
        action="store_true",
        help="Show current auto power status and exit"
    )

    # Profile commands parser
    profile_cmd = sub.add_parser(
        "profile",
        help="Manage profile overrides",
        description="""Manually override automatic profile switching.
        
When an override is set, the auto daemon will not change profiles automatically.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    profile_cmd.add_argument(
        "action",
        choices=["set", "auto"],
        help="""Profile action
  • set  - Manually set a specific profile (disables auto switching)
  • auto - Clear override and resume automatic switching"""
    )
    profile_cmd.add_argument(
        "profile_name",
        nargs="?",
        choices=["eco", "balanced", "quality", "eco_strict"],
        help="Profile to set (required for 'set' action)"
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


# Command dispatcher
COMMANDS = {
    "set": cli_set.run,
    "status": cli_status.run,
    "auto": cli_auto.run,
    "profile": cli_profile.run,
    "cache": cli_cache.run,
    "tldr": cli_tldr.run,
}


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
        if args.command == "stop":
            from hyprwall.cli.cli_common import animate_progress
            animate_progress("Stopping wallpaper(s)", 0.5)
            was_stopped = runner.stop()

            if was_stopped:
                print_success("Wallpaper(s) stopped successfully")
            else:
                print_warning("No wallpaper process was running")
            print()
        else:
            # Dispatch to appropriate command handler
            handler = COMMANDS.get(args.command)
            if handler:
                handler(args)
            else:
                print_error(f"Unknown command: {args.command}")
                raise SystemExit(1)

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