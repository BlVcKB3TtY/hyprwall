"""CLI command: set - Set a wallpaper on all monitors."""

from hyprwall.core import detect, hypr, optimize, runner
from hyprwall.core.session import Session, save_session
from hyprwall.cli.cli_common import (
    animate_progress,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
    Colors,
)


def run(args):
    """Execute the 'set' command."""
    # Validate wallpaper path
    animate_progress("Validating wallpaper path", 0.3)
    valid_path = detect.validate_wallpaper(args.path)
    print_success(f"Wallpaper found: {Colors.DIM}{valid_path.name}{Colors.RESET}")

    # Detect all monitors (global-only)
    animate_progress("Detecting monitor configuration", 0.3)
    monitors = hypr.list_monitors()
    if not monitors:
        print_error("No monitors detected")
        raise SystemExit(1)

    print_success(f"Detected {len(monitors)} monitor(s):")
    for m in monitors:
        print_info(f"  • {m.name}", f"{m.width}×{m.height}", indent=1)

    target_monitors = [(m.name, m.width, m.height) for m in monitors]

    # Validate auto-power settings
    if args.auto_power and args.profile == "off":
        print_error("Cannot use --auto-power with --profile off")
        raise SystemExit(1)

    # Display configuration
    print_header("Configuration")
    print_info("Source", str(valid_path))
    print_info("Mode", args.mode)
    print_info("Target", f"All monitors ({len(target_monitors)})")
    print_info("Profile", args.profile if args.profile != "off" else "off (no optimization)")
    if args.profile != "off":
        print_info("Codec", args.codec.upper())
        print_info("Encoder", args.encoder)
    print()

    # Optimization phase - optimize per resolution
    monitor_files = {}  # {monitor_name: file_to_play}

    if args.profile != "off":
        prof = {
            "eco": optimize.ECO,
            "eco_strict": optimize.ECO_STRICT,
            "balanced": optimize.BALANCED,
            "quality": optimize.QUALITY,
        }[args.profile]

        print_header("Optimization")

        # Group monitors by resolution to avoid duplicate optimizations
        res_to_monitors = {}
        for mon_name, w, h in target_monitors:
            key = (w, h)
            if key not in res_to_monitors:
                res_to_monitors[key] = []
            res_to_monitors[key].append(mon_name)

        # Optimize once per unique resolution
        res_to_file = {}
        for (w, h), mon_names in res_to_monitors.items():
            animate_progress(f"Optimizing for {w}×{h} ({len(mon_names)} monitor(s))", 0.5)

            res = optimize.ensure_optimized(
                valid_path,
                width=w,
                height=h,
                profile=prof,
                mode=args.mode,
                codec=args.codec,
                encoder=args.encoder,
                verbose=args.verbose,
            )

            res_to_file[(w, h)] = res.path

            # Display truthful information about what happened
            if res.cache_hit:
                print_success(f"Cache hit for {w}×{h}")
                if args.verbose:
                    print_info("Encoder used", res.used, indent=1)
            else:
                if res.used == res.chosen:
                    print_success(f"Encoded {w}×{h} with {res.used.upper()}")
                else:
                    print_warning(f"{res.chosen.upper()} failed, fallback to {res.used.upper()} (auto mode)")

            if args.verbose:
                print_info("Optimized file", str(res.path), indent=1)
                if res.requested != res.chosen:
                    print_info("Encoder selection", f"requested={res.requested}, chosen={res.chosen}, used={res.used}", indent=1)

        # Map monitors to their optimized files
        for mon_name, w, h in target_monitors:
            monitor_files[mon_name] = res_to_file[(w, h)]

        print()
    else:
        # No optimization - use source file for all
        for mon_name, w, h in target_monitors:
            monitor_files[mon_name] = valid_path

    # Stop existing wallpaper
    animate_progress("Stopping existing wallpaper", 0.3)
    runner.stop()

    # Start wallpaper on all monitors (global-only)
    print_header("Starting Wallpapers")
    entries = [
        runner.StartManyEntry(
            monitor=mon_name,
            file=monitor_files[mon_name],
            mode=args.mode,
        )
        for mon_name, w, h in target_monitors
    ]

    animate_progress("Starting wallpapers on all monitors", 0.5)
    multi_state = runner.start_many(entries, extra_args=[])

    print_success(f"Started on {len(multi_state.monitors)} monitor(s)")
    for mon_name in multi_state.monitors:
        print_info(f"  • {mon_name}", f"PID={multi_state.monitors[mon_name].pid}", indent=1)

    # Save session with real reference monitor (focused > largest)
    ref_mon = hypr.pick_reference_monitor(monitors)
    save_session(Session(
        source=str(valid_path),
        ref_monitor=ref_mon.name if ref_mon else "",
        mode=str(args.mode),
        codec=str(args.codec),
        encoder=str(args.encoder),
        auto_power=bool(args.auto_power),
        last_profile=args.profile if args.profile != "off" else "off",
        last_switch_at=0.0,
        cooldown_s=60,
        override_profile=None,
    ))

    print()
