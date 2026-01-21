"""Image loading and manipulation utilities for GTK."""

from pathlib import Path

try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Gdk', '4.0')
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import Gtk, Gdk, GdkPixbuf
except (ImportError, ValueError) as e:
    raise RuntimeError("GTK4 not available") from e


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