"""Thumbnail generation and caching utilities."""

import hashlib
import subprocess
from pathlib import Path


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