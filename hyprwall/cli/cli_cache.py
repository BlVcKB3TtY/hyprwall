"""CLI command: cache - Manage optimization cache."""

import shutil

from hyprwall.core import paths
from hyprwall.core.paths import count_tree
from hyprwall.cli.cli_common import (
    animate_progress,
    cache_size_bytes,
    human_size,
    print_header,
    print_info,
    print_success,
)


def run(args):
    """Execute the 'cache' command."""
    if args.action == "clear":
        print_header("Cache Management")
        animate_progress("Clearing cache", 0.5)

        removed_dirs = 0
        removed_files = 0

        if paths.CACHE_DIR.exists():
            for p in paths.CACHE_DIR.iterdir():
                # Preserve state directory (state.json + pid files)
                if p.name == "state":
                    continue

                # Count what will be removed (recursive for directories)
                if p.is_dir():
                    d, f = count_tree(p)
                    # +1 for the directory itself (so 'optimized' counts too)
                    removed_dirs += d  # Directories inside
                    removed_files += f
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    try:
                        p.unlink()
                        removed_files += 1
                    except OSError:
                        pass

        paths.ensure_directories()
        print_success(
            f"Cache cleared successfully ({removed_dirs} dirs, {removed_files} files removed)"
        )
        print_info("State preserved", str(paths.STATE_DIR), indent=1)
        print()

    # Always show cache info for both "size" and after "clear"
    print_header("Cache Information")
    n = cache_size_bytes(paths.CACHE_DIR)

    # Show how many entries exist in optimized cache
    opt_dirs, opt_files = count_tree(paths.OPT_DIR)

    print_info("Cache location", str(paths.CACHE_DIR))
    print_info("Cache size", f"{human_size(n)} ({n:,} bytes)")
    print_info("Optimized entries", f"{opt_dirs} dirs, {opt_files} files")
    print()