# Changelog

## v0.2.0 (2026-01-16)

### Added
- **Smart Optimization System** — Automatic video encoding with four performance profiles (eco, balanced, quality, av1-eco)
- **Hardware Acceleration Support** — NVENC and VAAPI encoder support with automatic detection
- **AV1 VAAPI Encoding** — Hardware-accelerated AV1 encoding for AMD GPUs (Radeon 780M and similar)
- **Intelligent Caching** — Content-based fingerprinting to avoid redundant re-encoding
- **Resolution-aware Scaling** — Automatic scaling to monitor's native resolution
- **Image-to-Video Conversion** — Static images converted to 2-second looped videos for consistent playback
- **Cache Management Commands** — View cache size and clear cache via CLI
- **Profile Selection** — `--profile` flag to choose optimization level or disable it entirely
- **Encoder Selection** — `--encoder` flag to choose between auto, cpu, nvenc, or vaapi

### Changed
- FFmpeg now required for video optimization features
- Cache directory structure reorganized for better organization
- Encoder selection logic rewritten for hardware-specific capabilities
- H.264 VAAPI disabled on AMD GPUs (not supported by Radeon 780M)
- AV1 VAAPI now uses `-quality` parameter instead of `-qp` (ffmpeg compatibility fix)

### Fixed
- **VAAPI H.264 encoding disabled** — Removed non-functional VAAPI H.264 support on AMD Radeon 780M
- **AV1 VAAPI encoding corrected** — Fixed ffmpeg parameter from `-qp` to `-quality`
- **Deterministic encoder selection** — No more implicit fallback in strict mode
- **Bug in paths.py** — Fixed duplicate `LOG_FILE` declaration causing import errors

### Technical Details
- **Codec-specific encoder mapping**:
  - H.264: CPU (libx264) or NVENC only
  - VP9: CPU (libvpx-vp9) only
  - AV1: VAAPI only (hardware-accelerated on AMD)
- SHA-256 fingerprinting for cache keys based on source file metadata and encoding settings
- Optimized files stored in `~/.cache/hyprwall/optimized/`
- Centralized `CODEC_ENCODERS` mapping reflects real hardware capabilities
- Simplified `ensure_optimized()` logic with deterministic behavior

### Performance
- Hardware-accelerated AV1 encoding reduces CPU usage on AMD GPUs
- NVENC support for NVIDIA GPUs reduces CPU usage for H.264 encoding
- Intelligent encoder auto-selection prioritizes hardware acceleration when available

## v0.1.0

### Added
- Initial CLI release
- Basic wallpaper switching
- Multi-format support (images and videos)
- Multiple rendering modes (auto, fit, cover, stretch)
- Multi-monitor support via hyprctl
- Directory support (selects most recent file)
- Safe process handling for mpvpaper
- XDG Base Directory compliance
- State persistence and status inspection
- Automatic swww conflict resolution
- First public version
