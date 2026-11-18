# -*- coding: utf-8 -*-
"""TODO describe the effect.

Contract (validate-effect rejects the skill if any of these is wrong):
  - export build(shot, params, caps) -> (extra_inputs, filter_chain_lines)
  - the base chain outputs the label [g], extra inputs are numbered from 1
  - the last line must output [out]
  - no writing to disk, no starting processes, no reading global config
  - paths and canvas size come from params["_overlays"] / ["_assets"] / ["_geom"]
"""
from typing import Any, Dict, List, Tuple


def build(shot: Dict[str, Any], params: Dict[str, Any],
          caps: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    geom = params.get("_geom", {"w": 1280, "h": 720, "fps": 24})
    contrast = float(params.get("contrast", 1.10))

    # TODO replace the line below with the real filter chain.
    # extra is the list of ffmpeg input arguments, for example
    # ["-i", "/path/to/overlay.mov"], which matches [1:v] in the chain.
    # Return an empty list when no extra material is needed.
    extra: List[str] = []
    lines = [
        "[g]eq=contrast=%.2f,format=yuv420p[out]" % contrast,
    ]
    return extra, lines
