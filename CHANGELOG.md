# Changelog

## v0.3.0 (2026-01-17)

### Added
- **Auto Power Status Command** — `hyprwall auto --status` displays current power state, profile decisions, and override status
- **One-Shot Auto Evaluation** — `hyprwall auto --once` runs a single evaluation cycle without starting the daemon
- **Manual Profile Override System** — New `hyprwall profile` command for manual control
  - `hyprwall profile set <profile>` — Manually set a profile and disable auto switching
  - `hyprwall profile auto` — Clear override and resume automatic switching
- **Persistent Cooldown** — 60-second cooldown between profile switches (persists across daemon restarts)
- **systemd User Service** — Production-ready systemd service file for auto daemon
  - `hyprwall-auto.service` with automatic restart on failure
  - Logs visible via `journalctl --user -u hyprwall-auto -f`

### Changed
- **Session State Extended** — Added three new fields to session.json:
  - `last_switch_at` — Unix timestamp of last profile switch
  - `cooldown_s` — Configurable cooldown period (default: 60 seconds)
  - `override_profile` — Manual profile override (null when auto mode active)
- **Auto Daemon Improvements** — Enhanced daemon respects override state and cooldown logic
- **Policy Module** — New `should_switch()` helper enforces override and cooldown rules

### Technical Details
- Override state prevents auto daemon from changing profiles
- Cooldown check uses unix timestamps for persistence across restarts
- Session backward-compatible (new fields have sensible defaults)
- Auto daemon exits cleanly with `--status` flag (no loop)

### Migration
No breaking changes. Existing sessions will be loaded with default values:
- `last_switch_at` = 0.0 (no previous switch)
- `cooldown_s` = 60 (60-second default)
- `override_profile` = None (auto mode)

## v0.2.1 (2026-01-17)

### Changed
- **BREAKING: Profile/Codec/Encoder Separation** — Refactored optimization architecture for clarity and flexibility
  - `--profile` now only defines optimization level (eco/balanced/quality/off)
  - `--codec` is now a separate argument (h264/av1/vp9)
  - `--encoder` remains independent (auto/cpu/vaapi/nvenc)
  - **Removed `av1` profile** — Use `--profile eco --codec av1 --encoder vaapi` instead
- **Improved Error Messages** — Clear, actionable error messages when codec/encoder combinations are invalid
- **Updated TLDR Command** — Comprehensive documentation with new profile/codec/encoder structure

### Technical Details
- `OptimizeProfile` dataclass no longer contains `codec` field
- `crf` parameter renamed to `quality` for consistency across codecs
- `ensure_optimized()` now requires explicit `codec` parameter
- `cache_key()` includes codec as separate parameter (not from profile)
- Cache keys remain backward-compatible (different structure = new cache entry)

### Migration Guide
**Old command:**
```bash
hyprwall set video.mp4 --profile av1
```

**New command:**
```bash
hyprwall set video.mp4 --profile eco --codec av1 --encoder vaapi
```

**Default behavior (unchanged):**
- Profile: `balanced` (30fps, quality 24)
- Codec: `h264` (MP4 output)
- Encoder: `auto` (smart selection)

### Benefits
- **Clearer separation**: Profile = level, Codec = format, Encoder = backend
- **More flexibility**: Use eco/balanced/quality with any codec
- **Better errors**: Explicit messages with supported options
- **Easier to extend**: Adding codecs/encoders is now straightforward

## v0.2.0 (2026-01-16)

### Added
- **Smart Optimization System** — Automatic video encoding with four performance profiles (eco, balanced, quality, av1-eco)
  - **Note**: `av1-eco` profile was replaced in v0.2.1 with `--codec av1` argument
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
