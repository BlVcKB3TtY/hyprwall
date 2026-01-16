from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from hyprwall import paths
from hyprwall.detect import IMAGE_EXTS

Codec = Literal["h264", "vp9"]

@dataclass(frozen=True)
class OptimizeProfile:
    name: str
    fps: int
    codec: Codec
    crf: int
    preset: str  # ffmpeg preset for x264, used if codec == "h264"

ECO = OptimizeProfile(name="eco", fps=24, codec="h264", crf=28, preset="veryfast")
BALANCED = OptimizeProfile(name="balanced", fps=30, codec="h264", crf=24, preset="veryfast")
QUALITY = OptimizeProfile(name="quality", fps=30, codec="h264", crf=20, preset="fast")

def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _source_fingerprint(p: Path) -> dict:
    st = p.stat()
    return {
        "path": str(p.resolve()),
        "size": st.st_size,
        "mtime": int(st.st_mtime),
    }

def cache_key(
    source: Path,
    width: int,
    height: int,
    profile: OptimizeProfile,
    mode: str,
) -> str:
    payload = {
        "src": _source_fingerprint(source),
        "w": width,
        "h": height,
        "fps": profile.fps,
        "codec": profile.codec,
        "crf": profile.crf,
        "preset": profile.preset,
        # "mode": mode,
    }
    return _sha256_text(json.dumps(payload, sort_keys=True))

def optimized_path(key: str, codec: Codec) -> Path:
    # One directory per key, easier to debug/clean
    out_dir = paths.OPT_DIR / key
    ext = ".mp4" if codec == "h264" else ".webm"
    return out_dir / f"wallpaper{ext}"

def _ffmpeg_exists() -> bool:
    return shutil.which("ffmpeg") is not None

def _build_vf(width: int, height: int, fps: int) -> str:
    # Cover behavior (fill screen): scale up then crop to exact size
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"fps={fps},"
        f"setsar=1"
    )

def _encode_h264(src: Path, dst: Path, vf: str, crf: int, preset: str) -> None:
    # No audio, yuv420p for compatibility
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-an",
        "-vf", vf,
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        "-pix_fmt", "yuv420p",
        str(dst),
    ]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        raise RuntimeError("Encoding interrupted by user.")

def _encode_vp9(src: Path, dst: Path, vf: str, crf: int) -> None:
    # VP9 often heavier on CPU decode, so keep it optional
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(src),
        "-an",
        "-vf", vf,
        "-c:v", "libvpx-vp9",
        "-crf", str(crf),
        "-b:v", "0",
        str(dst),
    ]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        raise RuntimeError("Encoding interrupted by user.")

def ensure_optimized(
    source: Path,
    width: int,
    height: int,
    profile: OptimizeProfile,
    mode: str,
    verbose: bool = False,
) -> Path:
    """
    Return a path to an optimized file in cache.
    If already present, reuse it.
    """
    if not _ffmpeg_exists():
        raise RuntimeError("ffmpeg not found in PATH. Install it to enable optimization.")

    key = cache_key(source, width, height, profile, mode)
    dst = optimized_path(key, profile.codec)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists() and dst.stat().st_size > 0:
        if verbose :
            print(f"[cache] hit: {dst}")
        return dst

    if verbose:
        print(f"[cache] miss: {dst}")

    vf = _build_vf(width, height, profile.fps)

    # NOTE: if input is a static image, ffmpeg will create a short video unless we loop.
    # For images, we loop the input and limit duration to something reasonable (mpv loops anyway).
    # Just to let you know, in my current hyprland setup I use swww for static wallpapers.
    # It doesn't mean that mpvpaper won't be used for static images, but it's less likely.
    src = source
    if source.suffix.lower() in IMAGE_EXTS:
        # 2 seconds looped still image, mpvpaper loops forever anyway
        tmp_dst = dst.with_name(dst.stem + ".tmp" + dst.suffix)
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(source),
            "-t", "2",
            "-an",
            "-vf", vf,
        ]
        if profile.codec == "h264":
            cmd += ["-c:v", "libx264", "-crf", str(profile.crf), "-preset", profile.preset, "-pix_fmt", "yuv420p"]
        else:
            cmd += ["-c:v", "libvpx-vp9", "-crf", str(profile.crf), "-b:v", "0"]
        cmd += [str(tmp_dst)]
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            raise RuntimeError("Encoding interrupted by user.")

        tmp_dst.replace(dst)
        return dst

    # Video inputs
    tmp = dst.with_name(dst.stem + ".tmp" + dst.suffix)
    try:
        if profile.codec == "h264":
            _encode_h264(src, tmp, vf, profile.crf, profile.preset)
        else:
            _encode_vp9(src, tmp, vf, profile.crf)
        tmp.replace(dst)
        return dst
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass