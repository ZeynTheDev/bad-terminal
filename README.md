# Bad Apple!! in the Terminal (responsive fork)

> **This is a fork of [Ubuntufanboy/bad-windows](https://github.com/Ubuntufanboy/bad-windows).**
> The original idea and first implementation (turning the Bad Apple!! frames into
> text and playing them in the Windows terminal) are by
> [Ubuntufanboy](https://github.com/Ubuntufanboy). If you enjoy this, please go
> star the original repository too.

Plays *Bad Apple!!* as text art in your terminal, and **fits whatever window size
you have**, even if you resize it while it plays.

## What's different from the original

| Original | This fork |
| --- | --- |
| Fixed 142×36 frame printed as one long line, so the picture only looks right in a window exactly 142 columns wide, and shears and wraps in anything else | Picture is fitted to your current window and re-fitted when you resize it |
| Clears the screen with `cls` on every frame (slow, flickers) | Redraws in place with ANSI cursor movement, one write per frame |
| Fixed `sleep()` between frames, so speed depends on your PC | Playback is clock-based and skips frames if your PC falls behind |
| Frame size ignores the video's shape and the tall shape of text characters | Keeps the video's aspect ratio, corrected for character cell height |
| Frames converted to many small `new*.png` files, text built one character at a time | Frames stored once in a single `frames.npz`, rendered with NumPy |
| ASCII only | ASCII or sharper half-block mode (`--mode block`) |
| No sound | Optional sound on Windows, macOS and Linux (`--audio`), no extra install needed on Windows/macOS |

## Requirements

- Python 3.8+
- `pillow` and `numpy` (`pip install -r requirements.txt`)
- A terminal that understands ANSI escape codes. **Windows Terminal** (the
  default on Windows 11) or any Linux/macOS/WSL terminal works well. The old
  standalone `cmd.exe` window is slow and may render poorly.

## Quick start

Get the code with `git clone` or by downloading the ZIP, open a terminal in the
project folder, then:

**Windows (PowerShell / Windows Terminal)**

```powershell
pip install -r requirements.txt
python convert.py      # one time: builds frames.npz from the PNGs in ./img
python main.py
```

**Linux / WSL / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python convert.py
python main.py
```

Press `Ctrl+C` to quit.

## Options

```
python main.py [--mode ascii|block] [--invert] [--fps N] [--cell-ratio R] [--data FILE]
               [--audio FILE] [--mute] [--audio-offset SEC]
```

| Option | Default | What it does |
| --- | --- | --- |
| `--mode ascii` / `--mode block` | `ascii` | `block` uses `▀ ▄ █` to show two pixels per character, which is much sharper |
| `--invert` | off | Swap light and dark (handy on light terminal themes) |
| `--fps N` | `15` | Playback speed |
| `--cell-ratio R` | `2.0` | Height divided by width of your font's characters. Change it if the picture looks stretched or squashed |
| `--data FILE` | `frames.npz` | Frame file made by `convert.py` |
| `--audio FILE` | auto | Sound file to play along (see [Sound](#sound)) |
| `--mute` | off | Never play sound |
| `--audio-offset SEC` | `0` | Delay the picture by SEC seconds if the sound is late (negative = picture starts earlier) |

`convert.py` has its own options: `--src` (frame folder, default `img`),
`--pattern` (default `*.png`), `--width` (stored width, default `192`; bigger
looks better on very large terminals), and `--out`.

## Sound

The repository includes `badapple.mp3`, which plays automatically next to the
picture on every platform. To use another file (`.mp3`, `.wav`, `.ogg`, `.flac`,
`.m4a` or `.aac`), pass it with `--audio`, or use `--mute` for silence.

```bash
python main.py --audio ~/Music/other-version.mp3
```

The song and the frames belong to their creators (see [Credits](#credits)).
They are included for a non-commercial hobby project only; if you are a rights
holder and want them removed, please open an issue and they will be taken down.

The player tries these in order and uses the first one that works, so you
normally don't have to install anything:

| Platform | Tried in this order |
| --- | --- |
| Windows | built-in Windows media API (mp3, wav), `ffplay`, `mpv`, VLC, `pygame` |
| macOS | built-in `afplay`, `ffplay`, `mpv`, VLC, `pygame` |
| Linux | `ffplay`, `mpv`, VLC, `mpg123`, `paplay`, `aplay`, `pygame` |

On Linux, `sudo apt install ffmpeg` is the easiest way to get a player.
`pip install pygame` is a last-resort fallback that works anywhere. If no
player works, the picture still plays and you get a message saying why.

**Keeping sound and picture together.** Playback is clock-based, so they won't
drift apart. Some players take 100-300 ms to start, though. If the sound
arrives late, delay the picture a little: `--audio-offset 0.2` (adjust until it
feels right). Use `--fps` to match how your frames were extracted.

**WSL:** Windows' built-in audio isn't reachable from inside WSL. Sound there
needs a Linux player *and* working audio (WSLg on Windows 11 usually has it).
If it doesn't work, run the player from Windows PowerShell instead.

## Using your own frames

`convert.py` reads numbered PNG frames (for example `img/output000001.png`). If
you have the video file and `ffmpeg`, you can extract frames yourself:

```bash
mkdir -p img
ffmpeg -i badapple.mp4 -vf fps=15 img/output%06d.png
```

Keep the `fps` here in line with `--fps` when you play. To pull the sound out of
the same video: `ffmpeg -i badapple.mp4 -vn badapple.mp3`.

## Troubleshooting

- **Garbled or flickering picture:** use Windows Terminal instead of the old
  `cmd.exe` window.
- **Picture looks stretched or squashed:** adjust `--cell-ratio` (try `1.8`
  to `2.4`), or change your terminal font.
- **Picture is too small or too big:** make the window bigger or smaller, or
  zoom the font with `Ctrl` + mouse wheel.
- **`frames.npz not found`:** run `python convert.py` first.
- **Playback speed feels wrong:** set `--fps` to match how your frames were
  extracted.
- **No sound / "Audio disabled":** read the message, it lists what was tried.
  Install a player (`sudo apt install ffmpeg`, `brew install ffmpeg`, or
  `winget install ffmpeg`) or use a `.wav`/`.mp3` file.
- **Sound starts after the picture:** try `--audio-offset 0.2` (or more).

## How it works

1. `convert.py` shrinks every frame to grayscale at a fixed master size and
   saves all of them into one compressed `frames.npz`.
2. `main.py` loads that file. For each frame it works out the biggest picture
   that fits the current terminal while keeping the video's shape, resamples
   the frame to that size, and maps brightness to characters.
3. It draws the whole frame with a single write at the top-left of the screen,
   and picks the frame to show from the clock, so the speed stays right.
4. If you gave it a sound file, `audio.py` starts it in the background just
   before the clock starts and stops it when the video ends or you press Ctrl+C.

## Credits

- Original project: [Ubuntufanboy/bad-windows](https://github.com/Ubuntufanboy/bad-windows)
  by [Ubuntufanboy](https://github.com/Ubuntufanboy). This fork keeps the
  original idea and the frame workflow, and rewrites the converter and player.
- *Bad Apple!!* was composed by ZUN (Team Shanghai Alice) for the Touhou Project
  game *Lotus Land Story*. The vocal version "Bad Apple!! feat. nomico" is by
  Alstroemeria Records (arrangement: Masayoshi Minoshima, vocals: nomico,
  lyrics: Haruka), and the shadow-art video is by Anira, from a storyboard by
  Μμ. This repository is not affiliated with any of them. The soundtrack and
  the frames come from their work and are shared here only for a non-commercial
  hobby project; if you are a rights holder and want them removed, please open
  an issue. Please support the original creators, for example through
  Alstroemeria Records' official releases.

## Licensing

The soundtrack and the frames are **not** covered by any license of this
project's code. See [NOTICE.md](NOTICE.md) for who owns what.
