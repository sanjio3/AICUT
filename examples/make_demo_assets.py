# -*- coding: utf-8 -*-
"""生成可自由分发的合成测试素材，让别人 clone 之后零素材也能跑通链路。

只用 ffmpeg 自带的 lavfi 测试源，不依赖任何受版权保护的画面。
输出到 AICUT_VIDEOS（默认 ./materials/videos），该目录已被 .gitignore 排除。
"""
import os
import subprocess

FF = os.environ.get("AICUT_FFMPEG", "ffmpeg")
OUT = os.environ.get("AICUT_VIDEOS", "./materials/videos")

# 三个动态源，保证 Pool 的运动量判定不会把它们全过滤掉。
SPECS = [
    ("demo_testsrc2.mp4", "testsrc2=size=640x360:rate=25"),
    ("demo_testsrc2_fast.mp4", "testsrc2=size=640x360:rate=30"),
    ("demo_mandelbrot.mp4", "mandelbrot=size=640x360:rate=25"),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    made = 0
    for name, src in SPECS:
        path = os.path.join(OUT, name)
        cmd = [FF, "-y", "-v", "error", "-f", "lavfi", "-i", src,
               "-t", "8", "-c:v", "libx264", "-pix_fmt", "yuv420p", path]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=120)
            print("wrote  %s" % path)
            made += 1
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                OSError) as exc:
            print("skip   %s -> %s" % (name, type(exc).__name__))
    print("%d/%d clips generated in %s" % (made, len(SPECS), OUT))
    print("no BGM generated: music.load falls back to an equal-tempered grid")
    print("next: python aicut.py prepare")
    print("      python aicut.py plan --run demo --effects base --duration 2")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
