# Changelog

## v0.7.0 (2026-01-19) - Performance Monitoring Module

### Added
- **Performance Monitoring Module** — Optional lightweight wallpaper performance tracking
  - New `hyprwall.perf` module with backend monitoring and GTK widget
  - Monitors CPU usage (process + children aggregation)
  - Monitors RAM usage (RSS in MiB)
  - GPU usage support (NVIDIA via nvidia-smi, AMD via sysfs)
  - CPU and GPU temperature monitoring via hwmon
  - Rolling average smoothing to avoid visual spikes
  - Fail-safe design: never crashes, shows "N/A" for unavailable metrics
  - Rate limiting: max 1 sample/second for minimal overhead
  - Clean GTK widget with dashboard layout
  - Full documentation in `hyprwall/perf/README.md`
  - CLI test script: `python -m hyprwall.perf.test_monitor <pid>`
  - Ready for GUI integration (toggle to show/hide)
  - Performance impact: ~0.1% CPU, ~2-3 MiB RAM

## v0.6.2 (2026-01-19) - Integrated Search & Cache Improvements

### Added
- **Integrated Search in Library** — Fast wallpaper search directly in Library view
  - Search bar positioned next to "Library:" label
  - Real-time filtering as you type
  - Automatically switches to list view when searching (better performance)
  - Returns to gallery view when search is cleared
  - Match counter shows filtered/total count (e.g., "12 / 245")
  - Optimized for large libraries (1000+ wallpapers)
  - Loads all wallpapers once on first search, then filters in memory
  - Clean UX: search integrated where it's needed, not hidden in a separate tab
  - **Preview on selection** — Click any search result to see wallpaper preview
    - Shows thumbnail for images (320x180)
    - Shows extracted frame for videos (320x180)
    - Preview appears above search results list
    - Includes filename label
    - Auto-hides when returning to gallery

### Changed
- **Simplified UI Navigation** — Removed separate Search tab
  - Search is now part of Library view (more intuitive)
  - Removed Gallery/List toggle (gallery is primary view)
  - List view only appears during search (performance optimization)
  - Cleaner interface with fewer toggles and tabs

### Fixed
- **Cache Clear Incomplete** — Now clears all cache types
  - Fixed: `cache clear` now removes both video cache AND thumbnail cache
  - Previously: only cleared `~/.cache/hyprwall/optimized` (videos)
  - Now also clears: `~/.cache/hyprwall/thumbs` (thumbnails)
  - Cache size statistics now include thumbnail cache
  - Proper cleanup prevents orphaned thumbnail files
- **Folder Dialog Cancel Error** — No more error popup on cancel
  - Fixed: Canceling folder selection dialog no longer shows error
  - Graceful handling of GLib.Error when user cancels
  - Clean UX: silent cancellation as expected
  - File chooser already handled cancellation correctly
- **Pagination in Search Mode** — Pagination bar now hidden during search
  - Prev/Next buttons automatically hidden when searching
  - All search results displayed in scrollable list (no pagination needed)
  - Pagination reappears when search is cleared and returning to gallery
  - Cleaner UI during search operations
- **Infinite Loader Bug** — Fixed library loading hang
  - Removed references to deleted `library_list` widget
  - Gallery pagination now renders correctly
  - Library loads properly on startup

### Technical
- **Search Implementation**
  - Search integrated in `library_stack` (switches between "gallery" and "search_results")
  - Filter state managed in `_filtered_search_items`
  - Search entry: `library_search_entry` (replaces old view mode toggle)
  - Results list: `library_search_list` (separate from gallery grid)
  - No separate view stack page, cleaner architecture

## v0.6.1 (2026-01-18) - Now Playing View & Enhanced Status

### Added
- **Now Playing View** — Dedicated tab for real-time wallpaper status
  - Clean navigation with Adw.ViewSwitcher between Library and Now Playing
  - Live wallpaper preview (image thumbnails or video frame extraction)
  - Detailed status per monitor: name, resolution, file, mode, PID
  - Session information: profile, codec, encoder, auto-power status
  - Auto-refresh every 2 seconds when view is visible
  - Empty state with helpful message when no wallpaper running
  - Professional "engine-ish" card layout with proper styling
