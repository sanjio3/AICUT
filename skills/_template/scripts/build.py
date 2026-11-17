# -*- coding: utf-8 -*-
"""TODO 特效说明。

契约（改错任何一条，validate-effect 都会拦下）：
  - 导出 build(shot, params, caps) -> (extra_inputs, filter_chain_lines)
  - 基础链输出标签是 [g]，额外输入编号从 1 开始
  - 最后一行必须输出 [out]
  - 不落盘、不启进程、不读全局配置
  - 路径与画布从 params["_overlays"] / ["_assets"] / ["_geom"] 取
"""
from typing import Any, Dict, List, Tuple


def build(shot: Dict[str, Any], params: Dict[str, Any],
          caps: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    geom = params.get("_geom", {"w": 1280, "h": 720, "fps": 24})
    contrast = float(params.get("contrast", 1.10))

    # TODO 把下面这行换成真正的滤镜链。
    # extra 是 ffmpeg 输入参数列表，例如 ["-i", "/path/to/overlay.mov"]，
    # 对应链里的 [1:v]；不需要额外素材就返回空列表。
    extra: List[str] = []
    lines = [
        "[g]eq=contrast=%.2f,format=yuv420p[out]" % contrast,
    ]
    return extra, lines
