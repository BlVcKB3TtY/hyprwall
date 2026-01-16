from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import shutil
from dataclasses import dataclass
from pathlib import Path

from hyprwall import paths
from hyprwall import hypr

# Type of images supported
from hyprwall.detect import IMAGE_EXTS

# Literal type for wallpaper modes
from typing import Literal
Mode = Literal["auto", "fit", "cover", "stretch"]

@dataclass(frozen=True)
class RunState:
    pid: int
    pgid: int
    monitor: str
    file: str
    needle: str
    mode: str
    started_at: float

def _read_state() -> RunState | None:
    try:
        data = json.loads(paths.STATE_FILE.read_text())
        return RunState(
            pid=int(data["pid"]),
            pgid=int(data["pgid"]),
            monitor=str(data.get("monitor", "")),
            file=str(data.get("file", "")),
            mode=str(data.get("mode", "auto")),
            started_at=float(data.get("started_at", 0.0)),
            needle=str(data.get("needle") or data.get("file", "")),
        )
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError):
        return None

def _write_state(state: RunState) -> None:
    paths.STATE_DIR.mkdir(parents=True, exist_ok=True)
    paths.STATE_FILE.write_text(
        json.dumps(
            {
                "pid": state.pid,
                "pgid": state.pgid,
                "monitor": state.monitor,
                "file": state.file,
                "mode": state.mode,
                "started_at": state.started_at,
                "needle": state.needle,
            },
            indent=2,
        )
        + "\n"
    )

def _remove_statefile() -> None:
    try:
        paths.STATE_FILE.unlink()
    except FileNotFoundError:
        pass

def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

def _cmdline_contains(pid: int, needle: str) -> bool:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        # /proc/<pid>/cmdline is null-byte separated
        txt = raw.replace(b"\0", b" ").decode(errors="ignore")
        return needle in txt
    except FileNotFoundError:
        return False
    except Exception:
        return False

def _is_mpvpaper(pid: int) -> bool:
    return _process_exists(pid) and _cmdline_contains(pid, "mpvpaper")