- **Video Thumbnails in Status** — Now Playing shows preview for all media types
  - Images: scaled preview (400x225 for main view)
  - Videos: extracted frame at 1s via ffmpeg (320x180 cached)
  - Fallback: icon display if thumbnail generation fails
  - Reuses existing thumbnail cache system from gallery

### Changed
- **Main UI Navigation** — Reorganized for better workflow
  - Library view contains file/folder choosers and wallpaper browser
  - Now Playing view shows active wallpaper status and info
  - File/folder selection UI moved into Library tab
- **Status Display Simplified** — Removed redundant status label
  - Status info (file, mode, PID) moved entirely to Now Playing tab
  - Cleaner interface with no duplicate information
  - Status label below Start/Stop buttons removed
  - All detailed status now centralized in Now Playing view
- **Status Refresh Logic** — Improved responsiveness
  - Now Playing view refreshes on Start/Stop actions
  - Timer-based auto-refresh (2s) only runs when view is visible
  - Timer cleanup on view switch (prevents unnecessary updates)
  - Manual refresh option via view switch
- **CSS Styling** — Enhanced visual hierarchy
  - `.now-playing-panel` for container styling
  - `.now-playing-card` for info list boxes
  - `.now-playing-title` for section headers
  - Consistent with existing Wallpaper Engine-inspired theme

### Fixed
- **Signal Connection Bug** — Now Playing view now refreshes properly
  - Fixed missing GTK signal connection for view change
  - `notify::visible-child-name` signal now properly connected
  - Auto-initialization at startup for already-running wallpapers
  - Robust widget checking prevents crashes

### Technical
- **Architecture** — Clean separation of concerns
  - All status logic via `core.get_status()` and `core.load_session()`
  - No business logic in GUI layer
  - Proper GTK4/libadwaita patterns (AdwViewStack, AdwViewSwitcher)
  - Signal-based view change handling with timer management

## v0.6.0 (2026-01-18) - GUI Performance & UX Improvements

### Added
- **Pagination System** — Gallery and list views now paginated (15 items per page)
  - Prev/Next navigation buttons with page indicator
  - Automatic pagination bar visibility (hidden for ≤15 items)
  - Dramatically improves performance for large wallpaper folders
  - Prevents UI freeze when loading 100+ wallpapers
- **Single File Preview Mode** — Dedicated view for individually selected files
  - Clear thumbnail preview for chosen file (images and videos)
  - File information display (name, type, path)
  - Supports both Gallery and List view modes
  - Pagination bar automatically hidden in single file mode
- **Loading Screen** — Professional loading indicator during library scan
  - Animated spinner with "Loading wallpapers..." message
  - Helpful hint: "Large folders can take a while"
  - Smooth crossfade transitions between loading/content states
  - Prevents window layout jump during async loading
- **Default Library Folder** — Auto-load wallpaper library on startup
  - Configurable default folder persisted in `~/.config/hyprwall/gui_config.json`
  - Intelligent fallback: `~/Pictures/wallpapers/.../LiveWallpapers` → `~/Pictures` → `~`
  - Menu action "Reset Default Folder" to restore fallback behavior
  - Eliminates need to re-select folder on every launch
- **Cache Management** — GUI actions for cache control
  - Menu: "Cache Size" displays optimization cache statistics
  - Menu: "Clear Cache" with confirmation dialog
  - Integrates with existing core cache system

### Changed
- **Library Loading Redesigned** — Non-blocking async architecture
  - Background thread scanning with `core.iter_library()`
  - Main thread remains responsive during scan
  - Window geometry frozen during load (prevents Wayland recentering)
  - All items loaded before rendering (no progressive pop-in)
- **View Toggle Consistency** — Gallery/List buttons work in all modes
  - Single file preview supports both Gallery and List views
  - Folder library supports both Gallery and List views
  - View mode preserved when switching between file/folder
