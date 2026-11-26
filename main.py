#!/usr/bin/env python3
"""Bad Apple!! in the terminal - fits any window size, with optional sound.

    python main.py                    # picture (plus sound if badapple.mp3 is here)
    python main.py --audio song.mp3   # play this sound file along with the picture
    python main.py --mute             # picture only
    python main.py --mode block       # sharper: 2 pixels per character
    python main.py --invert           # for light terminal themes
    python main.py --fps 15 --cell-ratio 2.0 --audio-offset 0.2

Run `python convert.py` once first to create frames.npz.
Press Ctrl+C to quit. Resize the window while playing - it adapts.
"""
import argparse
import os
import shutil
import sys
import time

import numpy as np
from PIL import Image

import audio

BOX = getattr(Image, "Resampling", Image).BOX
RAMP = np.array(list(" .:-=+*#%@"))   # dark -> bright
BLOCKS = np.array(list(" ▄▀█"))        # index = (top_pixel_on * 2) + bottom_pixel_on
HERE = os.path.dirname(os.path.abspath(__file__))


def enable_ansi():
    """Make cmd / PowerShell understand ANSI escape codes (Windows 10+)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.GetStdHandle.restype = ctypes.c_void_p
        handle = k32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        if k32.GetConsoleMode(ctypes.c_void_p(handle), ctypes.byref(mode)):
            k32.SetConsoleMode(ctypes.c_void_p(handle), mode.value | 0x0004)  # VT processing
    except Exception:
        os.system("")  # old trick that also flips the switch


def find_audio():
    """Look for badapple.mp3 / .wav / ... in the current folder or next to main.py."""
    for folder in (os.getcwd(), HERE):
        for ext in audio.AUDIO_EXTS:
            path = os.path.join(folder, "badapple" + ext)
            if os.path.isfile(path):
                return path
    return None


def fit(term_cols, term_rows, aspect, cell_ratio):
    """Biggest (cols, rows) that fits the window and keeps the video's shape.

    A character cell is about `cell_ratio` times taller than wide, so the
    picture is cols wide and rows*cell_ratio tall in "square" units.
    """
    max_w = max(1, term_cols - 1)   # keep the last column free (avoids wrap glitches)
    max_h = max(1, term_rows - 1)   # keep the last row free (avoids scrolling)
    rows = max_h
    cols = round(rows * cell_ratio * aspect)
    if cols > max_w:
        cols = max_w
        rows = max(1, round(cols / (cell_ratio * aspect)))
    return max(1, cols), rows


def render(gray, cols, rows, mode, invert, term_cols, term_rows):
    """One grayscale frame (2D uint8) -> one text string, centered."""
    vertical = rows * 2 if mode == "block" else rows
    px = np.asarray(Image.fromarray(gray).resize((cols, vertical), BOX))
    if invert:
        px = 255 - px

    if mode == "block":
        on = px >= 128
        code = on[0::2].astype(np.uint8) * 2 + on[1::2]
        chars = BLOCKS[code]
    else:
        idx = (px.astype(np.uint16) * (len(RAMP) - 1) + 127) // 255
        chars = RAMP[idx]

    # (rows, cols) array of 1-char strings -> one string per row, no Python loop
    lines = chars.view(f"<U{cols}")[:, 0]
    left = " " * max(0, (term_cols - cols) // 2)
    top = "\n" * max(0, (term_rows - rows) // 2)
    return top + "\n".join(left + str(line) for line in lines)


def play(frames, fps, mode, invert, cell_ratio, audio_path=None, offset=0.0):
    n, h, w = frames.shape
    aspect = w / h
    out = sys.stdout

    # Start the sound first, so it is already running when the video clock starts.
    stop_audio = None
    if audio_path:
        try:
            stop_audio, _backend = audio.start(audio_path)
        except audio.AudioError as exc:
            print(f"Audio disabled: {exc}", file=sys.stderr)
            time.sleep(2.5)  # let the person read it before the screen switches

    last_size, last_i = None, -1
    cols = rows = 1
    problem = None
    try:
        out.write("\x1b[?1049h\x1b[?25l\x1b[2J")  # alternate screen, hide cursor, clear
        # offset > 0 delays the picture (use it when the sound is late).
        t0 = time.perf_counter() + offset
        while True:
            elapsed = time.perf_counter() - t0
            i = max(0, int(elapsed * fps))  # clock decides the frame -> never drifts
            if i >= n:
                break
            if i == last_i:                 # already shown, wait for the next one
                time.sleep(max(0.0, (i + 1) / fps - elapsed))
                continue

            size = shutil.get_terminal_size()
            if size != last_size:           # first frame or window resized
                out.write("\x1b[2J")
                last_size = size
                cols, rows = fit(size.columns, size.lines, aspect, cell_ratio)

            out.write("\x1b[H" + render(frames[i], cols, rows, mode, invert,
                                        size.columns, size.lines))
            out.flush()
            last_i = i
    except KeyboardInterrupt:
        pass
    finally:
        if stop_audio:
            problem = stop_audio()
        out.write("\x1b[?25h\x1b[?1049l")   # show cursor, leave alternate screen
        out.flush()
    if problem:
        print(problem, file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="frames.npz", help="file made by convert.py")
    ap.add_argument("--fps", type=float, default=15.0, help="playback speed (default: 15)")
    ap.add_argument("--mode", choices=["ascii", "block"], default="ascii")
    ap.add_argument("--invert", action="store_true", help="swap light and dark")
    ap.add_argument("--cell-ratio", type=float, default=2.0,
                    help="character height / width of your font (default: 2.0)")
    ap.add_argument("--audio", metavar="FILE",
                    help="sound file to play along (default: badapple.mp3/.wav/... if present)")
    ap.add_argument("--mute", action="store_true", help="never play sound")
    ap.add_argument("--audio-offset", type=float, default=0.0, metavar="SEC",
                    help="delay the picture by SEC seconds if the sound is late "
                         "(negative: picture starts earlier). Try 0.2")
    args = ap.parse_args()

    if not os.path.exists(args.data):
        sys.exit(f"{args.data} not found. Run `python convert.py` first.")
    frames = np.load(args.data)["frames"]

    audio_path = None
    if not args.mute:
        if args.audio:
            if not os.path.isfile(args.audio):
                sys.exit(f"Audio file not found: {args.audio}")
            audio_path = args.audio
        else:
            audio_path = find_audio()

    if not (sys.stdout.encoding or "").lower().startswith("utf"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    enable_ansi()
    play(frames, args.fps, args.mode, args.invert, args.cell_ratio,
         audio_path, args.audio_offset)


if __name__ == "__main__":
    main()
