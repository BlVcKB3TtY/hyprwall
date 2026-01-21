"""CLI command: status - Show current wallpaper status."""

from hyprwall.core import runner
from hyprwall.cli.cli_common import (
    print_header,
    print_info,
    print_separator,
    print_warning,
    Colors,
)


def run(args):
    """Execute the 'status' command."""
    print_header("Wallpaper Status")
    st = runner.status()

    if not st.get("running"):
        print_warning("No wallpaper is currently running")
        if args.verbose:
            print()
            print(f"{Colors.DIM}Raw state: {st}{Colors.RESET}")
        return

    # Check if multi-monitor
    if st.get("multi"):
        print_info("Status", f"{Colors.BRIGHT_GREEN}Running (Multi-Monitor){Colors.RESET}")
        print_info("Monitors", str(len(st.get("monitors", {}))))
        print()

        for mon_name, mon_st in st.get("monitors", {}).items():
            print_separator("─", 40)
            print_info("Monitor", f"{Colors.BRIGHT_WHITE}{mon_name}{Colors.RESET}")
            print_info("Status", f"{Colors.BRIGHT_GREEN}Running{Colors.RESET}" if mon_st.get("running") else f"{Colors.BRIGHT_RED}Stopped{Colors.RESET}", indent=1)
            print_info("File", mon_st.get('file', 'unknown'), indent=1)
            print_info("Mode", mon_st.get('mode', 'auto'), indent=1)
            print_info("Process", f"PID={mon_st['pid']}, PGID={mon_st['pgid']}", indent=1)

            if args.verbose:
                print_info("Process exists", str(mon_st.get('exists', False)), indent=1)
                print_info("Is mpvpaper", str(mon_st.get('is_mpvpaper', False)), indent=1)

        print_separator("─", 40)

        if args.verbose:
            print()
            print_info("State file", st.get('state_file', 'unknown'))
            print_info("Log file", st.get('log_file', 'unknown'))
    else:
        # Single-monitor (legacy)
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