- **Window Stability** — Multiple fixes for layout jump issues
  - `library_container` always visible (no hide/show)
  - `library_outer_stack` with loading/single_file/content pages
  - Window size frozen during loading via `set_size_request()`
  - ScrolledWindow `propagate-natural-height=false`
  - Minimum height reserved for library area (340px)

### Fixed
- **Layout Jump Eliminated** — Window no longer repositions during loading
  - Root cause: `propagate-natural-height` causing geometry recalculation
  - Solution: Stable layout with frozen window size during operations
  - Tested on Wayland (Hyprland) with large wallpaper collections
- **FlowBox Placeholder Issue** — Loading placeholder properly removed
  - Used `get_first_child()` / `get_next_sibling()` GTK4 iteration
  - Placeholder removal happens before first batch render
  - Eliminates visual glitches during lazy loading
- **File vs Folder Confusion** — Clear UI distinction
  - "Choose file..." now shows single file preview (not folder gallery)
  - "Choose folder..." returns to folder library view
  - No more ambiguity about selected source

### Technical Details
- **Pagination Implementation:**
  - State: `_all_items`, `_page_size=15`, `_page_index`, `_total_pages`
  - Method: `_render_current_page()` slices items array
  - Thumbnails generated only for current page (max 15 at once)
  - Pagination bar styled with GTK toolbar class
- **Single File Preview:**
  - `single_file_view_stack` with gallery/list pages
  - Reuses `_make_picture_from_file()` and `_ensure_video_thumb()`
  - Thumbnail cache shared with folder library
- **Loading Architecture:**
  - `library_outer_stack`: loading → single_file → content
  - `_scan_library_thread()` runs in background
  - `GLib.idle_add()` for all GTK updates from thread
  - `_freeze_window_size()` / `_unfreeze_window_size()` guards
- **Performance:**
  - 15 thumbnails vs 200+ = 13x faster initial load
  - Background scanning keeps UI responsive
  - Smart caching avoids redundant video frame extraction

### Migration
- **No breaking changes** — All existing functionality preserved
- GUI config stored in new file: `~/.config/hyprwall/gui_config.json`
- First launch auto-detects default wallpaper folder
- Pagination automatically enabled (no configuration needed)

---

## v0.5.0 (2026-01-18) - GUI Overhaul & Global-Only Mode

### Added
- **GTK4 GUI Application** — Modern graphical interface with libadwaita
  - File chooser dialog for selecting wallpapers
  - Folder browser with wallpaper library view
  - Live monitor detection and display
  - Mode selection dropdown (auto/fit/cover/stretch)
  - Profile selection dropdown (off/eco/balanced/quality)
  - Auto-power toggle switch for battery-aware optimization
  - Real-time status display showing running wallpapers
- **Wallpaper Library View** — Browse local wallpaper collections
  - Choose folder to scan for supported media files
  - Scrollable list of all images and videos in folder
  - Click any item to select it as wallpaper source
  - Recursive directory scanning with filtering

### Changed
- **BREAKING: Global-Only Mode** — Simplified wallpaper behavior
  - `hyprwall set` always applies to ALL monitors (no more `--all` flag)
  - `hyprwall stop` always stops ALL monitors
  - Removed per-monitor selection from CLI and GUI
  - `--monitor` CLI flag removed (breaking change)
  - GUI no longer shows monitor dropdown
- **Session Format Updated** — Changed monitor field semantics
  - `monitor` field renamed to `ref_monitor` (reference monitor for resolution hint)
  - `ref_monitor` stores focused or largest monitor at time of set
  - Backward compatible: old `monitor` field auto-migrates to `ref_monitor`
- **API Refactored** — Core API becomes presentation-agnostic facade
  - New `HyprwallCore.set_wallpaper()` method with full business logic
  - All profile/mode/auto-power decisions moved from GUI to core
  - `start_wallpaper()` becomes compatibility wrapper
  - GUI reduced to pure presentation layer (no business logic)
