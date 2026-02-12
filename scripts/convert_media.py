#!/usr/bin/env python3
"""Convert media files in-place for the Tufty 2350 badge.

Scans playlist directories under app/media/, converts any non-ready files
(JPEGs, BMPs, WebPs, GIFs, videos) into 320x240 PNGs, and removes the
originals.

Files that are already badge-ready (320x240 PNGs) are left untouched.
Animated GIFs and videos are extracted into numbered frame directories
with a meta.txt file.

Usage:
    python convert_media.py [--media-dir DIR]

Examples:
    # Convert everything under app/media/
    python convert_media.py

    # Specify a custom media directory
    python convert_media.py --media-dir /path/to/media
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

DISPLAY_WIDTH = 320
DISPLAY_HEIGHT = 240
SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SUPPORTED_GIFS = {".gif"}
SUPPORTED_VIDEOS = {".mp4", ".avi", ".mov", ".webm", ".mkv"}
ALL_SUPPORTED = SUPPORTED_IMAGES | SUPPORTED_GIFS | SUPPORTED_VIDEOS


def unique_name(path):
    """Return a unique path by appending _N if it already exists.

    Works for both files and directories.
    """
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"


def letterbox(img, target_w, target_h):
    """Resize image to fit within target dimensions, letterboxing with black."""
    img_w, img_h = img.size
    scale = min(target_w / img_w, target_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
    offset_x = (target_w - new_w) // 2
    offset_y = (target_h - new_h) // 2
    canvas.paste(resized, (offset_x, offset_y))
    return canvas


def save_png(img, path):
    """Save image as PNG."""
    img.convert("RGB").save(path, "PNG")


def is_badge_ready_png(path):
    """Check if a PNG is already 320x240."""
    try:
        with Image.open(path) as img:
            return img.format == "PNG" and img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)
    except Exception:
        return False


def is_converted_anim_dir(path):
    """Check if a directory is an already-converted animation (has meta.txt and frame files)."""
    if not os.path.isdir(path):
        return False
    contents = os.listdir(path)
    has_meta = "meta.txt" in contents
    has_frames = any(f.startswith("frame_") and f.endswith(".png") for f in contents)
    return has_meta and has_frames


def write_meta(frame_dir, frame_count, delay_ms):
    """Write a meta.txt file for an animation directory."""
    with open(os.path.join(frame_dir, "meta.txt"), "w") as f:
        f.write(f"frame_count={frame_count}\n")
        f.write(f"delay_ms={delay_ms}\n")


def get_video_fps(input_path):
    """Get the FPS of a video file using ffprobe. Returns 10 on failure."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", str(input_path)],
            capture_output=True, text=True, check=True
        )
        for stream in json.loads(result.stdout).get("streams", []):
            if stream.get("codec_type") == "video":
                num, den = stream.get("r_frame_rate", "10/1").split("/")
                return float(num) / float(den)
    except Exception:
        pass
    return 10.0


def convert_static_image(input_path):
    """Convert a static image to 320x240 PNG in-place."""
    ext = Path(input_path).suffix.lower()

    if ext == ".png" and is_badge_ready_png(input_path):
        print(f"  Already ready: {input_path}")
        return

    img = letterbox(Image.open(input_path), DISPLAY_WIDTH, DISPLAY_HEIGHT)
    stem = Path(input_path).stem
    parent = str(Path(input_path).parent)
    out_path = os.path.join(parent, f"{stem}.png")

    if ext != ".png":
        out_path = unique_name(out_path)
        save_png(img, out_path)
        os.remove(input_path)
        print(f"  Converted: {input_path} -> {out_path}")
    else:
        save_png(img, input_path)
        print(f"  Re-encoded: {input_path}")


