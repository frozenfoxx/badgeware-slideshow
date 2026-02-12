"""Badgeware Slideshow - Media viewer for the Tufty 2350."""

import os
import time
from picographics import PicoGraphics, DISPLAY_TUFTY_2350
from jpegdec import JPEG

MEDIA_DIR = "/apps/slideshow/media"
DISPLAY_W = 320
DISPLAY_H = 240
DEBOUNCE_MS = 200
OVERLAY_DURATION_MS = 1500

# Button pins (Tufty 2350)
try:
    from machine import Pin
    btn_a = Pin(7, Pin.IN, Pin.PULL_UP)
    btn_b = Pin(8, Pin.IN, Pin.PULL_UP)
    btn_c = Pin(9, Pin.IN, Pin.PULL_UP)
    btn_up = Pin(22, Pin.IN, Pin.PULL_UP)
    btn_down = Pin(11, Pin.IN, Pin.PULL_UP)
except Exception:
    btn_a = btn_b = btn_c = btn_up = btn_down = None


def is_pressed(btn):
    if btn is None:
        return False
    return btn.value() == 0


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
            if e != ".gitkeep":
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
    playlists = []
    for e in sorted(entries):
        if is_dir(MEDIA_DIR + "/" + e) and not e.startswith("."):
            playlists.append(e)
    return playlists


def get_items(playlist):
    """Return sorted list of media items (filenames or animation dir names) in a playlist."""
    pdir = MEDIA_DIR + "/" + playlist
    entries = sorted(listdir_safe(pdir))
    items = []
    for e in entries:
        if e.startswith(".") or e == "meta.txt":
            continue
        full = pdir + "/" + e
        if is_dir(full):
            # Animation directory (has frame_*.jpg files)
            items.append(e)
        elif e.lower().endswith(".jpg"):
            items.append(e)
    return items


def read_meta(anim_dir):
    """Read meta.txt from an animation directory. Returns (frame_count, delay_ms)."""
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
        # No meta.txt, count frames manually
        frames = [f for f in listdir_safe(anim_dir) if f.startswith("frame_") and f.endswith(".jpg")]
        frame_count = len(frames)
    return frame_count, delay_ms


def draw_overlay(display, playlists, current_idx):
    """Draw playlist name overlay in bottom-left with faded prev/next names."""
    # Colors
    white = display.create_pen(255, 255, 255)
    dim = display.create_pen(120, 120, 120)
    shadow = display.create_pen(0, 0, 0)
    bg = display.create_pen(0, 0, 0)

    n = len(playlists)
    current_name = playlists[current_idx]
    prev_name = playlists[(current_idx - 1) % n] if n > 1 else ""
    next_name = playlists[(current_idx + 1) % n] if n > 1 else ""

    display.set_font("bitmap8")

    # Background box
    box_x = 0
    box_w = 160
    box_h = 48 if n > 1 else 20
    box_y = DISPLAY_H - box_h

    display.set_pen(bg)
    display.rectangle(box_x, box_y, box_w, box_h)

    x = 6
    if n > 1:
        # Previous playlist (dimmed, above current)
        display.set_pen(dim)
        display.text(prev_name, x, box_y + 4, box_w, 1)

        # Current playlist (bright)
        display.set_pen(white)
        display.text("> " + current_name, x, box_y + 18, box_w, 1)

        # Next playlist (dimmed, below current)
        display.set_pen(dim)
        display.text(next_name, x, box_y + 32, box_w, 1)
    else:
        display.set_pen(white)
        display.text(current_name, x, box_y + 4, box_w, 1)


def show_image(display, jpeg, path):
    """Display a JPEG image on screen."""
    try:
        jpeg.open_file(path)
        jpeg.decode(0, 0)
    except Exception as e:
        display.set_pen(display.create_pen(255, 0, 0))
        display.set_font("bitmap8")
        display.text("Error: " + str(e), 10, 110, 300, 1)


