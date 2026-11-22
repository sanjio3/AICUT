# -*- coding: utf-8 -*-
"""纯函数：build(shot, params, caps) -> (extra_inputs, filter_chain_lines)。

约定：基础链输出 [g]，最后一行必须输出 [out]。
不落盘、不启进程、不读全局配置；本特效不需要任何额外素材。
"""
from typing import Any, Dict, List, Tuple

# 亮带高度锁死 20px：720p 下为 2.8%，不超过画面高度的 3%。
BAND_H = 20


def build(shot: Dict[str, Any], params: Dict[str, Any],
          caps: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    gap = int(params.get("line_gap", 6))
    alpha = float(params.get("line_alpha", 0.25))
    speed = int(params.get("scan_speed", 300))

    extra: List[str] = []
    lines = [
        "[g]drawgrid=width=iw:height=%d:thickness=2:color=black@%.2f,"
        "drawbox=x=0:y='mod(t*%d,ih-%d)':w=iw:h=%d:color=white@0.14:t=fill,"
        "eq=contrast=1.06:saturation=1.12:brightness=0.01,format=yuv420p[out]"
        % (gap, alpha, speed, BAND_H, BAND_H),
    ]
    return extra, lines
