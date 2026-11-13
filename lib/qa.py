# -*- coding: utf-8 -*-
"""验收层：逐帧代理指标、gate 判定、runs 之间的参数与指标 diff。"""
import io
import json
import os

import cv2
import numpy as np
import yaml


def analyze(path, fps=24, plan=None):
    cap = cv2.VideoCapture(path)
    v, grays = [], []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        f = cv2.resize(fr, (320, 180), interpolation=cv2.INTER_AREA)
        v.append(float(np.max(f, axis=2).mean()))
        grays.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
    cap.release()
    if len(v) < 2:
        raise RuntimeError("no frames decoded from %s" % path)
    v = np.asarray(v, dtype=np.float32)
    diffs = np.asarray([np.abs(grays[i].astype(np.int16) -
                              grays[i - 1].astype(np.int16)).mean()
                        for i in range(1, len(grays))], dtype=np.float32)
    prev = np.concatenate([[99.0], diffs[:-1]])
    cuts = int(((diffs > 20) & (prev <= 20)).sum())
    dur = len(v) / float(fps)
    picks = grays[::max(1, len(grays) // 24)][:24]
    lap = float(np.mean([cv2.Laplacian(g, cv2.CV_64F).var() for g in picks]))
    return {
        "frames": int(len(v)),
        "duration": round(dur, 3),
        "V": round(float(v.mean()), 2),
        "dark_pct": round(float((v < 28).mean() * 100), 2),
        "bright_pct": round(float((v > 225).mean() * 100), 2),
        "dup_pct": round(float((diffs < 0.5).mean() * 100), 2),
        "cut_rate": round(cuts / max(0.01, dur), 2),
        "motion_p50": round(float(np.percentile(diffs, 50)), 2),
        "motion_p90": round(float(np.percentile(diffs, 90)), 2),
        "laplacian_var": round(lap, 1),
        "repeat_ratio": (plan or {}).get("repeat_ratio", 0.0),
    }


def gate(qa, cfg):
    g = cfg.get("gates") or {}
    checks = [
        ("dark_pct_max", "dark_pct", "<="),
        ("bright_pct_max", "bright_pct", "<="),
        ("dup_pct_max", "dup_pct", "<="),
        ("repeat_ratio_max", "repeat_ratio", "<="),
    ]
    failures = []
    for kname, mname, op in checks:
        if kname not in g:
            continue
        limit = float(g[kname])
        value = float(qa.get(mname, 0))
        ok = value <= limit if op == "<=" else value >= limit
        if not ok:
            failures.append("%s=%.2f exceeds %s=%.2f" % (mname, value, kname, limit))
    return {"status": "PASS" if not failures else "WARN",
            "failures": failures}


def _flat(node, prefix=""):
    out = {}
    if isinstance(node, dict):
        for k, val in node.items():
            key = "%s.%s" % (prefix, k) if prefix else k
            out.update(_flat(val, key))
    else:
        out[prefix] = node
    return out


def diff(runs_root, a, b):
    def read(name, fname):
        p = os.path.join(runs_root, name, fname)
        if not os.path.exists(p):
            return {}
        with io.open(p, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    pa = _flat(read(a, "params.yaml").get("overrides") or {})
    pb = _flat(read(b, "params.yaml").get("overrides") or {})
    keys = sorted(set(pa) | set(pb))
    changed = [{"param": k, "a": pa.get(k), "b": pb.get(k)}
               for k in keys if pa.get(k) != pb.get(k)]
    sa = (read(a, "params.yaml").get("selection") or {}).get("effects")
    sb = (read(b, "params.yaml").get("selection") or {}).get("effects")
    if sa != sb:
        changed.append({"param": "selection.effects", "a": sa, "b": sb})

    qa_a, qa_b = read(a, "qa.json"), read(b, "qa.json")
    metrics = ["V", "dark_pct", "bright_pct", "dup_pct", "cut_rate",
               "motion_p50", "motion_p90", "laplacian_var", "repeat_ratio"]
    delta = []
    for m in metrics:
        if m in qa_a and m in qa_b:
            delta.append({"metric": m, "a": qa_a[m], "b": qa_b[m],
                          "delta": round(float(qa_b[m]) - float(qa_a[m]), 2)})
    return {"run_a": a, "run_b": b, "params_changed": changed,
            "metrics": delta,
            "gate_a": (read(a, "gate.json") or {}).get("status"),
            "gate_b": (read(b, "gate.json") or {}).get("status")}
