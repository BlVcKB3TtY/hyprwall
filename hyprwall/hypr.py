from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Monitor:
    name: str
    width: int
    height: int
    refresh: float | None = None
    focused: bool = False

def _run_hyprctl_json(args: list[str]) -> Any:
    """
    Run hyprctl command and parse JSON output.
    """
    try:
        proc = subprocess.run(
            ["hyprctl", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError("hyprctl not found in PATH. Are you running Hyprland?") from e
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or "").strip() or (e.stdout or "").strip() or str(e)
        raise RuntimeError(f"hyprctl failed: {msg}") from e

    return json.loads(proc.stdout)


def list_monitors() -> list[Monitor]:
    data = _run_hyprctl_json(["monitors", "-j"])
    monitors: list[Monitor] = []

    # hyprctl returns a list of dicts
    for m in data:
        monitors.append(
            Monitor(
                name=m.get("name", ""),
                width=int(m.get("width", 0)),
                height=int(m.get("height", 0)),
                refresh=float(m.get("refreshRate")) if m.get("refreshRate") is not None else None,
                focused=bool(m.get("focused", False)),
            )
        )

    return monitors

def default_monitor_name() -> str:
    monitors = list_monitors()
    if not monitors:
        raise RuntimeError("No monitors found via hyprctl.")

    focused = [m for m in monitors if m.focused]
    return (focused[0] if focused else monitors[0]).name

def monitor_by_name(name: str) -> Monitor:
    monitors = list_monitors()
    for m in monitors:
        if m.name == name:
            return m
    raise RuntimeError(f"Monitor '{name}' not found via hyprctl.")

def monitor_resolution(name: str) -> tuple[int, int]:
    m = monitor_by_name(name)
    if m.width <= 0 or m.height <= 0:
        raise RuntimeError(f"Invalid resolution for monitor '{name}': {m.width}x{m.height}")
    return m.width, m.height