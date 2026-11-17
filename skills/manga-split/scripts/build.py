# -*- coding: utf-8 -*-
"""规则四格分屏。纯函数，不落盘、不启进程。"""
from typing import Any, Dict, List, Tuple


def build(shot: Dict[str, Any], params: Dict[str, Any],
          caps: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    geom = params.get("_geom", {"w": 1280, "h": 720})
    w, h = int(geom["w"]), int(geom["h"])
    cw, ch = w // 2, h // 2
    mono = float(params.get("mono_sat", 0.05))
    color = float(params.get("color_sat", 1.40))
    contrast = float(params.get("contrast", 1.25))

    lines = [
        "[g]split=4[a][b][c][d]",
        # 四格各取略有错位的区域，再画十字分格线；若按原象限裁切后拼回原位，
        # 几何上完全还原，只剩色调差异，肉眼看不出是分屏。
        "[a]crop=%d:%d:0:0,eq=contrast=%.2f:saturation=%.2f[a1]"
        % (cw, ch, contrast, mono),
        "[b]crop=%d:%d:%d:0,eq=contrast=%.2f:saturation=%.2f[b1]"
        % (cw, ch, max(0, cw - 48), contrast, color),
        "[c]crop=%d:%d:%d:%d,eq=contrast=%.2f:saturation=%.2f[c1]"
        % (cw, ch, 48, ch - 48, contrast, color),
        "[d]crop=%d:%d:%d:%d,eq=contrast=%.2f:saturation=%.2f[d1]"
        % (cw, ch, cw, ch, contrast, mono),
        "[a1][b1]hstack[top]",
        "[c1][d1]hstack[bot]",
        "[top][bot]vstack,"
        "drawbox=x=%d:y=0:w=4:h=%d:color=white:t=fill,"
        "drawbox=x=0:y=%d:w=%d:h=4:color=white:t=fill,"
        "format=yuv420p[out]" % (w // 2 - 2, h, h // 2 - 2, w),
    ]
    return [], lines