def _pgid_has_processes(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

def _terminate_group(pgid: int, timeout_s: float = 2.0, poll_s: float = 0.05) -> None:
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not _pgid_has_processes(pgid):
            return
        time.sleep(poll_s)

    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        return

def stop(timeout_s: float = 2.0) -> bool:
    state = _read_state()

    # No state: nothing we can precisely target
    if state is None:
        return False

    # Best effort: try killing stored pgid/pid if they exist
    if _process_exists(state.pid) and _is_mpvpaper(state.pid):
        _terminate_group(state.pgid, timeout_s=timeout_s)
        try:
            os.kill(state.pid, signal.SIGKILL)
        except Exception:
            pass

    # Robust verification: look for a remaining mpvpaper matching monitor + needle
    monitor = state.monitor
    needle = getattr(state, "needle", "") or state.file

    pids = _find_mpvpaper_pids(monitor=monitor, needle=needle)
    if not pids:
        # If needle match fails (maybe file changed), fallback to monitor-only
        pids = _find_mpvpaper_pids(monitor=monitor, needle="")

    if pids:
        # Kill them (TERM -> KILL)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        time.sleep(0.1)
        for pid in pids:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except Exception:
                pass

        # Recheck
        still = _find_mpvpaper_pids(monitor=monitor, needle=needle) or _find_mpvpaper_pids(monitor=monitor, needle="")
        if still:
            # Do NOT remove state, because wallpaper is still running
            return False

    _remove_statefile()
    return True

def _is_image(file: Path) -> bool:
    return file.suffix.lower() in IMAGE_EXTS

def _mpv_options_for(
        file: Path,
        mode: Mode = "auto",
        target_w: int | None = None,
        target_h: int | None = None,
) -> str:
    """
    mpv options via mpvpaper -o "<opts>"
    Modes:
    - fit:    keepaspect
    - cover:  scale=increase + crop (fill, no letterbox)
    - stretch: keepaspect=no (distort to fit)
    - auto: image->cover, video->fit
    """
    ext = file.suffix.lower()
    opts = ["--no-audio", "--no-border", "--really-quiet", "--hwdec=auto-safe"]

    # Auto decision
    if mode == "auto":
        mode = "cover" if _is_image(file) else "fit"

    if mode == "fit":
        # Default mpv behavior keeps aspect ratio
        opts.append("--keepaspect=yes")

    elif mode == "stretch":
        opts.append("--keepaspect=no")

    elif mode == "cover":
        if not (target_w and target_h):
            # Fallback to stretch if no target size
            opts.append("--keepaspect=no")
        else:
            vf = (
                f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
                f"crop={target_w}:{target_h}"
            )
            opts.append(f"--vf={vf}")

    else:
        raise ValueError(f"Unknown mode: {mode}")

    if ext in IMAGE_EXTS:
        opts.append("--image-display-duration=inf")
    else:
        opts.append("--loop-file=inf")

    return " ".join(opts)

def _find_mpvpaper_pids(monitor: str = "", needle: str = "") -> list[int]:
    pids: list[int] = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        pid = int(d.name)
        try:
            txt = (d / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
        except Exception:
            continue
        if "mpvpaper" not in txt:
            continue
        if monitor and f" {monitor} " not in f" {txt} ":
            continue
        if needle and needle not in txt:
            continue
        pids.append(pid)
    return pids

def start(
    monitor: str,
    file: Path,
    extra_args: list[str] | None = None,
    mode: Mode = "auto",
) -> RunState:
    if shutil.which("mpvpaper") is None:
        raise RuntimeError("mpvpaper not found in PATH. Install it first.")

    extra_args = extra_args or []
    file = Path(file)

    w, h = hypr.monitor_resolution(monitor)

    effective_mode: Mode = mode
    if mode == "auto":
        effective_mode = "cover" if _is_image(file) else "fit"

    mpv_opts = _mpv_options_for(
        file,
        mode=effective_mode,
        target_w=w,
        target_h=h,
    )

    # Before starting, kill swww if running
    if shutil.which("swww"):
        subprocess.run(["pkill", "-x", "swww-daemon"], check=False)
        subprocess.run(["pkill", "-x", "swww"], check=False)

    paths.STATE_DIR.mkdir(parents=True, exist_ok=True)
    logf = paths.LOG_FILE.open("a")

    proc = subprocess.Popen(
        ["mpvpaper", "-o", mpv_opts, *extra_args, monitor, str(file)],
        stdout=logf,
        stderr=logf,
        start_new_session=True,
        text=False,
    )

    try:
        pgid = os.getpgid(proc.pid)
    except Exception:
        pgid = proc.pid

    needle = str(file)

    state = RunState(
        pid=proc.pid,
        pgid=pgid,
        monitor=monitor,
        file=str(file),
        needle=needle,
        mode=str(effective_mode),
        started_at=time.time(),
    )
    _write_state(state)
    return state

def status() -> dict:
    state = _read_state()
    if state is None:
        return {"running": False, "reason": "no state file"}

    exists = _process_exists(state.pid)
    is_mpv = _is_mpvpaper(state.pid) if exists else False

    running = bool(exists and is_mpv)
    if not running:
        running = bool(
            _find_mpvpaper_pids(monitor=state.monitor, needle=state.needle) or
            _find_mpvpaper_pids(monitor=state.monitor, needle="")
        )

    return {
        "running": running,
        "pid": state.pid,
        "pgid": state.pgid,
        "monitor": state.monitor,
        "file": state.file,
        "needle": state.needle,
        "exists": exists,
        "is_mpvpaper": is_mpv,
        "started_at": state.started_at,
        "state_file": str(paths.STATE_FILE),
        "mode": state.mode,
        "log_file": str(paths.LOG_FILE),
    }