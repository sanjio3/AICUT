# -*- coding: utf-8 -*-
"""ffmpeg capability matrix. The measured result feeds the render cache hash,
so the cache invalidates automatically on a different machine or version."""
import hashlib
import json
import re

from .ff import run

WATCHED = [
    "xfade", "gradients", "tpad", "gblur", "blend", "overlay",
    "rgbashift", "maskedmerge", "alphamerge", "displace", "hstack",
    "vstack", "zoompan", "colorbalance", "geq", "fps", "crop",
]

# Version specific behaviour limits. These cannot be inferred from the
# -filters list, they can only come from actually running the filter.
# Source: item by item verification on the 2018 build used during development.
BEHAVIOR_NOTES = {
    "overlay_format": "the 2018 build has no format option",
    "gblur_sigma": "only accepts a constant sigma, not an expression",
    "rgbashift_c": "no c parameter, only rh/rv/gh/gv/bh/bv/ah/av/edge",
    "blend_screen": "all_mode=screen raises the U/V planes too and tints the "
                     "whole frame purple; use per-plane c0/c1/c2 expressions",
    "zoompan_dup": "zoompan produces duplicate frames; use a scale+crop "
                   "expression for the push instead",
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
    """Hash only the version and the presence of filters. Paths stay out of
    the hash, since moving them should not invalidate anything."""
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
