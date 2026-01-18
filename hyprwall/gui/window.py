"""
Main window for hyprwall GTK4 application.
"""

import hashlib
import subprocess
import time
from pathlib import Path

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    gi.require_version('Gdk', '4.0')
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import Gtk, Adw, Gio, Gdk, Pango, GLib, GdkPixbuf
except (ImportError, ValueError) as e:
    raise RuntimeError("GTK4 or libadwaita not available") from e

from hyprwall.core.api import HyprwallCore


# Feature flag: Set to False to use synchronous loading (baseline for debugging layout issues)
LAZY_LIBRARY_LOADING = False


def _thumb_cache_dir() -> Path:
    """Get the thumbnail cache directory"""
    cache_dir = Path.home() / ".cache" / "hyprwall" / "thumbs"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _thumb_key(path: Path, width: int, height: int) -> str:
    """Generate a unique cache key for a thumbnail based on path, mtime, and size"""
    try:
        stat = path.stat()
        data = f"{path}:{stat.st_mtime}:{stat.st_size}:{width}x{height}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    except Exception:
        # Fallback if stat fails
        data = f"{path}:{width}x{height}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


def _ensure_video_thumb(video_path: Path, width: int, height: int) -> Path | None:
    """
    Generate a video thumbnail using ffmpeg if not cached.
    Returns the path to the thumbnail PNG, or None on failure.
    """
    cache_dir = _thumb_cache_dir()
    thumb_key = _thumb_key(video_path, width, height)
    thumb_path = cache_dir / f"{thumb_key}.png"

    # Return cached thumbnail if it exists
    if thumb_path.exists():
        return thumb_path

    # Check if ffmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=2)
    except Exception:
        return None

    # Extract frame at 1 second using ffmpeg
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", "00:00:01",
            "-i", str(video_path),
            "-frames:v", "1",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
            str(thumb_path),
        ]

        subprocess.run(
            cmd,
            capture_output=True,
            timeout=5,
            check=False,
            text=False,
        )

        # Verify thumbnail was created
        if thumb_path.exists() and thumb_path.stat().st_size > 0:
            return thumb_path
        else:
            return None

    except Exception:
        return None


def _make_picture_from_file(file_path: Path, width: int, height: int, cover: bool = True) -> Gtk.Picture | None:
    """
    Create a Gtk.Picture from an image file with proper scaling.
    Returns None on failure.
    """
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(file_path),
            width=width,
            height=height,
            preserve_aspect_ratio=True
        )
        texture = Gdk.Texture.new_for_pixbuf(pixbuf)
        picture = Gtk.Picture.new_for_paintable(texture)

        if cover:
            picture.set_content_fit(Gtk.ContentFit.COVER)
        else:
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)

        picture.set_can_shrink(True)
        return picture
    except Exception:
        return None


