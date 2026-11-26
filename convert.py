#!/usr/bin/env python3
"""Turn a folder of video frames into ONE compact file (frames.npz).

Usage:
    python convert.py                      # reads ./img/*.png -> frames.npz
    python convert.py --src img --width 240

The frames are stored as grayscale at a fixed "master" size that keeps the
video's own aspect ratio. main.py shrinks them to whatever the terminal needs
at playback time, so you only run this once.
"""
import argparse
import glob
import os
import sys

import numpy as np
from PIL import Image

BOX = getattr(Image, "Resampling", Image).BOX  # clean downscale, no ringing


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="img", help="folder with the PNG frames (default: img)")
    ap.add_argument("--pattern", default="*.png", help="glob pattern (default: *.png)")
    ap.add_argument("--width", type=int, default=192,
                    help="master width in pixels; wider = sharper on big terminals (default: 192)")
    ap.add_argument("--out", default="frames.npz", help="output file (default: frames.npz)")
    args = ap.parse_args()

    # Zero-padded names (output000001.png ...) sort correctly as plain text.
    files = sorted(glob.glob(os.path.join(args.src, args.pattern)))
    if not files:
        sys.exit(f"No frames found: {os.path.join(args.src, args.pattern)}")

    with Image.open(files[0]) as im:
        w0, h0 = im.size
    width = min(args.width, w0)
    height = max(1, round(width * h0 / w0))

    frames = np.empty((len(files), height, width), dtype=np.uint8)
    for k, path in enumerate(files):
        with Image.open(path) as im:
            frames[k] = np.asarray(im.convert("L").resize((width, height), BOX))
        if (k + 1) % 200 == 0 or k + 1 == len(files):
            print(f"\r{k + 1}/{len(files)} frames", end="", flush=True)
    print()

    np.savez_compressed(args.out, frames=frames)
    size_mb = os.path.getsize(args.out) / 1e6
    print(f"Saved {args.out}: {len(files)} frames of {width}x{height} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
