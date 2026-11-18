# -*- coding: utf-8 -*-
"""Double weighted blur. A pure function: no disk writes, no processes."""
from typing import Any, Dict, List, Tuple


def build(shot: Dict[str, Any], params: Dict[str, Any],
          caps: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    sigma = float(params.get("gblur_sigma", 8))
    sigma2 = min(20.0, sigma * 1.5)
    gamma = float(params.get("gamma", 0.68))
    mix = float(params.get("mix", 0.28))
    keep = 1.0 - mix

    lines = [
        "[g]split=2[ga][gb]",
        "[ga]gblur=sigma=%.2f,eq=gamma=%.2f:brightness=-0.03:"
        "saturation=0.85,format=yuv420p[gd]" % (sigma, gamma),
        "[gb]gblur=sigma=%.2f,eq=gamma=0.78,format=yuv420p[gb2]" % sigma2,
        "[gd][gb2]blend=all_expr='A*%.3f+B*%.3f',format=yuv420p[out]"
        % (keep, mix),
    ]
    return [], lines
