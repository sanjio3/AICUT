# -*- coding: utf-8 -*-
"""Pure function: build(shot, params, caps) -> (extra_inputs, filter_chain_lines).

Contract: the base chain outputs [g], extra inputs are numbered from 1, and
the last line must output [out]. No disk writes, no processes, no global
config. Paths and canvas size are injected by render.py as _overlays / _geom.
"""
import os

# Generic placeholder names, only used when the prepare index is missing.
# The normal path discovers material through _assets, so no concrete media
# filename is written into the repository and no local naming convention
# leaks into the open source project.
FALLBACK_CLIPS = {"fire01": "fire_01.mov", "fire02": "fire_02.mov"}


def build(shot, params, caps):
    geom = params.get("_geom", {"w": 1280, "h": 720, "fps": 24})
    w, h, fps = int(geom["w"]), int(geom["h"]), int(geom["fps"])
    overlays = params.get("_overlays", "materials/overlays")
    # Overlay material is discovered by prepare and written into the
    # index, so a fixed filename is no longer required.
    fire_files = ((params.get("_assets") or {}).get("overlays") or {}).get("fire") or []
    want = params.get("clip", "fire01")
    if fire_files:
        slot = 0 if want == "fire01" else 1
        fname = fire_files[slot % len(fire_files)]
    else:
        fname = FALLBACK_CLIPS.get(want, FALLBACK_CLIPS["fire01"])
    path = os.path.join(overlays, fname)
    trim = float(params.get("trim_start", 0.55))
    dim = float(params.get("base_dim", 0.68))
    gain = float(params.get("flame_gain", 1.95))
    mix = float(params.get("chroma_mix", 0.28))
    dur = max(0.04, float(shot["dur"]))

    if not os.path.exists(path):
        # When the material is missing, do not fake success: degrade to a
        # mild brightening that is visible in the QA V metric.
        return [], ["[g]eq=brightness=0.03:contrast=1.10,format=yuv420p[out]"]

    extra = ["-stream_loop", "-1", "-ss", "%.4f" % trim,
             "-t", "%.4f" % dur, "-i", path]
    lines = [
        "[1:v]fps=%d,scale=%d:%d:flags=lanczos,format=yuv420p[fr]" % (fps, w, h),
        "[g][fr]blend=c0_expr='min(255,A*%.3f+B*%.3f)':"
        "c1_expr='A*%.3f+B*%.3f':c2_expr='A*%.3f+B*%.3f',"
        "format=yuv420p[out]" % (dim, gain, 1 - mix, mix, 1 - mix, mix),
    ]
    return extra, lines
