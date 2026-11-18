# -*- coding: utf-8 -*-
"""Generate freely redistributable synthetic demo clips.

Nothing here is tied to copyrighted footage: the frames are computed pixel by
pixel. That also means the generator works on any ffmpeg build, including old
ones without the `lavfi` input device.

The clips land in the materials directory, which is excluded from version
control. They exist so that a fresh clone can produce a picture without the
user supplying any media.

Used in two places:
  - `examples/make_demo_assets.py` for a manual run
  - `lib/assets.py` as an automatic fallback when the user has no media yet
"""
import os
import subprocess

import numpy as np

W, H, RATE = 640, 360, 25

# (filename, seconds, style)
# Motion matters: Pool drops clips whose measured motion is too low, so a
# static pattern would be filtered out and never reach the timeline.
SPECS = [
    ("demo_gradient.mp4", 8, "gradient"),
    ("demo_blocks.mp4", 8, "blocks"),
    ("demo_diagonal.mp4", 8, "diagonal"),
]


def ffmpeg_path():
    return os.environ.get("AICUT_FFMPEG", "ffmpeg")


def _frames(style, n):
    """Build n frames of rgb24 data for the given visual style."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # Moving fine detail. Without it the frame-to-frame difference is so
    # small that the QA duplicate-frame detector flags the clip, which would
    # make a fresh clone start with a failing gate.
    stripe = ((xx * 0.5 + yy * 0.35) % 23.0)
    out = np.empty((n, H, W, 3), dtype=np.uint8)
    for i in range(n):
        t = i / float(max(1, n))
        if style == "gradient":
            # Kept in the mid-to-bright range: the demo clips are what a fresh
            # user sees first, and they must not trip the dark-frame gate.
            r = 90.0 + (xx / W) * 150.0
            g = 80.0 + (yy / H) * 150.0
            b = 70.0 + 90.0
        elif style == "blocks":
            r = np.full_like(xx, 110.0)
            g = np.full_like(xx, 105.0)
            b = np.full_like(xx, 125.0)
            # a bright block travelling across the frame
            bx = int((t * 1.4 - 0.2) * W) % (W + 120) - 60
            mask = (np.abs(xx - bx) < 60) & (np.abs(yy - H * 0.5) < 90)
            r = np.where(mask, 240.0, r)
            g = np.where(mask, 205.0, g)
            b = np.where(mask, 90.0, b)
        else:  # diagonal
            band = ((xx + yy + t * 260.0) % 150.0) / 150.0
            r = 95.0 + band * 145.0
            g = 105.0 + (1.0 - band) * 115.0
            b = 125.0 + band * 75.0
        # fine scrolling texture keeps the frame difference above the
        # duplicate-frame threshold
        tex = (stripe + t * 900.0) % 23.0
        bump = np.where(tex < 11.5, 16.0, -16.0)
        out[i, :, :, 0] = np.clip(r + bump, 0, 255)
        out[i, :, :, 1] = np.clip(g + bump, 0, 255)
        out[i, :, :, 2] = np.clip(b + bump, 0, 255)
    return out


def _encode(path, style, seconds, ffmpeg):
    n = int(seconds * RATE)
    cmd = [ffmpeg, "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(RATE), "-i", "pipe:0",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
           "-pix_fmt", "yuv420p", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        p.communicate(_frames(style, n).tobytes(), timeout=300)
    except subprocess.TimeoutExpired:
        p.kill()
        p.communicate()
        raise
    return p.returncode


def generate(out_dir, ffmpeg=None, seconds=8, verbose=True):
    """Create the demo clips in out_dir. Returns the list of files written."""
    ff = ffmpeg or ffmpeg_path()
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for name, dur, style in SPECS:
        path = os.path.join(out_dir, name)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            made.append(path)
            if verbose:
                print("exists %s" % path)
            continue
        try:
            rc = _encode(path, style, dur, ff)
            if rc == 0 and os.path.exists(path):
                made.append(path)
                if verbose:
                    print("wrote  %s" % path)
                continue
            if verbose:
                print("skip   %s -> ffmpeg rc=%s" % (name, rc))
        except (subprocess.TimeoutExpired, OSError) as exc:
            if verbose:
                print("skip   %s -> %s" % (name, type(exc).__name__))
    return made


def ensure(out_dir, ffmpeg=None, verbose=False):
    """Make sure out_dir holds at least one usable clip. Returns (files, made)."""
    existing = []
    if os.path.isdir(out_dir):
        for fn in sorted(os.listdir(out_dir)):
            if fn.lower().endswith((".mp4", ".mov", ".mkv", ".webm")):
                p = os.path.join(out_dir, fn)
                if os.path.getsize(p) > 0:
                    existing.append(p)
    if existing:
        return existing, False
    made = generate(out_dir, ffmpeg=ffmpeg, verbose=verbose)
    return made, bool(made)