class HyprwallWindow(Adw.ApplicationWindow):
    """
    Main window for the hyprwall GTK4 application.
    This window allows users to select wallpapers and control
    the wallpaper playback globally (all monitors).
    It uses GtkBuilder to load the UI from a .ui file if available,
    otherwise it builds the UI programmatically.
    """

    def __init__(self, application, core: HyprwallCore):
        super().__init__(application=application)

        self.core = core

        # Try to load UI from .ui file
        ui_path = Path(__file__).parent / "ui" / "window.ui"
        if ui_path.exists():
            self._load_from_ui(ui_path)
        else:
            self._build_ui_programmatically()

        # Load initial status
        self._refresh_status()

    def _load_from_ui(self, ui_path: Path):
        """Load the UI from a .ui file using GtkBuilder"""
        builder = Gtk.Builder()
        builder.add_from_file(str(ui_path))

        # Get widgets
        self.start_button = builder.get_object("start_button")
        self.stop_button = builder.get_object("stop_button")
        self.monitors_label = builder.get_object("monitors_label")
        self.file_chooser_button = builder.get_object("file_chooser_button")
        self.folder_chooser_button = builder.get_object("folder_chooser_button")
        self.selected_label = builder.get_object("selected_label")

        # Library views
        self.library_container = builder.get_object("library_container")
        self.library_outer_stack = builder.get_object("library_outer_stack")
        self.library_stack = builder.get_object("library_stack")
        self.library_list = builder.get_object("library_list")
        self.library_grid = builder.get_object("library_grid")
        self.library_scroll_list = builder.get_object("library_scroll_list")
        self.library_scroll_grid = builder.get_object("library_scroll_grid")
        self.single_file_preview_box = builder.get_object("single_file_preview_box")
        self.single_file_view_stack = builder.get_object("single_file_view_stack")
        self.single_file_list = builder.get_object("single_file_list")

        # Pagination
        self.pagination_bar = builder.get_object("pagination_bar")
        self.page_prev = builder.get_object("page_prev")
        self.page_next = builder.get_object("page_next")
        self.page_label = builder.get_object("page_label")

        # View mode toggles
        self.view_mode_gallery = builder.get_object("view_mode_gallery")
        self.view_mode_list = builder.get_object("view_mode_list")

        self.status_label = builder.get_object("status_label")
        self.mode_dropdown = builder.get_object("mode_dropdown")
        self.profile_dropdown = builder.get_object("profile_dropdown")
        self.codec_dropdown = builder.get_object("codec_dropdown")
        self.encoder_dropdown = builder.get_object("encoder_dropdown")
        self.auto_power_switch = builder.get_object("auto_power_switch")

        # Library state
        self._library_items = []
        self._library_folder = None

        # Pagination state
        self._all_items = []
        self._page_size = 15
        self._page_index = 0
        self._total_pages = 1

        # Get content
        content = builder.get_object("window_content")
        if content:
            # Create header and toolbar view
            header = Adw.HeaderBar()

            # Menu
            menu_button = Gtk.MenuButton()
            menu_button.set_icon_name("open-menu-symbolic")
            menu = Gio.Menu()

            # Cache section
            cache_menu = Gio.Menu()
            cache_menu.append("Cache Size", "win.cache-size")
            cache_menu.append("Clear Cache", "win.cache-clear")
            cache_menu.append("Reset Default Folder", "win.reset-default-folder")
            menu.append_section("Cache", cache_menu)

            # App actions
            menu.append("Preferences", "app.preferences")
            menu.append("About", "app.about")
            menu.append("Quit", "app.quit")
            menu_button.set_menu_model(menu)
            header.pack_end(menu_button)

            # Toolbar view
            toolbar_view = Adw.ToolbarView()
            toolbar_view.add_top_bar(header)
            toolbar_view.set_content(content)

            self.set_content(toolbar_view)

        # Connect signals
        if self.start_button:
            self.start_button.connect("clicked", self._on_start_clicked)
        if self.stop_button:
            self.stop_button.connect("clicked", self._on_stop_clicked)
        if self.file_chooser_button:
            self.file_chooser_button.connect("clicked", self._on_choose_file)
        if self.folder_chooser_button:
            self.folder_chooser_button.connect("clicked", self._on_choose_folder)
        if self.library_list:
            self.library_list.connect("row-activated", self._on_library_list_activated)
        if self.library_grid:
            self.library_grid.connect("child-activated", self._on_library_grid_activated)

        # View mode toggle
        if self.view_mode_gallery:
            self.view_mode_gallery.connect("toggled", self._on_view_mode_changed)
        if self.view_mode_list:
            self.view_mode_list.connect("toggled", self._on_view_mode_changed)

        # Pagination
        if hasattr(self, 'page_prev') and self.page_prev:
            self.page_prev.connect("clicked", self._on_page_prev)
        if hasattr(self, 'page_next') and self.page_next:
            self.page_next.connect("clicked", self._on_page_next)

        # Update monitors display
        if self.monitors_label:
            self._update_monitors_display()

        # Add window actions for cache management
        cache_size_action = Gio.SimpleAction.new("cache-size", None)
        cache_size_action.connect("activate", self._on_cache_size)
        self.add_action(cache_size_action)

        cache_clear_action = Gio.SimpleAction.new("cache-clear", None)
        cache_clear_action.connect("activate", self._on_cache_clear)
        self.add_action(cache_clear_action)

        # Add action to reset default library folder
        reset_folder_action = Gio.SimpleAction.new("reset-default-folder", None)
        reset_folder_action.connect("activate", self._on_reset_default_folder)
        self.add_action(reset_folder_action)

        self.selected_file = None
        self.set_default_size(800, 600)  # Larger default to accommodate library
        self.set_title("HyprWall")

        # Prevent window from recentering when content changes
        # Set size request to avoid resize jumps
        if self.library_container:
            self.library_container.set_size_request(-1, 300)  # Minimum height for library

        # Auto-load default library directory at startup
        self._auto_load_default_library()

    def _freeze_window_size(self):
        """Freeze window size to prevent repositioning during content changes"""
        width = self.get_width()
        height = self.get_height()

        # Only freeze if we have valid dimensions
        if width > 0 and height > 0:
            self.set_size_request(width, height)

    def _unfreeze_window_size(self):
        """Unfreeze window size to allow normal resizing"""
        self.set_size_request(-1, -1)

    def _build_ui_programmatically(self):
        """Build the UI in Python (fallback if no .ui file)"""
        # Header bar
        header = Adw.HeaderBar()

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu = Gio.Menu()
        menu.append("Preferences", "app.preferences")
        menu.append("About", "app.about")
        menu.append("Quit", "app.quit")
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        # Main content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        # Title
        title = Gtk.Label(label="HyprWall Manager")
        title.add_css_class("title-1")
        content.append(title)

        # Monitors display (read-only)
        monitors_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        monitors_header = Gtk.Label(label="Detected monitors:")
        monitors_header.set_xalign(0)
        monitors_header.add_css_class("dim-label")
        monitors_box.append(monitors_header)

        self.monitors_label = Gtk.Label(label="Loading...")
        self.monitors_label.set_xalign(0)
        self.monitors_label.set_wrap(True)
        self.monitors_label.set_hexpand(True)
        monitors_box.append(self.monitors_label)
        content.append(monitors_box)

        # File chooser
        file_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        file_label = Gtk.Label(label="Wallpaper:")
        file_box.append(file_label)

        self.file_chooser_button = Gtk.Button(label="Choose file...")
        self.file_chooser_button.set_hexpand(True)
        self.file_chooser_button.connect("clicked", self._on_choose_file)
        file_box.append(self.file_chooser_button)

        self.folder_chooser_button = Gtk.Button(label="Choose folder...")
        self.folder_chooser_button.set_hexpand(True)
        self.folder_chooser_button.connect("clicked", self._on_choose_folder)
        file_box.append(self.folder_chooser_button)

        content.append(file_box)

        # Selected file label
        self.selected_label = Gtk.Label(label="Selected: (none)")
        self.selected_label.set_xalign(0)
        self.selected_label.set_wrap(True)
        self.selected_label.add_css_class("dim-label")
        content.append(self.selected_label)

        # Library list (initially hidden)
        self.library_scroll = Gtk.ScrolledWindow()
        self.library_scroll.set_vexpand(True)
        self.library_scroll.set_max_content_height(200)
        self.library_scroll.set_propagate_natural_height(True)
        self.library_scroll.set_visible(False)

        self.library_list = Gtk.ListBox()
        self.library_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.library_list.add_css_class("boxed-list")
        self.library_list.connect("row-activated", self._on_library_list_activated)
        self.library_scroll.set_child(self.library_list)

        content.append(self.library_scroll)

        # Mode, Profile, and Auto-power controls
        controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Mode dropdown
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mode_label = Gtk.Label(label="Mode:")
        mode_label.set_width_chars(12)
        mode_label.set_xalign(0)
        mode_box.append(mode_label)

        mode_list = Gtk.StringList()
        mode_list.append("auto")
        mode_list.append("fit")
        mode_list.append("cover")
        mode_list.append("stretch")
        self.mode_dropdown = Gtk.DropDown(model=mode_list)
        self.mode_dropdown.set_hexpand(True)
        mode_box.append(self.mode_dropdown)
        controls_box.append(mode_box)

        # Profile dropdown
        profile_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        profile_label = Gtk.Label(label="Profile:")
        profile_label.set_width_chars(12)
        profile_label.set_xalign(0)
        profile_box.append(profile_label)

        profile_list = Gtk.StringList()
        profile_list.append("off")
        profile_list.append("eco")
        profile_list.append("balanced")
        profile_list.append("quality")
        self.profile_dropdown = Gtk.DropDown(model=profile_list)
        self.profile_dropdown.set_selected(2)  # Default to "balanced"
        self.profile_dropdown.set_hexpand(True)
        profile_box.append(self.profile_dropdown)
        controls_box.append(profile_box)

        # Auto-power switch
        auto_power_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        auto_power_label = Gtk.Label(label="Auto-power:")
        auto_power_label.set_width_chars(12)
        auto_power_label.set_xalign(0)
        auto_power_box.append(auto_power_label)

        self.auto_power_switch = Gtk.Switch()
        self.auto_power_switch.set_valign(Gtk.Align.CENTER)
        auto_power_box.append(self.auto_power_switch)

        auto_power_hint = Gtk.Label(label="(adaptive profile based on power status)")
        auto_power_hint.set_hexpand(True)
        auto_power_hint.set_xalign(0)
        auto_power_hint.add_css_class("dim-label")
        auto_power_hint.add_css_class("caption")
        auto_power_box.append(auto_power_hint)

        controls_box.append(auto_power_box)
        content.append(controls_box)

        # Control buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.CENTER)

        self.start_button = Gtk.Button(label="Start")
        self.start_button.add_css_class("suggested-action")
        self.start_button.connect("clicked", self._on_start_clicked)
        button_box.append(self.start_button)

        self.stop_button = Gtk.Button(label="Stop")
        self.stop_button.add_css_class("destructive-action")
        self.stop_button.connect("clicked", self._on_stop_clicked)
        button_box.append(self.stop_button)

        content.append(button_box)

        # Status
        self.status_label = Gtk.Label(label="No wallpaper running")
        self.status_label.add_css_class("dim-label")
        content.append(self.status_label)

        # Toolbar view to combine header + content
        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(content)

        self.set_content(toolbar_view)
        self.set_default_size(600, 400)
        self.set_title("HyprWall")

        self.selected_file = None
        self._update_monitors_display()

    def _update_monitors_display(self):
        """Update the read-only monitor display"""
        try:
            monitors = self.core.list_monitors()
            if monitors:
                monitor_info = [f"{m.name} {m.width}x{m.height}" for m in monitors]
                self.monitors_label.set_label(", ".join(monitor_info))
            else:
                self.monitors_label.set_label("No monitors detected (are you on Hyprland?)")
        except Exception as e:
            self.monitors_label.set_label(f"Error detecting monitors: {e}")

    def _on_choose_file(self, button):
        self.present()

        filter_media = Gtk.FileFilter()
        filter_media.set_name("Media files")
        filter_media.add_mime_type("image/*")
        filter_media.add_mime_type("video/*")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_media)

        dialog = Gtk.FileDialog()
        dialog.set_title("Choose Wallpaper")
        dialog.set_filters(filters)
        dialog.set_default_filter(filter_media)
        dialog.set_modal(True)

        try:
            pictures = Path.home() / "Pictures"
            folder_path = pictures if pictures.exists() else Path.home()
            dialog.set_initial_folder(Gio.File.new_for_path(str(folder_path)))
        except Exception:
            pass

        self._file_dialog = dialog
        button.set_sensitive(False)

        try:
            dialog.open(self, None, self._on_file_chosen)
        except Exception as e:
            button.set_sensitive(True)
            self._show_error(f"Failed to open file dialog: {e!r}")

    def _on_file_chosen(self, dialog, result):
        self.file_chooser_button.set_sensitive(True)
        self._file_dialog = None

        try:
            file = dialog.open_finish(result)
            if file:
                self.selected_file = Path(file.get_path())
                self._update_selected_label()

                # Show single file preview mode
                self._show_single_file_preview(self.selected_file)
        except Exception:
            pass

    def _show_single_file_preview(self, file_path: Path):
        """Show preview of a single selected file in both gallery and list views"""
        if not hasattr(self, 'single_file_preview_box') or not self.single_file_preview_box:
            return

        # Clear previous gallery preview
        child = self.single_file_preview_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.single_file_preview_box.remove(child)
            child = next_child

        # Clear previous list
        if hasattr(self, 'single_file_list') and self.single_file_list:
            child = self.single_file_list.get_first_child()
            while child:
                next_child = child.get_next_sibling()
                self.single_file_list.remove(child)
                child = next_child

        # Determine if it's an image or video
        from hyprwall.core import detect
        is_video = detect.is_video(file_path)

        # Create thumbnail
        thumb_width = 320
        thumb_height = 180

        # === GALLERY VIEW ===
        if is_video:
            # Try to generate video thumbnail
            thumb_path = _ensure_video_thumb(file_path, thumb_width, thumb_height)
            if thumb_path:
                thumb = _make_picture_from_file(thumb_path, thumb_width, thumb_height, cover=True)
            else:
                thumb = None

            if not thumb:
                # Fallback: icon
                icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                icon_box.set_valign(Gtk.Align.CENTER)
                icon_box.set_halign(Gtk.Align.CENTER)
                icon_box.set_size_request(thumb_width, thumb_height)

                icon = Gtk.Image.new_from_icon_name("video-x-generic-symbolic")
                icon.set_pixel_size(64)
                icon_box.append(icon)
                self.single_file_preview_box.append(icon_box)
            else:
                thumb.set_size_request(thumb_width, thumb_height)
                thumb.add_css_class("wallpaper-thumb")
                self.single_file_preview_box.append(thumb)
        else:
            # Image thumbnail
            thumb = _make_picture_from_file(file_path, thumb_width, thumb_height, cover=True)
            if thumb:
                thumb.set_size_request(thumb_width, thumb_height)
                thumb.add_css_class("wallpaper-thumb")
                self.single_file_preview_box.append(thumb)
            else:
                # Fallback: icon
                icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                icon_box.set_valign(Gtk.Align.CENTER)
                icon_box.set_halign(Gtk.Align.CENTER)
                icon_box.set_size_request(thumb_width, thumb_height)

                icon = Gtk.Image.new_from_icon_name("image-x-generic-symbolic")
                icon.set_pixel_size(64)
                icon_box.append(icon)
                self.single_file_preview_box.append(icon_box)

        # Filename label (gallery)
        filename_label = Gtk.Label(label=file_path.name)
        filename_label.set_wrap(True)
        filename_label.set_max_width_chars(40)
        filename_label.add_css_class("title-4")
        self.single_file_preview_box.append(filename_label)

        # File type label (gallery)
        type_label = Gtk.Label(label=f"Type: {'Video' if is_video else 'Image'}")
        type_label.add_css_class("dim-label")
        self.single_file_preview_box.append(type_label)

        # === LIST VIEW ===
        if hasattr(self, 'single_file_list') and self.single_file_list:
            # Create list row with file info
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            content.set_margin_top(12)
            content.set_margin_bottom(12)
            content.set_margin_start(12)
            content.set_margin_end(12)

            # Icon
            icon_name = "video-x-generic-symbolic" if is_video else "image-x-generic-symbolic"
            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(32)
            content.append(icon)

            # File info box
            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            info_box.set_hexpand(True)

            # Filename
            name_label = Gtk.Label(label=file_path.name)
            name_label.set_xalign(0)
            name_label.set_wrap(True)
            name_label.add_css_class("heading")
            info_box.append(name_label)

            # Path + type
            details_label = Gtk.Label(label=f"{file_path.parent} • {'Video' if is_video else 'Image'}")
            details_label.set_xalign(0)
            details_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            details_label.add_css_class("dim-label")
            details_label.add_css_class("caption")
            info_box.append(details_label)

            content.append(info_box)

            # Create row
            row = Gtk.ListBoxRow()
            row.set_child(content)
            row.set_activatable(False)
            row.set_selectable(False)
            self.single_file_list.append(row)

        # Hide pagination bar (not relevant for single file)
        if hasattr(self, 'pagination_bar') and self.pagination_bar:
            self.pagination_bar.set_visible(False)

        # Switch to single file view (respects current gallery/list mode)
        if hasattr(self, 'library_outer_stack') and self.library_outer_stack:
            self.library_outer_stack.set_visible_child_name("single_file")

    def _on_choose_folder(self, button):
        """Open folder chooser dialog"""
        self.present()

        dialog = Gtk.FileDialog()
        dialog.set_title("Choose Wallpaper Folder")
        dialog.set_modal(True)

        try:
            pictures = Path.home() / "Pictures"
            folder_path = pictures if pictures.exists() else Path.home()
            dialog.set_initial_folder(Gio.File.new_for_path(str(folder_path)))
        except Exception:
            pass

        self._folder_dialog = dialog
        button.set_sensitive(False)

        try:
            dialog.select_folder(self, None, self._on_folder_chosen)
        except Exception as e:
            button.set_sensitive(True)
            self._show_error(f"Failed to open folder dialog: {e!r}")

    def _on_folder_chosen(self, dialog, result):
        """Handle folder selection and set as default"""
        self.folder_chooser_button.set_sensitive(True)
        self._folder_dialog = None

        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                folder_path = Path(folder.get_path())

                # Save as default library directory (calls core API)
                if not self.core.set_default_library_dir(folder_path):
                    self._show_error(f"Failed to set default folder: {folder_path}")
                    return

                # Clear selected_file (switching to folder mode)
                self.selected_file = None
                self._update_selected_label()

                # Load library from this folder (switches to library view)
                self._load_library(folder_path)
        except Exception as e:
            self._show_error(f"Folder selection error: {e!r}")

    def _load_library(self, folder: Path):
        """Load media library - synchronous or lazy depending on LAZY_LIBRARY_LOADING flag"""
        # Cancel any ongoing scan
        if hasattr(self, '_scan_cancelled'):
            self._scan_cancelled = True

        # Store folder
        self._library_folder = folder
        self._library_items = []

        # KEEP library container visible to avoid layout jump
        if self.library_container:
            self.library_container.set_visible(True)

        # Show loading page (spinner + message)
        if hasattr(self, 'library_outer_stack') and self.library_outer_stack:
            self.library_outer_stack.set_visible_child_name("loading")

        # Update status label
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.set_label("Loading wallpapers...")

        if LAZY_LIBRARY_LOADING:
            # === LAZY MODE (background thread) ===
            # Freeze window size to prevent Wayland recentering
            self._freeze_window_size()

            # Start progressive scan in background
            self._scan_cancelled = False
            import threading
            thread = threading.Thread(
                target=self._scan_library_thread,
                args=(folder,),
                daemon=True
            )
            thread.start()
        else:
            # === SYNCHRONOUS MODE (baseline for debugging) ===
            # Freeze window size to prevent repositioning
            self._freeze_window_size()

            # Load all items synchronously (blocking, but no thread)
            items = self.core.list_library(folder, recursive=True)

            # Store all items for pagination
            self._all_items = items
            self._page_index = 0

            # Calculate total pages
            import math
            self._total_pages = max(1, math.ceil(len(self._all_items) / self._page_size))

            # Render first page
            self._render_current_page()

            # Show content page (gallery/list)
            if hasattr(self, 'library_outer_stack') and self.library_outer_stack:
                self.library_outer_stack.set_visible_child_name("content")

            # Unfreeze window
            self._unfreeze_window_size()

            # Update status
            self._reset_status()

    def _scan_library_thread(self, folder: Path):
        """Background thread for scanning library (calls core API only)"""
        try:
            all_items = []

            # Iterate over batches from core API and accumulate
            for batch in self.core.iter_library(folder, recursive=True, batch_size=50):
                # Check if scan was cancelled
                if self._scan_cancelled:
                    return

                # Accumulate items instead of rendering immediately
                all_items.extend(batch)

            # Signal completion with all items at once
            if not self._scan_cancelled:
                GLib.idle_add(self._on_library_scan_complete_with_items, all_items)

        except Exception as e:
            GLib.idle_add(self._unfreeze_window_size)
            GLib.idle_add(self._show_error, f"Library scan error: {e}")
            GLib.idle_add(self._reset_status)

    def _append_library_batch(self, batch):
        """Append a batch of items to both views (called from idle_add)"""
        # Remove loading placeholder on first batch
        if not self._library_items:
            self._clear_loading_placeholder()

        self._library_items.extend(batch)

        # Append to list view
        for item in batch:
            self._append_to_list_view(item)

        # Append to grid view
        for item in batch:
            self._append_to_grid_view(item)

        return False  # Don't repeat

    def _on_library_scan_complete_with_items(self, items):
        """Called when library scan completes - setup pagination and render first page"""
        # Store all items for pagination
        self._all_items = items
        self._page_index = 0

        # Calculate total pages
        import math
        self._total_pages = max(1, math.ceil(len(self._all_items) / self._page_size))

        # Render first page
        self._render_current_page()

        # Show content page (switch from loading to gallery/list)
        if hasattr(self, 'library_outer_stack') and self.library_outer_stack:
            self.library_outer_stack.set_visible_child_name("content")

        # Unfreeze window size (allow normal resizing)
        self._unfreeze_window_size()

        # Reset status
        self._reset_status()

        return False  # Don't repeat

    def _render_current_page(self):
        """Render only the current page of items (pagination)"""
        # Clear views first
        self._clear_library_views()

        if not self._all_items:
            # Show "no media found" message
            self._show_no_media_message()
            # Hide pagination bar
            if hasattr(self, 'pagination_bar') and self.pagination_bar:
                self.pagination_bar.set_visible(False)
            return

        # Calculate slice for current page
        start_idx = self._page_index * self._page_size
        end_idx = min(start_idx + self._page_size, len(self._all_items))
        page_items = self._all_items[start_idx:end_idx]

        # Store current page items for compatibility
        self._library_items = page_items

        # Render only the current page items
        self._render_list_view(page_items)
        self._render_grid_view(page_items)

        # Update pagination UI
        self._update_pagination_ui()

    def _update_pagination_ui(self):
        """Update pagination bar state (label + button sensitivity)"""
        if not hasattr(self, 'pagination_bar') or not self.pagination_bar:
            return

        # Show pagination bar if more than one page
        if self._total_pages > 1:
            self.pagination_bar.set_visible(True)
        else:
            self.pagination_bar.set_visible(False)
            return

        # Update label
        if hasattr(self, 'page_label') and self.page_label:
            current_page = self._page_index + 1  # 1-based for display
            self.page_label.set_label(f"Page {current_page} / {self._total_pages}")

        # Update button sensitivity
        if hasattr(self, 'page_prev') and self.page_prev:
            self.page_prev.set_sensitive(self._page_index > 0)

        if hasattr(self, 'page_next') and self.page_next:
            self.page_next.set_sensitive(self._page_index < self._total_pages - 1)

    def _on_page_prev(self, button):
        """Navigate to previous page"""
        if self._page_index > 0:
            self._page_index -= 1
            self._render_current_page()

    def _on_page_next(self, button):
        """Navigate to next page"""
        if self._page_index < self._total_pages - 1:
            self._page_index += 1
            self._render_current_page()

    def _reset_status(self):
        """Reset status label to normal state"""
        if self.status_label:
            self._refresh_status()
        return False

    def _on_library_scan_complete(self):
        """Called when library scan completes"""
        # Clear loading placeholder
        self._clear_loading_placeholder()

        # If no items found, show message
        if not self._library_items:
            self._show_no_media_message()

        return False  # Don't repeat

    def _clear_library_views(self):
        """Clear both list and grid views"""
        # Clear list view
        while True:
            row = self.library_list.get_row_at_index(0)
            if row is None:
                break
            self.library_list.remove(row)

        # Clear grid view
        self.library_grid.remove_all()

    def _show_loading_placeholder(self):
        """Show 'Loading...' placeholder in both views"""
        # Clear first to ensure clean state
        self._clear_library_views()

        # List view placeholder
        label = Gtk.Label(label="Loading wallpapers...")
        label.add_css_class("dim-label")
        label.set_margin_top(12)
        label.set_margin_bottom(12)

        row = Gtk.ListBoxRow()
        row.set_child(label)
        row.set_activatable(False)
        row.set_selectable(False)
        row.set_name("loading-placeholder")  # Mark for removal
        self.library_list.append(row)

        # Grid view placeholder - centered to avoid layout distortion
        label_grid = Gtk.Label(label="Loading wallpapers...")
        label_grid.add_css_class("dim-label")
        label_grid.set_halign(Gtk.Align.CENTER)
        label_grid.set_valign(Gtk.Align.CENTER)
        label_grid.set_hexpand(True)
        label_grid.set_vexpand(True)

        child = Gtk.FlowBoxChild()
        child.set_child(label_grid)
        child.set_can_focus(False)
        child.set_name("loading-placeholder")  # Mark for removal
        self.library_grid.append(child)

    def _clear_loading_placeholder(self):
        """Remove loading placeholder from both views"""
        # Clear list view placeholder
        idx = 0
        while True:
            row = self.library_list.get_row_at_index(idx)
            if row is None:
                break
            if row.get_name() == "loading-placeholder":
                self.library_list.remove(row)
                break  # Only one placeholder
            idx += 1

        # Clear grid view placeholder (FlowBox) - GTK4 iteration
        child = self.library_grid.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            if isinstance(child, Gtk.FlowBoxChild) and child.get_name() == "loading-placeholder":
                self.library_grid.remove(child)
                break  # Only one placeholder
            child = next_child

    def _show_no_media_message(self):
        """Show 'no media found' message in both views"""
        # List view
        label = Gtk.Label(label="No media files found")
        label.add_css_class("dim-label")
        row = Gtk.ListBoxRow()
        row.set_child(label)
        row.set_activatable(False)
        row.set_selectable(False)
        self.library_list.append(row)

        # Grid view
        label_grid = Gtk.Label(label="No media files found")
        label_grid.add_css_class("dim-label")
        label_grid.set_margin_top(24)
        label_grid.set_margin_bottom(24)
        child = Gtk.FlowBoxChild()
        child.set_child(label_grid)
        child.set_can_focus(False)
        self.library_grid.append(child)

    def _render_list_view(self, items):
        """Render list view with MediaItem list"""
        # Clear existing items
        while True:
            row = self.library_list.get_row_at_index(0)
            if row is None:
                break
            self.library_list.remove(row)

        if not items:
            # Show "no media found" message
            label = Gtk.Label(label="No media files found")
            label.add_css_class("dim-label")

            row = Gtk.ListBoxRow()
            row.set_child(label)
            row.set_activatable(False)
            row.set_selectable(False)
            self.library_list.append(row)
            return

        # Populate list
        for item in items:
            # Create content box
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            content.set_margin_top(6)
            content.set_margin_bottom(6)
            content.set_margin_start(12)
            content.set_margin_end(12)

            # Icon based on kind
            icon_name = "video-x-generic-symbolic" if item.kind == "video" else "image-x-generic-symbolic"
            icon = Gtk.Image.new_from_icon_name(icon_name)
            content.append(icon)

            # Filename
            label = Gtk.Label(label=item.path.name)
            label.set_xalign(0)
            label.set_hexpand(True)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            content.append(label)

            # Create ListBoxRow and set content
            row = Gtk.ListBoxRow()
            row.set_child(content)

            # Store path as Python attribute (not set_data)
            row.media_path = item.path

            self.library_list.append(row)

    def _render_grid_view(self, items):
        """Render gallery view (FlowBox) with MediaItem list"""
        # Clear existing items
        self.library_grid.remove_all()

        if not items:
            # Show "no media found" message
            label = Gtk.Label(label="No media files found")
            label.add_css_class("dim-label")
            label.set_margin_top(24)
            label.set_margin_bottom(24)

            child = Gtk.FlowBoxChild()
            child.set_child(label)
            child.set_can_focus(False)
            self.library_grid.append(child)
            return

        # Populate gallery
        for item in items:
            card = self._create_gallery_card(item)

            child = Gtk.FlowBoxChild()
            child.set_child(card)

            # Store path as Python attribute
            child.media_path = item.path

            self.library_grid.append(child)

    def _append_to_list_view(self, item):
        """Append a single item to list view (for progressive loading)"""
        # Create content box
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        content.set_margin_top(6)
        content.set_margin_bottom(6)
        content.set_margin_start(12)
        content.set_margin_end(12)

        # Icon based on kind
        icon_name = "video-x-generic-symbolic" if item.kind == "video" else "image-x-generic-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        content.append(icon)

        # Filename
        label = Gtk.Label(label=item.path.name)
        label.set_xalign(0)
        label.set_hexpand(True)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        content.append(label)

        # Create ListBoxRow and set content
        row = Gtk.ListBoxRow()
        row.set_child(content)

        # Store path as Python attribute
        row.media_path = item.path

        self.library_list.append(row)

    def _append_to_grid_view(self, item):
        """Append a single item to grid view (for progressive loading)"""
        card = self._create_gallery_card(item)

        child = Gtk.FlowBoxChild()
        child.set_child(card)

        # Store path as Python attribute
        child.media_path = item.path

        self.library_grid.append(child)

    def _create_gallery_card(self, item):
        """Create a gallery card for a media item with proper thumbnails"""
        # Main card container
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card.add_css_class("wallpaper-card")

        # 16:9 aspect ratio for better preview (Wallpaper Engine style)
        thumb_width = 260
        thumb_height = 146

        # Thumbnail area
        if item.kind == "image":
            # Load image thumbnail using proper GdkPixbuf
            thumb = _make_picture_from_file(item.path, thumb_width, thumb_height, cover=True)

            if thumb:
                thumb.set_size_request(thumb_width, thumb_height)
                thumb.add_css_class("wallpaper-thumb")
                card.append(thumb)
            else:
                # Fallback to icon if image loading fails
                icon_box = self._create_fallback_icon("image-x-generic-symbolic", thumb_width, thumb_height)
                card.append(icon_box)
        else:
            # Video - try to generate/load thumbnail
            thumb_path = _ensure_video_thumb(item.path, thumb_width, thumb_height)

            if thumb_path:
                # Successfully generated/cached thumbnail
                thumb = _make_picture_from_file(thumb_path, thumb_width, thumb_height, cover=True)

                if thumb:
                    thumb.set_size_request(thumb_width, thumb_height)
                    thumb.add_css_class("wallpaper-thumb")
                    card.append(thumb)
                else:
                    # Thumbnail exists but couldn't be loaded
                    icon_box = self._create_fallback_icon("video-x-generic-symbolic", thumb_width, thumb_height)
                    card.append(icon_box)
            else:
                # Fallback to icon if ffmpeg unavailable or extraction failed
                icon_box = self._create_fallback_icon("video-x-generic-symbolic", thumb_width, thumb_height)
                card.append(icon_box)

        # Filename label
        label = Gtk.Label(label=item.path.name)
        label.set_xalign(0.5)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(20)
        label.add_css_class("wallpaper-title")
        card.append(label)

        return card

    def _create_fallback_icon(self, icon_name: str, width: int, height: int) -> Gtk.Box:
        """Create a fallback icon box for when thumbnail generation fails"""
        icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        icon_box.set_valign(Gtk.Align.CENTER)
        icon_box.set_halign(Gtk.Align.CENTER)
        icon_box.set_size_request(width, height)
        icon_box.add_css_class("wallpaper-thumb")

        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(48)
        icon_box.append(icon)

        return icon_box

    def _on_view_mode_changed(self, button):
        """Handle view mode toggle (both folder library and single file)"""
        if not button.get_active():
            return

        if button == self.view_mode_gallery:
            # Switch folder library to gallery
            if hasattr(self, 'library_stack') and self.library_stack:
                self.library_stack.set_visible_child_name("gallery")
            # Switch single file to gallery
            if hasattr(self, 'single_file_view_stack') and self.single_file_view_stack:
                self.single_file_view_stack.set_visible_child_name("gallery")
        elif button == self.view_mode_list:
            # Switch folder library to list
            if hasattr(self, 'library_stack') and self.library_stack:
                self.library_stack.set_visible_child_name("list")
            # Switch single file to list
            if hasattr(self, 'single_file_view_stack') and self.single_file_view_stack:
                self.single_file_view_stack.set_visible_child_name("list")

    def _on_library_list_activated(self, list_box, row):
        """Handle library list item selection"""
        media_path = getattr(row, "media_path", None)
        if media_path:
            self.selected_file = media_path
            self._update_selected_label()

    def _on_library_grid_activated(self, flow_box, child):
        """Handle library grid item selection"""
        media_path = getattr(child, "media_path", None)
        if media_path:
            self.selected_file = media_path
            self._update_selected_label()

    def _update_selected_label(self):
        """Update the selected file label"""
        if self.selected_file:
            self.selected_label.set_label(f"Selected: {self.selected_file.name}")
        else:
            self.selected_label.set_label("Selected: (none)")

    def _on_start_clicked(self, button):
        """Start wallpaper on all monitors (global-only)"""
        if not hasattr(self, 'selected_file') or self.selected_file is None:
            self._show_error("Please choose a file first")
            return

        # Read UI values
        mode_idx = self.mode_dropdown.get_selected()
        modes = ["auto", "fit", "cover", "stretch"]
        mode = modes[mode_idx] if mode_idx < len(modes) else "auto"

        profile_idx = self.profile_dropdown.get_selected()
        profiles = ["off", "eco", "balanced", "quality"]
        profile = profiles[profile_idx] if profile_idx < len(profiles) else "balanced"

        codec_idx = self.codec_dropdown.get_selected()
        codecs = ["h264", "vp9", "av1"]
        codec = codecs[codec_idx] if codec_idx < len(codecs) else "h264"

        encoder_idx = self.encoder_dropdown.get_selected()
        encoders = ["auto", "cpu", "vaapi", "nvenc"]
        encoder = encoders[encoder_idx] if encoder_idx < len(encoders) else "auto"

        auto_power = self.auto_power_switch.get_active()

        # Call core API - all business logic is in core
        try:
            success = self.core.set_wallpaper(
                source=self.selected_file,
                mode=mode,
                profile=profile,
                codec=codec,
                encoder=encoder,
                auto_power=auto_power,
            )

            if success:
                self._refresh_status()
            else:
                self._show_error("Failed to start wallpaper")
        except Exception as e:
            self._show_error(f"Error starting wallpaper: {e}")

    def _on_stop_clicked(self, button):
        """Stop wallpaper on all monitors (global-only)"""
        self.core.stop_wallpaper()
        self._refresh_status()

    def _refresh_status(self):
        """Update the status display with wallpaper state (calls core API only)"""
        # Call core API - no business logic here
        status = self.core.get_status()

        if status.running and status.monitors:
            # Build detailed status text
            lines = ["Status: Running"]

            for name, mon_status in status.monitors.items():
                file_name = Path(mon_status.file).name if mon_status.file else "unknown"
                mode = mon_status.mode or "auto"
                pid = mon_status.pid if mon_status.pid else "N/A"

                lines.append(f"  {name}:")
                lines.append(f"    File: {file_name}")
                lines.append(f"    Mode: {mode}")
                lines.append(f"    PID: {pid}")

            self.status_label.set_label("\n".join(lines))
        else:
            self.status_label.set_label("Status: Stopped")

    def _show_error(self, message: str):
        """Display an error message"""
        dialog = Adw.MessageDialog.new(self, "Error", message)
        dialog.add_response("ok", "OK")
        dialog.present()

    def _on_cache_size(self, action, param):
        """Display cache size statistics (calls core API only)"""
        try:
            # Call core API - no business logic here
            cache_info = self.core.cache_size()

            # Format display message
            message = (
                f"Cache Directory: {cache_info['path']}\n\n"
                f"Files: {cache_info['files']}\n"
                f"Directories: {cache_info['dirs']}\n"
                f"Total Size: {cache_info['size_mb']} MB ({cache_info['size_bytes']} bytes)"
            )

            dialog = Adw.MessageDialog.new(self, "Cache Statistics", message)
            dialog.add_response("ok", "OK")
            dialog.present()
        except Exception as e:
            self._show_error(f"Failed to get cache size: {e}")

    def _on_cache_clear(self, action, param):
        """Clear the optimization cache with confirmation"""
        # First show confirmation dialog
        def on_response(dialog, response):
            if response == "clear":
                self._do_clear_cache()

        dialog = Adw.MessageDialog.new(
            self,
            "Clear Cache?",
            "This will delete all optimized video files. Original files will not be affected."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear Cache")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", on_response)
        dialog.present()

    def _do_clear_cache(self):
        """Actually clear the cache (calls core API only)"""
        try:
            # Call core API - no business logic here
            result = self.core.clear_cache()

            if result.get("success"):
                files = result.get("files_deleted", 0)
                bytes_freed = result.get("bytes_freed", 0)
                mb_freed = round(bytes_freed / (1024 * 1024), 2)

                message = (
                    f"Cache cleared successfully!\n\n"
                    f"Files deleted: {files}\n"
                    f"Space freed: {mb_freed} MB"
                )

                dialog = Adw.MessageDialog.new(self, "Success", message)
                dialog.add_response("ok", "OK")
                dialog.present()
            else:
                error_msg = result.get("error", "Unknown error")
                self._show_error(f"Failed to clear cache: {error_msg}")
        except Exception as e:
            self._show_error(f"Failed to clear cache: {e}")

    def _auto_load_default_library(self):
        """Auto-load the default library directory at startup (calls core API only)"""
        try:
            # Get default library directory from core
            default_dir = self.core.get_default_library_dir()

            # Load library from this directory
            if default_dir and default_dir.exists() and default_dir.is_dir():
                self._load_library(default_dir)
        except Exception as e:
            # Silently fail - user can manually choose folder
            pass

    def _on_reset_default_folder(self, action, param):
        """Reset the default library folder to intelligent fallback"""
        try:
            # Call core API - no business logic here
            success = self.core.reset_default_library_dir()

            if success:
                # Get the new fallback directory
                fallback_dir = self.core.get_default_library_dir()

                message = (
                    f"Default folder reset successfully!\n\n"
                    f"Using fallback: {fallback_dir}"
                )

                dialog = Adw.MessageDialog.new(self, "Success", message)
                dialog.add_response("ok", "OK")
                dialog.present()

                # Reload library from fallback
                if fallback_dir and fallback_dir.exists():
                    self._load_library(fallback_dir)
            else:
                self._show_error("Failed to reset default folder")
        except Exception as e:
            self._show_error(f"Failed to reset default folder: {e}")