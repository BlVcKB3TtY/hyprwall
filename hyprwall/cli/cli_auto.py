"""CLI command: auto - Run auto power-aware profile switching daemon."""

import time
from pathlib import Path

from hyprwall.core import hypr, optimize, runner
from hyprwall.core.power import get_power_status
from hyprwall.core.policy import choose_profile, Hysteresis, should_switch
from hyprwall.core.session import Session, load_session, save_session
from hyprwall.cli.cli_common import (
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
    """Execute the 'auto' command."""
    sess = load_session()
    if not sess:
        print_error("No session found. Run 'hyprwall set ... --auto-power' first.")
        raise SystemExit(1)

    if not sess.auto_power:
        print_warning("auto_power is disabled in session. Re-run set with --auto-power.")
        raise SystemExit(1)

    # Handle --status flag
    if args.status:
        print_header("Auto Power Status")
        st = get_power_status()
        h = Hysteresis()
        target = choose_profile(st, sess.last_profile, h)

        print_info("Power State", f"AC={st.on_ac}, Battery={st.percent}%")
        print_info("Last Profile", sess.last_profile)
        print_info("Target Profile", target)
        print_info("Auto Power", "enabled" if sess.auto_power else "disabled")
        print_info("Override", sess.override_profile or "none")
        print_info("Cooldown", f"{sess.cooldown_s}s")

        elapsed = int(time.time() - sess.last_switch_at) if sess.last_switch_at > 0 else 0
        if sess.last_switch_at > 0:
            print_info("Last Switch", f"{elapsed}s ago")
        else:
            print_info("Last Switch", "never")

        print()

        if sess.override_profile:
            print_warning(f"Manual override active: {sess.override_profile}")
            print_info("Tip", "Run 'hyprwall profile auto' to resume automatic switching", indent=1)
        elif target != sess.last_profile:
            can_switch = should_switch(
                target,
                sess.last_profile,
                sess.last_switch_at,
                sess.cooldown_s,
                sess.override_profile
            )
            if can_switch:
                print_success(f"Ready to switch to: {target}")
            else:
                remaining = sess.cooldown_s - elapsed
                if remaining < 0:
                    remaining = 0
                print_warning(f"Cooldown active: {remaining}s remaining")
        else:
            print_success("Profile is optimal")

        print()
        raise SystemExit(0)

    # Normal daemon mode
    print_header("Auto Power Profiles")
    h = Hysteresis()
    last = sess.last_profile

    print_info("Source", sess.source)
    print_info("Monitor", sess.ref_monitor)
    print_info("Mode", sess.mode)
    print_info("Codec", sess.codec)
    print_info("Encoder", sess.encoder)
    print_info("Last profile", last)
    if sess.override_profile:
        print_info("Override", sess.override_profile)
    print()

    if not args.once:
        print_success("Auto power daemon started. Press Ctrl+C to stop.")
        print()

    while True:
        st = get_power_status()
        target = choose_profile(st, last, h)

        # Check if switch is allowed (respects override and cooldown)
        if should_switch(target, last, sess.last_switch_at, sess.cooldown_s, sess.override_profile):
            print_info("Power", f"on_ac={st.on_ac} percent={st.percent}")
            print_warning(f"Switch profile: {last} -> {target}")

            # Resolve OptimizeProfile object
            prof = {
                "eco": optimize.ECO,
                "balanced": optimize.BALANCED,
                "quality": optimize.QUALITY,
                "eco_strict": optimize.ECO_STRICT,
            }[target]

            # Re-optimize from SOURCE (not cached optimized file)
            src = Path(sess.source)
            w, hres = get_reference_resolution(sess.ref_monitor)

            res = optimize.ensure_optimized(
                src,
                width=w,
                height=hres,
                profile=prof,
                mode=sess.mode,
                codec=sess.codec,
                encoder=sess.encoder,
                verbose=False,
            )

            runner.stop()
            # Global start (all monitors) - ref_monitor used only for resolution hint
            all_monitors = hypr.list_monitors()
            entries = [
                runner.StartManyEntry(monitor=m.name, file=res.path, mode=sess.mode)
                for m in all_monitors
            ]
            runner.start_many(entries)

            last = target
            save_session(Session(
                source=sess.source,
                ref_monitor=sess.ref_monitor,
                mode=sess.mode,
                codec=sess.codec,
                encoder=sess.encoder,
                auto_power=True,
                last_profile=last,
                last_switch_at=time.time(),
                cooldown_s=sess.cooldown_s,
                override_profile=sess.override_profile,
            ))

            # debounce
            time.sleep(10)

        # Exit if --once flag
        if args.once:
            if target == last:
                print_success(f"Profile is optimal: {last}")
            print()
            break

        # polling interval
        if st.on_ac is True:
            time.sleep(90)
        else:
            time.sleep(25)