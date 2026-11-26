"""Cross-platform background audio for the terminal player.

No hard dependencies: start(path) tries whatever sound tools are likely to be
on this machine and returns right away while the sound plays in the background.

    stop, backend = audio.start("badapple.mp3")
    ...
    problem = stop()      # stops the sound; returns a message if it had failed

Backends, tried in this order per platform:
    Windows : mci (built in), ffplay, mpv, vlc, pygame
    macOS   : afplay (built in), ffplay, mpv, vlc, pygame
    Linux   : ffplay, mpv, vlc, mpg123, paplay, aplay, pygame
    (WSL counts as Linux: it needs a Linux player and working sound, see README)
"""
import ctypes
import os
import platform
import shutil
import subprocess
import sys

AUDIO_EXTS = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac")


class AudioError(Exception):
    """No backend could play the file (the message says why and what to do)."""


# --------------------------------------------------------------------------
# Backends. Each takes an absolute path and returns a stop() function, or
# raises AudioError / OSError so the next backend gets a turn.
# --------------------------------------------------------------------------

def _spawn(cmd):
    """Run a command-line player quietly in the background."""
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop():
        code = proc.poll()
        if code is None:                       # still playing: stop it
            proc.terminate()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
            return None
        if code != 0:                          # died on its own with an error
            return (f"The audio player stopped early (exit code {code}). "
                    "Check the file format and that your sound device works.")
        return None

    return stop


def _cli(binary, args, exts=None):
    """Build a backend for a command-line player."""
    def start(path):
        exe = shutil.which(binary)
        if not exe:
            raise AudioError(f"{binary} not found")
        ext = os.path.splitext(path)[1].lower()
        if exts and ext not in exts:
            raise AudioError(f"{binary} cannot play {ext} files")
        return _spawn([exe, *args, path])
    return start


def _mci(path):
    """Windows' built-in media API (winmm). Plays mp3 and wav, nothing to install."""
    if os.name != "nt":
        raise AudioError("MCI only exists on Windows")
    if '"' in path:
        raise AudioError("the file path must not contain a double quote")
    winmm = ctypes.windll.winmm
    alias = "badapple"

    def send(command):
        buf = ctypes.create_unicode_buffer(256)
        err = winmm.mciSendStringW(command, buf, 255, None)
        if err:
            winmm.mciGetErrorStringW(err, buf, 255)
            return buf.value or f"MCI error {err}"
        return None

    problem = send(f'open "{path}" alias {alias}')
    if problem:
        raise AudioError(f"MCI could not open the file ({problem})")
    problem = send(f"play {alias}")          # returns immediately
    if problem:
        send(f"close {alias}")
        raise AudioError(f"MCI could not play the file ({problem})")

    def stop():
        send(f"stop {alias}")
        send(f"close {alias}")
        return None

    return stop


def _pygame(path):
    """Optional fallback: `pip install pygame`. Works everywhere."""
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        import pygame
    except ImportError:
        raise AudioError("pygame is not installed")
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
    except pygame.error as exc:
        raise AudioError(f"pygame could not play the file ({exc})")

    def stop():
        pygame.mixer.music.stop()
        pygame.mixer.quit()
        return None

    return stop


BACKENDS = {
    "mci": _mci,
    "afplay": _cli("afplay", []),
    "ffplay": _cli("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
    "mpv": _cli("mpv", ["--no-video", "--no-terminal"]),
    "vlc": _cli("cvlc", ["--play-and-exit", "--quiet"]),
    "mpg123": _cli("mpg123", ["-q"], {".mp3"}),
    "paplay": _cli("paplay", [], {".wav", ".ogg", ".flac"}),
    "aplay": _cli("aplay", ["-q"], {".wav"}),
    "pygame": _pygame,
}


def _order():
    if sys.platform == "win32":
        return ["mci", "ffplay", "mpv", "vlc", "pygame"]
    if sys.platform == "darwin":
        return ["afplay", "ffplay", "mpv", "vlc", "pygame"]
    return ["ffplay", "mpv", "vlc", "mpg123", "paplay", "aplay", "pygame"]


def _advice():
    if sys.platform == "win32":
        return ("Use a .wav or .mp3 file, or install ffmpeg "
                "(for example: winget install ffmpeg).")
    if sys.platform == "darwin":
        return "afplay should be built in; otherwise: brew install ffmpeg"
    text = "Install a player, for example: sudo apt install ffmpeg"
    if "microsoft" in platform.uname().release.lower():
        text += (" (WSL also needs working sound: Windows 11 with WSLg, "
                 "or run the player from Windows instead)")
    return text


def start(path):
    """Start playing `path` in the background -> (stop_function, backend_name)."""
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise AudioError(f"audio file not found: {path}")
    reasons = []
    for name in _order():
        try:
            return BACKENDS[name](path), name
        except (AudioError, OSError) as exc:
            reasons.append(f"{name}: {exc}")
    raise AudioError("no audio backend worked. " + _advice()
                     + "  [" + "; ".join(reasons) + "]")
