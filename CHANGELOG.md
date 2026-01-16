# Changelog

## v0.2.0 (Unreleased)

### Added
- **Smart Optimization System** — Automatic video encoding with three performance profiles (eco, balanced, quality)
- **Intelligent Caching** — Content-based fingerprinting to avoid redundant re-encoding
- **Resolution-aware Scaling** — Automatic scaling to monitor's native resolution
- **Image-to-Video Conversion** — Static images converted to 2-second looped videos for consistent playback
- **Cache Management Commands** — View cache size and clear cache via CLI
- **Profile Selection** — `--profile` flag to choose optimization level or disable it entirely

### Changed
- FFmpeg now required for video optimization features
- Cache directory structure reorganized for better organization

### Technical Details
- H.264 encoding with configurable CRF (20-28) and presets (fast to veryfast)
- SHA-256 fingerprinting for cache keys based on source file metadata and encoding settings
- Optimized files stored in `~/.cache/hyprwall/optimized/`

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
