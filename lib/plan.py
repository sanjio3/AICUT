# -*- coding: utf-8 -*-
"""Decision layer: parameter merging, the attribution table, and plan.json."""
import io
import os

import yaml

from . import music as musiclib


def _val(v):
    return v.get("default") if isinstance(v, dict) else v


def _flatten(node, prefix=""):
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            key = "%s.%s" % (prefix, k) if prefix else k
            out.update(_flatten(v, key))
    else:
        out[prefix] = node
    return out


def _meta(node, prefix=""):
    out = {}
    if isinstance(node, dict):
        if "default" in node:
            out[prefix] = node
        else:
            for k, v in node.items():
                key = "%s.%s" % (prefix, k) if prefix else k
                out.update(_meta(v, key))
    return out


def _local(cfg, effect_id):
    """Skill-local parameters, empty when absent. A standard skill keeps them
    in references/params.yaml."""
    if not effect_id or effect_id == "base":
        return {}
    path = os.path.join("skills", effect_id, "references", "params.yaml")
    if not os.path.exists(path):
        return {}
    with io.open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def merged(cfg, effect_id=None, overrides=None, all_effects=False):
    """Expand {default:...} into scalars. Precedence: overrides > skill-local >
    global > built-in defaults."""
    scalars = {g: {k: _val(v) for k, v in group.items()}
               for g, group in (cfg.get("effects") or {}).items()}
    if effect_id and effect_id != "base":
        local = _local(cfg, effect_id)
        scalars.setdefault(effect_id, {}).update(
            {k: _val(v) for k, v in local.items()})
    if all_effects and os.path.isdir("skills"):
        for name in sorted(os.listdir("skills")):
            if name.startswith(("_", ".")) or name == effect_id:
                continue
            scalars.setdefault(name, {}).update(
                {k: _val(v) for k, v in _local(cfg, name).items()})
    for path, value in (overrides or {}).items():
        parts = path.split(".")
        cur = scalars
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = value
    return scalars


def param_table(cfg, effect_id=None, overrides=None):
    """Step 3 of the workflow: the tunable parameter table shown to the user
    before rendering."""
    groups = _meta(cfg.get("effects") or {})
    if effect_id and effect_id != "base":
        groups.update(_meta(_local(cfg, effect_id), effect_id))
    scalars = merged(cfg, effect_id, overrides)
    flat = _flatten(scalars)
    rows = []
    for path, meta in sorted(groups.items()):
        rows.append({
            "name": path,
            "current": flat.get(path, meta.get("default")),
            "min": meta.get("min"),
            "max": meta.get("max"),
            "step": meta.get("step"),
            "affects": meta.get("affects", []),
            "note": meta.get("note", ""),
            "locked": bool(meta.get("locked", False)),
        })
    return rows


def attribute(cfg, words):
    """Attribution table: user speech to parameter paths. Returns the matched
    entries."""
    hits = []
    for row in cfg.get("attribution") or []:
        if any(w in words for w in row.get("say", [])):
            hits.append(row)
    return hits


SPEEDS = (1.0, 1.25, 1.5, 1.9)
SEQ = ["base", "fire-transition", "manga-split",
       "base", "fire-transition", "manga-split"]


def build(cfg, grid, pool, overrides=None, duration=None, effects=None):
    pr = cfg["project"]
    fps = int(pr["fps"])
    total_t = float(duration if duration is not None else pr["duration"])
    total = int(total_t * fps)
    m0 = float(pr["m0"])

    # When the user names a few effects, only those are used. Whatever the
    # router matched has to be passed in here, otherwise "the sub-skill was
    # loaded" and "the effect is actually used" are two different things.
    sel = effects
    if sel is None:
        sel = (overrides or {}).get("selection.effects")
    if sel is None:
        sel = (cfg.get("selection") or {}).get("effects")
    if isinstance(sel, str):
        sel = [x.strip() for x in sel.split(",") if x.strip()]
    seq = list(sel) if sel else list(SEQ)
    for name in seq:
        if name != "base" and not os.path.isdir(os.path.join("skills", name)):
            raise RuntimeError("unknown effect: %s" % name)
    rotating = [e for e in seq if e != "ending-dissolve"] or ["base"]
    has_ending = "ending-dissolve" in seq

    scalars = merged(cfg, None, overrides, all_effects=True)
    beats = grid.frames(fps, m0, total_t)
    bounds = sorted(set([0] + beats + [total]))

    shots, ci = [], 0
    idx = 0
    while idx < len(bounds) - 1:
        a = bounds[idx]
        d = musiclib.density(a / float(fps))
        nbeats = 2 if d <= 0.5 else 1
        z = bounds[min(idx + nbeats, len(bounds) - 1)]
        n = z - a
        if n < 2:
            idx += 1
            continue
        cuts = [n] if d < 2.0 else [n // 2, n - n // 2]
        if d == 1.5 and ci % 2 == 0:
            cuts = [n]
        for j, nf in enumerate(cuts):
            if nf < 2:
                continue
            dur = nf / float(fps)
            t = a / float(fps) + sum(cuts[:j]) / float(fps)
            sp = SPEEDS[(ci + j) % len(SPEEDS)]
            src, seg = pool.take(dur * sp)
            tail = min(5.5, total_t * 0.30)
            if has_ending and t >= total_t - tail:
                effect = "ending-dissolve"
            else:
                effect = rotating[ci % len(rotating)]
            params = {}
            params.update(scalars.get("card", {}))
            if effect != "base":
                params.update(scalars.get(effect, {}))
            shots.append({
                "index": len(shots),
                "start": round(t, 4),
                "dur": round(dur, 4),
                "frames": nf,
                "src": src,
                "seg": seg,
                "speed": sp,
                "effect": effect,
                "params": params,
                "beat": a in beats,
            })
            ci += 1
        idx += nbeats

    return {
        "version": 1,
        "project": {"fps": fps, "duration": total_t, "m0": m0,
                    "width": pr["width"], "height": pr["height"]},
        "beat_frames": beats,
        "shots": shots,
        "repeat_ratio": pool.repeat_ratio(),
    }
