# -*- coding: utf-8 -*-
"""Generate freely redistributable synthetic demo clips.

Frames are computed pixel by pixel, so nothing here is tied to copyrighted
footage and the generator works on any ffmpeg build, including old ones
without the `lavfi` input device.

Output goes to AICUT_VIDEOS (default ./materials/videos), which is excluded
from version control. `python aicut.py prepare` calls the same code
automatically when the user has no media of their own, so running this script
by hand is optional.

Usage:
  python examples/make_demo_assets.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib import demo_assets  # noqa: E402


def main():
    out = os.environ.get("AICUT_VIDEOS", os.path.join(ROOT, "materials", "videos"))
    ff = demo_assets.ffmpeg_path()
    made = demo_assets.generate(out, ffmpeg=ff, verbose=True)
    print("%d/%d clips ready in %s" % (len(made), len(demo_assets.SPECS), out))
    print("no BGM generated: music.load falls back to an equal-tempered grid")
    print("next: python aicut.py prepare")
    print("      python aicut.py plan --run demo --effects base --duration 2")
    print("      python aicut.py confirm --run demo --hash <hash>")
    print("      python aicut.py render --run demo")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