def show_no_media(display):
    """Show a message when no media is found."""
    black = display.create_pen(0, 0, 0)
    white = display.create_pen(255, 255, 255)
    display.set_pen(black)
    display.clear()
    display.set_pen(white)
    display.set_font("bitmap8")
    display.text("No media found", 80, 100, 300, 2)
    display.text("Add images to media/", 60, 130, 300, 1)
    display.update()


def main():
    display = PicoGraphics(display=DISPLAY_TUFTY_2350)
    display.set_backlight(1.0)
    jpeg = JPEG(display)

    ensure_playlists()
    playlists = get_playlists()

    if not playlists:
        show_no_media(display)
        while True:
            time.sleep(1)

    playlist_idx = 0
    items = get_items(playlists[playlist_idx])
    item_idx = 0

    # Animation state
    anim_frame = 0
    anim_count = 0
    anim_delay = 100
    paused = False

    # Overlay state
    overlay_until = 0
    show_overlay = True

    # Track what's displayed to avoid unnecessary redraws
    needs_redraw = True
    last_button_time = 0

    def now_ms():
        return time.ticks_ms()

    def debounced():
        nonlocal last_button_time
        t = now_ms()
        if time.ticks_diff(t, last_button_time) < DEBOUNCE_MS:
            return False
        last_button_time = t
        return True

    def current_path():
        if not items:
            return None
        return MEDIA_DIR + "/" + playlists[playlist_idx] + "/" + items[item_idx]

    def is_animation(path):
        return path is not None and is_dir(path)

    def load_item():
        nonlocal anim_frame, anim_count, anim_delay, paused, needs_redraw
        path = current_path()
        anim_frame = 0
        paused = False
        if path and is_animation(path):
            anim_count, anim_delay = read_meta(path)
        else:
            anim_count = 0
            anim_delay = 100
        needs_redraw = True

    def switch_playlist(new_idx):
        nonlocal playlist_idx, items, item_idx, overlay_until, show_overlay
        playlist_idx = new_idx
        items = get_items(playlists[playlist_idx])
        item_idx = 0
        overlay_until = time.ticks_add(now_ms(), OVERLAY_DURATION_MS)
        show_overlay = True
        load_item()

    # Initial load
    load_item()
    overlay_until = time.ticks_add(now_ms(), OVERLAY_DURATION_MS)

    while True:
        t = now_ms()

        # Button handling
        if is_pressed(btn_a) and debounced():
            if items:
                item_idx = (item_idx - 1) % len(items)
                load_item()

        if is_pressed(btn_c) and debounced():
            if items:
                item_idx = (item_idx + 1) % len(items)
                load_item()

        if is_pressed(btn_b) and debounced():
            path = current_path()
            if path and is_animation(path):
                paused = not paused

        if is_pressed(btn_up) and debounced():
            new_idx = (playlist_idx - 1) % len(playlists)
            switch_playlist(new_idx)

        if is_pressed(btn_down) and debounced():
            new_idx = (playlist_idx + 1) % len(playlists)
            switch_playlist(new_idx)

        # Rendering
        path = current_path()

        if path is None:
            show_no_media(display)
            time.sleep_ms(100)
            continue

        if is_animation(path):
            if not paused or needs_redraw:
                frame_path = path + "/frame_{:03d}.jpg".format(anim_frame)
                show_image(display, jpeg, frame_path)

                # Draw overlay if active
                if time.ticks_diff(overlay_until, t) > 0:
                    draw_overlay(display, playlists, playlist_idx)

                display.update()
                needs_redraw = False

                if not paused:
                    anim_frame = (anim_frame + 1) % max(anim_count, 1)
                    time.sleep_ms(anim_delay)
            else:
                # Paused, just check buttons
                time.sleep_ms(50)
        else:
            # Static image
            if needs_redraw:
                show_image(display, jpeg, path)

                # Draw overlay if active
                if time.ticks_diff(overlay_until, t) > 0:
                    draw_overlay(display, playlists, playlist_idx)

                display.update()
                needs_redraw = False

            # Check if overlay needs clearing
            if show_overlay and time.ticks_diff(overlay_until, t) <= 0:
                show_overlay = False
                needs_redraw = True

            time.sleep_ms(50)


main()