- **Media Detection Enhanced** — New `find_supported_files()` in detect module
  - Recursive directory scanning for images and videos
  - Used by both CLI and GUI for consistent behavior
  - Returns sorted list of Path objects

### Fixed
- **Critical: Wallpaper Stacking Bug** — Wallpapers now replace instead of stack
  - `set_wallpaper()` now calls `runner.stop()` before `runner.start_many()`
  - Setting wallpaper B after wallpaper A properly kills A's processes
  - `stop` command removes all wallpapers permanently (no ghost processes)
  - Prevents mpvpaper process accumulation
- **Session Persistence** — Fixed ref_monitor handling
  - No longer stores pseudo-monitor `"__all__"` in session
  - Always stores real reference monitor name for resolution hints
  - Fallback logic in auto/profile commands handles missing monitors
- **Profile "off" Support** — Profile off now properly supported
  - Skips video optimization when profile is "off"
  - Maintains last_profile state for auto-power continuity
  - Never corrupts last_profile with "off" value

### Technical Details
- GUI built with GTK4 and libadwaita for modern GNOME aesthetics
- `HyprwallCore.list_library()` returns `MediaItem` dataclass with path and kind
- `pick_reference_monitor()` utility for deterministic monitor selection (focused > largest)
- State file cleanup ensures no orphaned mpvpaper processes
- GTK FileDialog replaces deprecated FileChooserNative

### Migration
- **Breaking:** Remove `--all` flag from scripts (now default behavior)
- **Breaking:** Remove `--monitor` flag from scripts (no longer supported)
- Old sessions with `monitor` field auto-migrate to `ref_monitor`
- GUI users: install GTK4/libadwaita dependencies (see README)

### Examples

```bash
# Set wallpaper (always global)
hyprwall set wallpaper.mp4 --profile balanced

# With auto-power mode
hyprwall set wallpaper.mp4 --auto-power

# Stop all wallpapers
hyprwall stop

# Launch GUI
hyprwall-gui
```

---

## v0.4.0 (2026-01-17) - Multi-Monitor Support

### Added
- **Multi-Monitor Mode** — Set wallpaper on all monitors with single command
  - `hyprwall set <file> --all` — Apply wallpaper to all active monitors
  - Same source file, optimized per resolution automatically
  - Intelligent caching: one optimization per unique resolution
- **Multi-Monitor Status** — Enhanced status display
  - Shows per-monitor information in multi-monitor setups
  - Displays running state, PID, file, and mode for each monitor
  - Backward-compatible with single-monitor status

### Changed
- **State File Format v2** — New multi-monitor state structure
  - Format: `{"version": 2, "monitors": {...}}`
  - Automatic v1 → v2 migration on write
  - Full backward compatibility with existing v1 state files
- **Session Convention** — Multi-monitor sessions use `monitor="__all__"`
  - Distinguishes multi-monitor from single-monitor sessions
  - Enables future auto-power support for multi-monitor
- **Optimization Logic** — Groups monitors by resolution
  - Avoids duplicate optimizations for monitors with same resolution
  - Reuses cache across monitors efficiently
- **Stop Command** — Simplified to always stop all monitors
  - `hyprwall stop` — Stops all running wallpapers (multi or single monitor)
  - Removed per-monitor stop option for simplicity

### Technical Details
- New `MultiRunState` and `MonitorRunState` dataclasses
- `start_many()` function for parallel monitor setup
- State migration is transparent and automatic
- Cache structure unchanged (per-resolution as before)

### Migration
- No action required — v1 state files auto-migrate to v2
- Existing single-monitor setups work unchanged
- `--all` flag is opt-in for multi-monitor behavior

### Examples

```bash
# Multi-monitor setup
hyprwall set wallpaper.mp4 --all --profile balanced

# Stop all wallpapers
hyprwall stop

# View multi-monitor status
hyprwall status

# All existing commands still work
hyprwall set wallpaper.mp4              # Single monitor (default)
hyprwall set wallpaper.mp4 --monitor HDMI-A-1  # Specific monitor
```

---

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
