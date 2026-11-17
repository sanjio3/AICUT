# -*- coding: utf-8 -*-
"""纯函数：build(shot, params, caps) -> (extra_inputs, filter_chain_lines)。

约定：基础链输出 [g]，额外输入编号从 1 开始，最后一行必须输出 [out]。
不落盘、不启进程、不读全局配置；路径与画布尺寸由 render.py 注入 _overlays / _geom。
"""
import os

# 仅在 prepare 索引缺失时使用的通用占位名；正常路径由 _assets 自动发现素材，
# 仓库里不写任何具体素材文件名，避免把本机素材命名约定带进开源项目。
FALLBACK_CLIPS = {"fire01": "fire_01.mov", "fire02": "fire_02.mov"}


def build(shot, params, caps):
    geom = params.get("_geom", {"w": 1280, "h": 720, "fps": 24})
    w, h, fps = int(geom["w"]), int(geom["h"]), int(geom["fps"])
    overlays = params.get("_overlays", "materials/overlays")
    # 叠加素材由 prepare 自动发现并写进索引，不再依赖固定文件名。
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
        # 素材缺失时不做假成功：降级为可观测的轻度提亮，QA 的 V 会体现差异
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