def convert_gif(input_path):
    """Convert an animated GIF to a directory of PNG frames + meta.txt, in-place."""
    img = Image.open(input_path)
    n_frames = getattr(img, "n_frames", 1)

    if n_frames <= 1:
        convert_static_image(input_path)
        return

    stem = Path(input_path).stem
    parent = str(Path(input_path).parent)
    frame_dir = unique_name(os.path.join(parent, stem))
    os.makedirs(frame_dir)

    delay_ms = img.info.get("duration", 100) or 100

    for i in range(n_frames):
        img.seek(i)
        frame = letterbox(img.convert("RGB"), DISPLAY_WIDTH, DISPLAY_HEIGHT)
        save_png(frame, os.path.join(frame_dir, f"frame_{i:03d}.png"))

    write_meta(frame_dir, n_frames, delay_ms)

    img.close()
    os.remove(input_path)
    print(f"  Converted GIF ({n_frames} frames): {input_path} -> {frame_dir}")


def convert_video(input_path):
    """Convert a video to a directory of PNG frames + meta.txt, in-place."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print(f"  Error: ffmpeg/ffprobe not found. Skipping {input_path}")
        return

    stem = Path(input_path).stem
    parent = str(Path(input_path).parent)
    frame_dir = unique_name(os.path.join(parent, stem))
    os.makedirs(frame_dir)

    fps = get_video_fps(input_path)
    target_fps = min(fps, 15)
    delay_ms = int(1000 / target_fps)

    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            ["ffmpeg", "-i", str(input_path), "-vf",
             f"fps={target_fps},scale={DISPLAY_WIDTH}:{DISPLAY_HEIGHT}:"
             f"force_original_aspect_ratio=decrease,"
             f"pad={DISPLAY_WIDTH}:{DISPLAY_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black",
             os.path.join(tmpdir, "frame_%03d.png")],
            capture_output=True, check=True
        )

        frames = sorted(f for f in os.listdir(tmpdir) if f.endswith(".png"))
        for i, fname in enumerate(frames):
            shutil.move(
                os.path.join(tmpdir, fname),
                os.path.join(frame_dir, f"frame_{i:03d}.png")
            )

    frame_count = len([x for x in os.listdir(frame_dir) if x.endswith(".png")])
    write_meta(frame_dir, frame_count, delay_ms)

    os.remove(input_path)
    print(f"  Converted video ({frame_count} frames @ {target_fps}fps): {input_path} -> {frame_dir}")


def process_file(file_path):
    """Route a single file to the appropriate converter."""
    ext = Path(file_path).suffix.lower()
    if ext in SUPPORTED_GIFS:
        convert_gif(file_path)
    elif ext in SUPPORTED_VIDEOS:
        convert_video(file_path)
    elif ext in SUPPORTED_IMAGES:
        convert_static_image(file_path)
    else:
        print(f"  Skipping unsupported file: {file_path}")


def process_playlist(playlist_dir):
    """Process all unconverted files in a playlist directory."""
    print(f"Playlist: {os.path.basename(playlist_dir)}/")

    entries = sorted(os.listdir(playlist_dir))
    found = False

    for entry in entries:
        full_path = os.path.join(playlist_dir, entry)

        if entry.startswith("."):
            continue
        if os.path.isdir(full_path):
            if is_converted_anim_dir(full_path):
                print(f"  Already converted: {full_path}")
            continue

        if Path(entry).suffix.lower() in ALL_SUPPORTED:
            found = True
            process_file(full_path)

    if not found:
        print("  No files to convert.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert media in-place for Badgeware Slideshow (Tufty 2350)"
    )
    parser.add_argument(
        "--media-dir",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "media"),
        help="Path to the media directory (default: app/media)"
    )
    args = parser.parse_args()

    media_dir = os.path.abspath(args.media_dir)
    if not os.path.isdir(media_dir):
        print(f"Error: Media directory not found: {media_dir}")
        sys.exit(1)

    print(f"Media directory: {media_dir}\n")

    playlists = sorted(
        entry for entry in os.listdir(media_dir)
        if os.path.isdir(os.path.join(media_dir, entry)) and not entry.startswith(".")
    )

    if not playlists:
        print("No playlist directories found. Create directories under media/ first.")
        print("Example: media/default/, media/furry/, media/gaming/")
        sys.exit(1)

    for playlist in playlists:
        process_playlist(os.path.join(media_dir, playlist))
        print()

    print("Done.")


if __name__ == "__main__":
    main()
