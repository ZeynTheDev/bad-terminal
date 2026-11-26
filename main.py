#!/usr/bin/env python3
"""Bad Apple!! in the terminal - fits any window size.

    python main.py                 # ASCII, fits the current window
    python main.py --mode block    # sharper: 2 pixels per character
    python main.py --invert        # for light terminal themes
    python main.py --fps 15 --cell-ratio 2.0

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

BOX = getattr(Image, "Resampling", Image).BOX
RAMP = np.array(list(" .:-=+*#%@"))   # dark -> bright
BLOCKS = np.array(list(" ▄▀█"))        # index = (top_pixel_on * 2) + bottom_pixel_on


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


def play(frames, fps, mode, invert, cell_ratio):
    n, h, w = frames.shape
    aspect = w / h
    out = sys.stdout
    out.write("\x1b[?1049h\x1b[?25l\x1b[2J")  # alternate screen, hide cursor, clear
    last_size, last_i = None, -1
    cols = rows = 1
    t0 = time.perf_counter()
    try:
        while True:
            now = time.perf_counter() - t0
            i = int(now * fps)          # clock decides the frame -> never drifts
            if i >= n:
                break
            if i == last_i:             # already shown, wait for the next one
                time.sleep(max(0.0, (i + 1) / fps - now))
                continue

            size = shutil.get_terminal_size()
            if size != last_size:       # first frame or window resized
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
        out.write("\x1b[?25h\x1b[?1049l")  # show cursor, leave alternate screen
        out.flush()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="frames.npz", help="file made by convert.py")
    ap.add_argument("--fps", type=float, default=15.0, help="playback speed (default: 15)")
    ap.add_argument("--mode", choices=["ascii", "block"], default="ascii")
    ap.add_argument("--invert", action="store_true", help="swap light and dark")
    ap.add_argument("--cell-ratio", type=float, default=2.0,
                    help="character height / width of your font (default: 2.0)")
    args = ap.parse_args()

    if not os.path.exists(args.data):
        sys.exit(f"{args.data} not found. Run `python convert.py` first.")
    frames = np.load(args.data)["frames"]

    if not (sys.stdout.encoding or "").lower().startswith("utf"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    enable_ansi()
    play(frames, args.fps, args.mode, args.invert, args.cell_ratio)


if __name__ == "__main__":
    main()
