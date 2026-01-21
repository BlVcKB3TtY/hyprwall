"""CLI command: profile - Manage profile overrides."""

import time
from pathlib import Path

from hyprwall.core import hypr, optimize, runner
from hyprwall.core.session import Session, load_session, save_session
from hyprwall.cli.cli_common import (
    animate_progress,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)


def get_reference_resolution(ref_monitor_name: str) -> tuple[int, int]:
    """
    Get resolution from ref_monitor, with fallback to focused>largest if invalid.

    Args:
        ref_monitor_name: Name of the reference monitor (may be empty or invalid)

    Returns:
        Tuple of (width, height)

    Raises:
        RuntimeError: If no monitors are detected
    """
    if ref_monitor_name:
        try:
            return hypr.monitor_resolution(ref_monitor_name)
        except RuntimeError:
            pass  # Monitor not found, fallback below

    # Fallback: pick reference monitor
    all_mons = hypr.list_monitors()
    if not all_mons:
        raise RuntimeError("No monitors detected")

    ref_mon = hypr.pick_reference_monitor(all_mons)
    if not ref_mon:
        raise RuntimeError("No valid reference monitor found")

    return ref_mon.width, ref_mon.height


def run(args):
    """Execute the 'profile' command."""
    print_header("Profile Management")
    sess = load_session()
    if not sess:
        print_error("No session found. Run 'hyprwall set' first.")
        raise SystemExit(1)

    if args.action == "set":
        if not args.profile_name:
            print_error("Profile name required for 'set' action")
            print_info("Usage", "hyprwall profile set <eco|balanced|quality|eco_strict>", indent=1)
            raise SystemExit(1)

        target_profile = args.profile_name

        print_info("Current profile", sess.last_profile)
        print_info("Override to", target_profile)
        print()

        # Resolve OptimizeProfile object
        prof = {
            "eco": optimize.ECO,
            "balanced": optimize.BALANCED,
            "quality": optimize.QUALITY,
            "eco_strict": optimize.ECO_STRICT,
        }[target_profile]

        # Re-optimize and apply
        src = Path(sess.source)
        w, hres = get_reference_resolution(sess.ref_monitor)

        animate_progress("Optimizing video", 1.0)
        res = optimize.ensure_optimized(
            src,
            width=w,
            height=hres,
            profile=prof,
            mode=sess.mode,
            codec=sess.codec,
            encoder=sess.encoder,
            verbose=args.verbose,
        )

        runner.stop()
        # Global start (all monitors) - ref_monitor used only for resolution hint
        all_monitors = hypr.list_monitors()
        entries = [
            runner.StartManyEntry(monitor=m.name, file=res.path, mode=sess.mode)
            for m in all_monitors
        ]
        runner.start_many(entries)

        # Save with override set
        save_session(Session(
            source=sess.source,
            ref_monitor=sess.ref_monitor,
            mode=sess.mode,
            codec=sess.codec,
            encoder=sess.encoder,
            auto_power=sess.auto_power,
            last_profile=target_profile,
            last_switch_at=time.time(),
            cooldown_s=sess.cooldown_s,
            override_profile=target_profile,  # Set override
        ))

        print_success(f"Profile set to: {target_profile}")
        print_warning("Auto power switching is now DISABLED")
        print_info("Tip", "Run 'hyprwall profile auto' to re-enable automatic switching", indent=1)
        print()

    elif args.action == "auto":
        if sess.override_profile is None:
            print_success("Auto mode already active")
            print()
            raise SystemExit(0)

        print_info("Previous override", sess.override_profile)
        print_info("Resuming", "automatic profile switching")
        print()

        # Clear override
        save_session(Session(
            source=sess.source,
            ref_monitor=sess.ref_monitor,
            mode=sess.mode,
            codec=sess.codec,
            encoder=sess.encoder,
            auto_power=sess.auto_power,
            last_profile=sess.last_profile,
            last_switch_at=sess.last_switch_at,
            cooldown_s=sess.cooldown_s,
            override_profile=None,  # Clear override
        ))

        print_success("Automatic profile switching re-enabled")
        if sess.auto_power:
            print_info("Tip", "Run 'hyprwall auto' daemon to apply automatic switching", indent=1)
        else:
            print_warning("Note: auto_power is disabled in session")
            print_info("Tip", "Run 'hyprwall set --auto-power' to enable it", indent=1)
        print()