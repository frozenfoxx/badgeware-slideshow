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

Organize your source media (images, GIFs, videos) into folders by playlist. Then use the conversion script to prepare them for the badge's 320x240 display.

```bash
# Convert a folder of images into a playlist called "furry"
python scripts/convert_media.py ./my_furry_pics/ --playlist furry

# Convert a single GIF into the "funny" playlist
python scripts/convert_media.py dancing_cat.gif --playlist funny

# Convert a video clip
python scripts/convert_media.py clip.mp4 --playlist gaming

# Convert files into the default playlist
python scripts/convert_media.py photo.jpg
```

If you want your media to play in a specific order, name your source files with a numeric prefix:

```
001_first_image.jpg
002_second_image.png
003_my_animation.gif
```

Converted media is output to `app/media/<playlist>/`.

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
            │   ├── photo1.jpg
            │   └── cool_animation/
            │       ├── meta.txt
            │       ├── frame_000.jpg
            │       ├── frame_001.jpg
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
| Static images (.jpg, .png, .bmp, .webp) | Single 320x240 JPEG |
| Animated GIFs (.gif) | Directory of JPEG frames + meta.txt |
| Videos (.mp4, .avi, .mov, .webm, .mkv) | Directory of JPEG frames + meta.txt |

## Contributing

Contributions are welcome. Please open an issue to discuss your idea, then submit a pull request.
