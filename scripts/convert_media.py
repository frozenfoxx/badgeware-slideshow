#!/usr/bin/env python3
"""Convert media files (images, GIFs, videos) into Tufty 2350-ready format.

Outputs 320x240 non-progressive JPEGs, letterboxed to fit. Animated GIFs and
videos are extracted into numbered frame directories with a meta.txt file.

Usage:
    python convert_media.py INPUT [INPUT ...] --playlist NAME [--output DIR]

Examples:
    python convert_media.py photo.png --playlist furry
    python convert_media.py animation.gif --playlist funny
    python convert_media.py clip.mp4 --playlist gaming
    python convert_media.py ./my_images/ --playlist default
"""

import argparse
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
JPEG_QUALITY = 85
SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SUPPORTED_GIFS = {".gif"}
SUPPORTED_VIDEOS = {".mp4", ".avi", ".mov", ".webm", ".mkv"}


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


def save_jpeg(img, path):
    """Save image as non-progressive JPEG."""
    img = img.convert("RGB")
    img.save(path, "JPEG", quality=JPEG_QUALITY, progressive=False)


def convert_static_image(input_path, output_dir):
    """Convert a static image to 320x240 JPEG."""
    img = Image.open(input_path)
    img = letterbox(img, DISPLAY_WIDTH, DISPLAY_HEIGHT)
    stem = Path(input_path).stem
    out_path = os.path.join(output_dir, f"{stem}.jpg")
    # Avoid name collisions
    counter = 1
    while os.path.exists(out_path):
        out_path = os.path.join(output_dir, f"{stem}_{counter}.jpg")
        counter += 1
    save_jpeg(img, out_path)
    print(f"  Converted image: {out_path}")


def convert_gif(input_path, output_dir):
    """Convert an animated GIF to a directory of JPEG frames + meta.txt."""
    img = Image.open(input_path)
    n_frames = getattr(img, "n_frames", 1)

    if n_frames <= 1:
        convert_static_image(input_path, output_dir)
        return

    stem = Path(input_path).stem
    frame_dir = os.path.join(output_dir, stem)
    counter = 1
    while os.path.exists(frame_dir):
        frame_dir = os.path.join(output_dir, f"{stem}_{counter}")
        counter += 1
    os.makedirs(frame_dir)

    # Get frame delay (in ms), default to 100ms
    delay_ms = img.info.get("duration", 100)
    if delay_ms == 0:
        delay_ms = 100

    for i in range(n_frames):
        img.seek(i)
        frame = img.convert("RGB")
        frame = letterbox(frame, DISPLAY_WIDTH, DISPLAY_HEIGHT)
        save_jpeg(frame, os.path.join(frame_dir, f"frame_{i:03d}.jpg"))

    with open(os.path.join(frame_dir, "meta.txt"), "w") as f:
        f.write(f"frame_count={n_frames}\n")
        f.write(f"delay_ms={delay_ms}\n")

    print(f"  Converted GIF ({n_frames} frames): {frame_dir}")


def convert_video(input_path, output_dir):
    """Convert a video to a directory of JPEG frames + meta.txt using ffmpeg."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print(f"  Error: ffmpeg/ffprobe not found. Skipping {input_path}")
        return

    stem = Path(input_path).stem
    frame_dir = os.path.join(output_dir, stem)
    counter = 1
    while os.path.exists(frame_dir):
        frame_dir = os.path.join(output_dir, f"{stem}_{counter}")
        counter += 1
    os.makedirs(frame_dir)

    # Get video FPS
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", str(input_path)],
            capture_output=True, text=True, check=True
        )
        import json
        streams = json.loads(result.stdout)
        fps = 10  # default
        for stream in streams.get("streams", []):
            if stream.get("codec_type") == "video":
                r_fps = stream.get("r_frame_rate", "10/1")
                num, den = r_fps.split("/")
                fps = float(num) / float(den)
                break
    except Exception:
        fps = 10

    # Cap FPS to avoid too many frames on the constrained device
    target_fps = min(fps, 15)
    delay_ms = int(1000 / target_fps)

    # Extract frames with ffmpeg
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            ["ffmpeg", "-i", str(input_path), "-vf",
             f"fps={target_fps},scale={DISPLAY_WIDTH}:{DISPLAY_HEIGHT}:"
             f"force_original_aspect_ratio=decrease,"
             f"pad={DISPLAY_WIDTH}:{DISPLAY_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black",
             "-q:v", "3", os.path.join(tmpdir, "frame_%03d.jpg")],
            capture_output=True, check=True
        )

        frames = sorted(f for f in os.listdir(tmpdir) if f.endswith(".jpg"))
        for i, fname in enumerate(frames):
            shutil.move(
                os.path.join(tmpdir, fname),
                os.path.join(frame_dir, f"frame_{i:03d}.jpg")
            )

    frame_count = len(os.listdir(frame_dir)) - 1  # exclude meta.txt we're about to write
    with open(os.path.join(frame_dir, "meta.txt"), "w") as f:
        f.write(f"frame_count={len([x for x in os.listdir(frame_dir) if x.endswith('.jpg')])}\n")
        f.write(f"delay_ms={delay_ms}\n")

    print(f"  Converted video ({frame_count} frames @ {target_fps}fps): {frame_dir}")


def process_input(input_path, output_dir):
    """Route a single input file to the appropriate converter."""
    ext = Path(input_path).suffix.lower()
    if ext in SUPPORTED_IMAGES:
        convert_static_image(input_path, output_dir)
    elif ext in SUPPORTED_GIFS:
        convert_gif(input_path, output_dir)
    elif ext in SUPPORTED_VIDEOS:
        convert_video(input_path, output_dir)
    else:
        print(f"  Skipping unsupported file: {input_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert media for Badgeware Slideshow (Tufty 2350)"
    )
    parser.add_argument(
        "inputs", nargs="+",
        help="Input file(s) or directory to convert"
    )
    parser.add_argument(
        "--playlist", default="default",
        help="Playlist (category) name (default: 'default')"
    )
    parser.add_argument(
        "--output", default=os.path.join(os.path.dirname(__file__), "..", "app", "media"),
        help="Output media directory (default: app/media)"
    )
    args = parser.parse_args()

    output_dir = os.path.join(os.path.abspath(args.output), args.playlist)
    os.makedirs(output_dir, exist_ok=True)

    print(f"Output playlist: {output_dir}")

    for input_path in args.inputs:
        input_path = os.path.abspath(input_path)
        if os.path.isdir(input_path):
            print(f"Processing directory: {input_path}")
            for fname in sorted(os.listdir(input_path)):
                fpath = os.path.join(input_path, fname)
                if os.path.isfile(fpath):
                    process_input(fpath, output_dir)
        elif os.path.isfile(input_path):
            print(f"Processing file: {input_path}")
            process_input(input_path, output_dir)
        else:
            print(f"Not found: {input_path}")

    print("Done.")


if __name__ == "__main__":
    main()
