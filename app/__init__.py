"""Badgeware Slideshow - Media viewer for the Tufty 2350."""

import os
import sys
import gc

APP_DIR = "/".join(__file__.replace("\\", "/").split("/")[:-1]) or "."
os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

from badgeware import run

try:
    mode(HIRES)
except Exception:
    pass  # HIRES may not be available on all firmware versions

MEDIA_DIR = "media"
OVERLAY_TICKS = 90  # frames to show overlay (~1.5s at ~60fps)

# State
playlists = []
playlist_idx = 0
items = []
item_idx = 0

# Animation state
anim_frame = 0
anim_count = 0
anim_delay = 6  # ticks between frames
anim_tick = 0
paused = False

# Overlay state
overlay_ticks_left = 0

# Display state
current_img = None


def listdir_safe(path):
    try:
        return os.listdir(path)
    except OSError:
        return []


def is_dir(path):
    try:
        return (os.stat(path)[0] & 0x4000) != 0
    except OSError:
        return False


def ensure_playlists():
    """If media dir has loose files but no subdirectories, move them into 'default'."""
    entries = listdir_safe(MEDIA_DIR)
    has_dirs = False
    loose_files = []
    for e in entries:
        full = MEDIA_DIR + "/" + e
        if is_dir(full):
            if not e.startswith("."):
                has_dirs = True
        else:
            if not e.startswith("."):
                loose_files.append(e)

    if not has_dirs and loose_files:
        default_dir = MEDIA_DIR + "/default"
        try:
            os.mkdir(default_dir)
        except OSError:
            pass
        for f in loose_files:
            os.rename(MEDIA_DIR + "/" + f, default_dir + "/" + f)


def get_playlists():
    """Return sorted list of playlist directory names."""
    entries = listdir_safe(MEDIA_DIR)
    result = []
    for e in sorted(entries):
        if is_dir(MEDIA_DIR + "/" + e) and not e.startswith("."):
            result.append(e)
    return result


def get_items(playlist):
    """Return sorted list of media items (filenames or animation dir names)."""
    pdir = MEDIA_DIR + "/" + playlist
    entries = sorted(listdir_safe(pdir))
    result = []
    for e in entries:
        if e.startswith(".") or e == "meta.txt":
            continue
        full = pdir + "/" + e
        if is_dir(full):
            result.append(e)
        elif e.lower().endswith(".png"):
            result.append(e)
    return result


def read_meta(anim_dir):
    """Read meta.txt from an animation directory. Returns (frame_count, delay_ticks)."""
    frame_count = 0
    delay_ms = 100
    try:
        with open(anim_dir + "/meta.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("frame_count="):
                    frame_count = int(line.split("=")[1])
                elif line.startswith("delay_ms="):
                    delay_ms = int(line.split("=")[1])
    except OSError:
        frames = [f for f in listdir_safe(anim_dir) if f.startswith("frame_") and f.endswith(".png")]
        frame_count = len(frames)
    # Convert delay_ms to approximate ticks (assuming ~60fps → ~16ms per tick)
    delay_ticks = max(delay_ms // 16, 1)
    return frame_count, delay_ticks


def current_path():
    if not items:
        return None
    return MEDIA_DIR + "/" + playlists[playlist_idx] + "/" + items[item_idx]


def is_animation(path):
    return path is not None and is_dir(path)


def load_image(path):
    """Load an image, freeing the previous one first."""
    global current_img
    current_img = None
    gc.collect()
    try:
        current_img = image.load(path)
    except Exception as e:
        current_img = None
        print("Error loading:", path, e)


def load_item():
    """Load the current media item."""
    global anim_frame, anim_count, anim_delay, anim_tick, paused
    path = current_path()
    anim_frame = 0
    anim_tick = 0
    paused = False
    if path and is_animation(path):
        anim_count, anim_delay = read_meta(path)
        frame_path = path + "/frame_{:03d}.png".format(anim_frame)
        load_image(frame_path)
    elif path:
        anim_count = 0
        anim_delay = 6
        load_image(path)


def switch_playlist(new_idx):
    global playlist_idx, items, item_idx, overlay_ticks_left
    playlist_idx = new_idx
    items = get_items(playlists[playlist_idx])
    item_idx = 0
    overlay_ticks_left = OVERLAY_TICKS
    load_item()


def draw_overlay():
    """Draw playlist name overlay in bottom-left with faded prev/next names."""
    n = len(playlists)
    if n == 0:
        return

    current_name = playlists[playlist_idx]
    prev_name = playlists[(playlist_idx - 1) % n] if n > 1 else ""
    next_name = playlists[(playlist_idx + 1) % n] if n > 1 else ""

    # Background box
    box_w = 160
    if n > 1:
        box_h = 48
    else:
        box_h = 20
    box_y = screen.height - box_h

    screen.pen = color.rgb(0, 0, 0, 200)
    screen.rectangle(0, box_y, box_w, box_h)

    x = 6
    if n > 1:
        # Previous playlist (dimmed)
        screen.pen = color.rgb(120, 120, 120)
        screen.text(prev_name, x, box_y + 4)

        # Current playlist (bright, with indicator)
        screen.pen = color.rgb(255, 255, 255)
        screen.text("> " + current_name, x, box_y + 18)

        # Next playlist (dimmed)
        screen.pen = color.rgb(120, 120, 120)
        screen.text(next_name, x, box_y + 32)
    else:
        screen.pen = color.rgb(255, 255, 255)
        screen.text(current_name, x, box_y + 4)


def show_no_media():
    """Show a message when no media is found."""
    screen.pen = color.rgb(0, 0, 0)
    screen.clear()
    screen.pen = color.rgb(255, 255, 255)
    screen.text("No media found", 60, 100)
    screen.text("Add images to media/", 40, 130)


def init():
    global playlists, items

    ensure_playlists()
    playlists = get_playlists()

    if not playlists:
        return

    items = get_items(playlists[playlist_idx])
    if items:
        load_item()
        overlay_ticks_left = OVERLAY_TICKS


def update():
    global item_idx, anim_frame, anim_tick, paused
    global overlay_ticks_left

    if not playlists:
        show_no_media()
        return

    # Button handling
    if io.BUTTON_A in io.pressed:
        if items:
            item_idx = (item_idx - 1) % len(items)
            load_item()

    if io.BUTTON_C in io.pressed:
        if items:
            item_idx = (item_idx + 1) % len(items)
            load_item()

    if io.BUTTON_B in io.pressed:
        path = current_path()
        if path and is_animation(path):
            paused = not paused

    if io.BUTTON_UP in io.pressed:
        new_idx = (playlist_idx - 1) % len(playlists)
        switch_playlist(new_idx)

    if io.BUTTON_DOWN in io.pressed:
        new_idx = (playlist_idx + 1) % len(playlists)
        switch_playlist(new_idx)

    # Animation tick
    path = current_path()
    if path and is_animation(path) and not paused:
        anim_tick += 1
        if anim_tick >= anim_delay:
            anim_tick = 0
            anim_frame = (anim_frame + 1) % max(anim_count, 1)
            frame_path = path + "/frame_{:03d}.png".format(anim_frame)
            load_image(frame_path)

    # Rendering - must draw every frame as the framework clears between updates
    if path is None:
        show_no_media()
        return

    screen.pen = color.rgb(0, 0, 0)
    screen.clear()

    if current_img:
        screen.blit(current_img, vec2(0, 0))

    if overlay_ticks_left > 0:
        draw_overlay()
        overlay_ticks_left -= 1


run(update, init=init)
