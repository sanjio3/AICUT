# -*- coding: utf-8 -*-
"""ffmpeg 能力矩阵。实测结果进渲染缓存哈希，换机器/换版本时缓存自动失效。"""
import hashlib
import json
import re

from .ff import run

WATCHED = [
    "xfade", "gradients", "tpad", "gblur", "blend", "overlay",
    "rgbashift", "maskedmerge", "alphamerge", "displace", "hstack",
    "vstack", "zoompan", "colorbalance", "geq", "fps", "crop",
]

# 版本相关的行为限制，无法从 -filters 列表推断，只能靠实测记录。
# 来源：v30 在本机 2018 构建上的逐条验证。
BEHAVIOR_NOTES = {
    "overlay_format": "2018 构建无 format 选项",
    "gblur_sigma": "只收常量 sigma，不接受表达式",
    "rgbashift_c": "无 c 参数，只有 rh/rv/gh/gv/bh/bv/ah/av/edge",
    "blend_screen": "all_mode=screen 会连 U/V 抬高造成整幅染紫，须用逐平面 c0/c1/c2 表达式",
    "zoompan_dup": "zoompan 会产生相同帧，推镜改用 scale+crop 表达式",
}


def probe(ffmpeg):
    v = run([ffmpeg, "-hide_banner", "-version"], timeout=60)
    first = v.stdout.decode("utf-8", "ignore").splitlines()
    version = first[0] if first else "unknown"

    p = run([ffmpeg, "-hide_banner", "-filters"], timeout=60)
    txt = (p.stdout.decode("utf-8", "ignore") + "\n" +
           p.stderr.decode("utf-8", "ignore"))
    found = {}
    for name in WATCHED:
        found[name] = bool(re.search(r"\b%s\b" % re.escape(name), txt))

    caps = {
        "ffmpeg": ffmpeg,
        "version": version,
        "filters": found,
        "notes": BEHAVIOR_NOTES,
    }
    caps["hash"] = caps_hash(caps)
    return caps


def caps_hash(caps):
    """只用版本与 filter 有无做哈希，路径不进哈希（换路径不应失效）。"""
    payload = {"version": caps.get("version", ""),
               "filters": caps.get("filters", {})}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def report(caps):
    lines = ["ffmpeg  : %s" % caps["version"],
             "cap hash: %s" % caps["hash"],
             "missing : %s" % (", ".join(k for k, ok in caps["filters"].items()
                                          if not ok) or "none")]
    for k, note in caps["notes"].items():
        lines.append("note    : %s -> %s" % (k, note))
    return "\n".join(lines)
