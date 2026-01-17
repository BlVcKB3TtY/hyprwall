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
- **Smart optimization** — Automatic video encoding with three performance profiles
- **Intelligent caching** — Content-based fingerprinting avoids redundant re-encoding
- **Resolution-aware** — Automatically scales to your monitor's native resolution
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
- [ffmpeg](https://ffmpeg.org/) — Video encoding and optimization
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

### Optimization Profiles

HyprWall automatically optimizes wallpapers for performance and battery life using ffmpeg.

#### Profiles (Optimization Level)

Profiles define the FPS and quality level, independent of codec choice:

```bash
hyprwall set file.mp4 --profile balanced  # default
hyprwall set file.mp4 --profile eco       # maximum battery savings
hyprwall set file.mp4 --profile quality   # best visual quality
hyprwall set file.mp4 --profile off       # no optimization, use source
```

| Profile | FPS | Quality (CRF/QP) | Preset | Use Case |
|---------|-----|------------------|--------|----------|
| `eco` | 24 | 28 | veryfast | Maximum battery life |
| `balanced` | 30 | 24 | veryfast | Good balance (default) |
| `quality` | 30 | 20 | fast | Best visual quality |
| `off` | — | — | — | Use source file directly (no re-encoding) |

#### Video Codecs

Choose the output format independently of the optimization profile:

```bash
hyprwall set file.mp4 --codec h264  # default (MP4)
hyprwall set file.mp4 --codec av1   # modern, efficient (MKV)
hyprwall set file.mp4 --codec vp9   # open format (WebM)
```

| Codec | Output Format | Description | Hardware Support |
|-------|---------------|-------------|------------------|
| `h264` | MP4 | Widely compatible (default) | CPU, NVENC |
| `av1` | MKV | Modern, efficient | VAAPI only |
| `vp9` | WebM | Open format | CPU only |

#### Combined Example

```bash
# AV1 with ECO profile and VAAPI hardware encoding
hyprwall set file.mp4 --profile eco --codec av1 --encoder vaapi

# H.264 with QUALITY profile and CPU encoding
hyprwall set file.mp4 --profile quality --codec h264 --encoder cpu
```

**How it works:**
- Videos are automatically re-encoded to your monitor's native resolution
- Static images are converted to 2-second looped videos for consistent playback
- Optimized files are cached using content-based fingerprinting
- Cache avoids redundant re-encoding when using the same file with identical settings

### Hardware Acceleration

HyprWall supports hardware-accelerated encoding for improved performance:

```bash
# Automatic encoder selection (default, recommended)
hyprwall set file.mp4 --encoder auto

# Force CPU encoding (libx264/libvpx-vp9)
hyprwall set file.mp4 --encoder cpu

# Force NVIDIA NVENC (H.264 only)
hyprwall set file.mp4 --codec h264 --encoder nvenc

# Force VAAPI (AV1 only, AMD/Intel)
hyprwall set file.mp4 --codec av1 --encoder vaapi
```

**Codec/Encoder Compatibility:**

| Codec | CPU | VAAPI | NVENC |
|-------|-----|-------|-------|
| **H.264** | libx264 | Not supported* | h264_nvenc |
| **AV1** | Not supported | av1_vaapi | Not supported |
| **VP9** | libvpx-vp9 | Not supported | Not supported |

\* VAAPI H.264 encoding is not supported on AMD Radeon 780M due to hardware limitations.

**Auto Mode Behavior:**
- **H.264**: Tries NVENC (if NVIDIA GPU detected), falls back to CPU
- **AV1**: Uses VAAPI (requires AMD/Intel GPU with AV1 support)
- **VP9**: Uses CPU (only option available)

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

HyprWall caches optimized wallpapers to avoid redundant re-encoding:

```bash
# View cache size
hyprwall cache

# Clear cache
hyprwall cache clear
```

**Cache behavior:**
- Each unique combination of source file, resolution, and profile gets a unique cache key
- Cache keys use SHA-256 fingerprints based on file path, size, modification time, and encoding settings
- Optimized files are stored in `~/.cache/hyprwall/optimized/`
- Changing source files or encoding settings automatically triggers re-encoding

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

**Made with ❤ for the Hyprland community**

[Report Bug](https://github.com/TheOnlyChou/hyprwall/issues) • [Request Feature](https://github.com/TheOnlyChou/hyprwall/issues)

</div>

