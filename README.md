# badgeware-slideshow

[![syntax](https://github.com/frozenfoxx/badgeware-slideshow/actions/workflows/syntax.yml/badge.svg)](https://github.com/frozenfoxx/badgeware-slideshow/actions/workflows/syntax.yml)

A media slideshow app for the Badgeware series of badges. Browse static images and animations organized into playlists, controlled with the badge's buttons.

## Requirements

### Supported Badges

- [x] [Badgeware Tufty](https://github.com/pimoroni/tufty2350) (Tufty 2350)
- [ ] [Badgeware Badger](https://github.com/pimoroni/badger2350) (Badger 2350) - not supported
- [ ] [Badgeware Blinky](https://github.com/pimoroni/blinky2350) (Blinky 2350) - not supported

### Helper Script Dependencies

To convert media for the badge, you need:

- Python 3.8+
- [Pillow](https://pillow.readthedocs.io/) (for images and GIFs)
- [ffmpeg](https://ffmpeg.org/) (for video conversion, must be on your PATH)

Install Python dependencies:

```bash
pip install -r scripts/requirements.txt
```

## Installation

### 1. Prepare Your Media

Place your source media files (images, GIFs, videos) directly into playlist directories under `app/media/`. Create a directory for each playlist you want:

```
app/media/
├── furry/
│   ├── 001_cute_fox.png
│   ├── 002_dancing_cat.gif
│   └── 003_wolf_howl.mp4
├── gaming/
│   ├── highlight_reel.mp4
│   └── victory_screen.bmp
└── funny/
    └── meme.webp
```

If you want your media to play in a specific order, name your files with a numeric prefix:

```
001_first_image.jpg
002_second_image.png
003_my_animation.gif
```

Then run the conversion script. It will scan every playlist directory, convert all files in-place to badge-ready 320x240 PNGs, and remove the originals:

```bash
pip install -r scripts/requirements.txt
python scripts/convert_media.py
```

Already-converted files (320x240 PNGs) and animation directories are left untouched, so the script is safe to run repeatedly.

To use a custom media directory:

```bash
python scripts/convert_media.py --media-dir /path/to/media
```

### 2. Deploy to Badge

Connect your Tufty 2350 via USB. It will appear as a mass storage device. Copy the contents of the `app/` directory to `/apps/slideshow/` on the badge:

```
Badge root/
└── apps/
    └── slideshow/
        ├── __init__.py
        ├── icon.png
        └── media/
            ├── furry/
            │   ├── photo1.png
            │   └── cool_animation/
            │       ├── meta.txt
            │       ├── frame_000.png
            │       ├── frame_001.png
            │       └── ...
            └── gaming/
                └── ...
```

Safely eject the badge and reboot it. Select "slideshow" from the Badgeware app launcher.

## Usage

### Button Controls

| Button | Action |
|--------|--------|
| **A** | Previous media item (loops around) |
| **B** | Pause / Play (animations only) |
| **C** | Next media item (loops around) |
| **Up** | Previous playlist (loops around) |
| **Down** | Next playlist (loops around) |

### Playlists

Playlists are subdirectories inside the `media/` folder. Each one contains a collection of images and animations. Use **Up** and **Down** to cycle through playlists. When switching, a brief overlay appears in the bottom-left corner showing the current playlist name with the previous and next playlists listed above and below it.

If you place media files directly in `media/` without any subdirectories, the app will automatically create a `default` playlist and move them into it on first launch.

### Supported Media (via conversion script)

| Source Format | Converted To |
|---------------|-------------|
| Static images (.jpg, .png, .bmp, .webp) | Single 320x240 PNG |
| Animated GIFs (.gif) | Directory of PNG frames + meta.txt |
| Videos (.mp4, .avi, .mov, .webm, .mkv) | Directory of PNG frames + meta.txt |

## Contributing

Contributions are welcome. Please open an issue to discuss your idea, then submit a pull request.
