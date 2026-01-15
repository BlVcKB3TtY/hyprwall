<div align="center">

# HyprWall

**Lightweight wallpaper manager for Hyprland**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Hyprland](https://img.shields.io/badge/Hyprland-compatible-purple)](https://hyprland.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Documentation](#documentation)

</div>

---

## Overview

HyprWall is a lightweight wallpaper manager for Hyprland, built on top of mpvpaper. It supports both images and videos with automatic aspect-ratio handling and multiple rendering modes designed for performance and battery efficiency.

Unlike heavier "wallpaper engines", HyprWall is designed with a focus on:

- **Predictability** — clean process management and deterministic behavior
- **Performance** — minimal resource usage, battery-friendly
- **Simplicity** — no GUI bloat, just CLI efficiency
- **Wayland-native** — built specifically for modern Wayland compositors

## Features

- **Multi-format support** — Images and video wallpapers
- **Intelligent mode selection** — Automatic aspect ratio detection (images → cover, videos → fit)
- **Flexible rendering modes** — fit (letterbox), cover (crop), stretch (distort)
- **Multi-monitor aware** — Automatic detection via `hyprctl`
- **Directory support** — Automatically uses the most recent file from a directory
- **Safe process handling** — Kills stale mpvpaper instances, avoids PID reuse bugs
- **Persistent state** — Status inspection and XDG-compliant paths
- **Conflict resolution** — Automatically stops `swww` to prevent rendering conflicts

## Requirements

### Required
- [Hyprland](https://hyprland.org/) — Wayland compositor
- [mpvpaper](https://github.com/GhostNaN/mpvpaper) — Video wallpaper tool
- [mpv](https://mpv.io/) — Media player
- Python ≥ 3.10

### Optional
- [figlet](http://www.figlet.org/) — ASCII banner generation
- [swww](https://github.com/Horus645/swww) — Will be stopped automatically to avoid conflicts

## Installation

### From Source

```bash
git clone https://github.com/TheOnlyChou/hyprwall.git
cd hyprwall
python -m pip install -e .
```

This installs `hyprwall` into `~/.local/bin`.

### Using pip

```bash
pip install hyprwall
```

## Usage

### Set a Wallpaper

```bash
# Set an image wallpaper
hyprwall set ~/Pictures/wallpaper.jpg

# Set a video wallpaper
hyprwall set ~/Videos/wallpaper.mp4

# Use a directory (selects most recent file)
hyprwall set ~/Pictures/wallpapers
```

### Rendering Modes

```bash
hyprwall set file.jpg --mode auto     # default
hyprwall set file.jpg --mode cover    # fill screen, crop if needed
hyprwall set file.jpg --mode fit      # keep aspect ratio (letterbox)
hyprwall set file.jpg --mode stretch  # fill screen, distort
```

| Mode | Description |
|------|-------------|
| `auto` | Image → cover, video → fit |
| `fit` | Keep aspect ratio (letterbox) |
| `cover` | Fill screen, crop if needed |
| `stretch` | Fill screen, distort |

### Status & Control

#### Check Status

```bash
hyprwall status
```

**Output example:**
```
Status: running
Monitor: eDP-1
File: /home/user/Pictures/wallpaper.jpg
Mode: cover
```

#### Stop Wallpaper

```bash
hyprwall stop
```

> **Note:** Under Wayland, stopping mpvpaper does not automatically redraw the background. The last frame may remain visible until another wallpaper source redraws the screen.

### Cache Management

```bash
# View cache information
hyprwall cache

# Clear cache
hyprwall cache clear
```

## Documentation

### XDG Base Directory Compliance

HyprWall follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir/latest/):

| Purpose | Path |
|---------|------|
| Config | `~/.config/hyprwall/` |
| Cache | `~/.cache/hyprwall/` |
| State | `~/.cache/hyprwall/state/` |

### Why not swww?

Both `swww` and `mpvpaper` attempt to draw the wallpaper layer. Running both simultaneously leads to:

- Flickering
- Invisible wallpapers
- Undefined behavior

HyprWall automatically stops `swww-daemon` before launching mpvpaper to ensure deterministic results.

### Logs & Debugging

Logs are written to:
```
~/.cache/hyprwall/state/hyprwall.log
```

View recent logs:
```bash
tail -n 50 ~/.cache/hyprwall/state/hyprwall.log
```

> **Note:** Hardware decoding is set to a safe mode to avoid CUDA/NVIDIA warnings on non-NVIDIA systems.

## Project Goals

### HyprWall is **NOT**:
- A full Wallpaper Engine clone
- A GUI tool
- A heavy compositor plugin

### HyprWall **IS**:
- Predictable
- Debuggable
- Wayland-native
- Friendly to laptops and batteries

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on top of [mpvpaper](https://github.com/GhostNaN/mpvpaper)
- Designed for [Hyprland](https://hyprland.org/)
- Inspired by the need for lightweight, predictable wallpaper management

---

<div align="center">

Made with ❤️ for the Hyprland community

[Report Bug](https://github.com/TheOnlyChou/hyprwall/issues) • [Request Feature](https://github.com/TheOnlyChou/hyprwall/issues)

</div>

