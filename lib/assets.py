# -*- coding: utf-8 -*-
"""素材自行预处理：一次性扫描视频、发现叠加素材、分析 BGM，全部落盘到 runs/_cache/。

prepare 之后 plan 不再需要 AICUT_MUSIC_JSON，也不必每次重新打开 23 个视频读元数据。
"""
import io
import json
import os

import cv2
import numpy as np

from . import beat

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".avi")
OVERLAY_EXT = (".mov", ".mp4", ".png", ".jpg", ".webm")


def cache_dir(cfg):
    d = os.path.abspath(os.path.normpath(
        os.path.join(cfg["paths"]["runs"], "_cache")))
    os.makedirs(d, exist_ok=True)
    return d


def index_path(cfg):
    return os.path.join(cache_dir(cfg), "assets.json")


def music_path(cfg):
    return os.path.join(cache_dir(cfg), "music.json")


def load_index(cfg):
    p = index_path(cfg)
    if not os.path.exists(p):
        return {}
    try:
        with io.open(p, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (ValueError, IOError):
        return {}


def _probe_video(path, samples=7):
    """一次打开，按 7 个采样点读整段亮度，标记中途黑场。"""
    c = cv2.VideoCapture(path)
    fps = c.get(cv2.CAP_PROP_FPS) or 24.0
    n = c.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    dur = n / fps if fps else 0.0
    if dur <= 0.01:
        c.release()
        return None
    vals = []
    for i in range(samples):
        t = dur * (i + 0.5) / samples
        c.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, fr = c.read()
        if ok:
            vals.append(round(float(np.max(fr, axis=2).mean()), 1))
    c.release()
    return {
        "duration": round(float(dur), 3),
        "fps": round(float(fps), 3),
        "frames": int(n),
        "brightness": vals,
        "dark_span": bool(vals) and min(vals) < 32,
        "mean_v": round(float(np.mean(vals)), 1) if vals else 0.0,
    }


def _videos(cfg):
    d = cfg["paths"]["videos"]
    out = {}
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.lower().endswith(VIDEO_EXT):
            continue
        rec = _probe_video(os.path.join(d, fn))
        if rec:
            out[fn] = rec
    return out


def _overlays(cfg):
    d = cfg["paths"]["overlays"]
    out = {"all": [], "fire": []}
    if not os.path.isdir(d):
        return out
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(OVERLAY_EXT))
    out["all"] = files
    out["fire"] = [f for f in files
                   if ("火焰" in f or "fire" in f.lower() or "burn" in f.lower())]
    return out


def _analyse_bgm(cfg):
    """只分析成片附近的一段音频，再把相对时间平移回 BGM 绝对时间。"""
    bgm = cfg["paths"]["bgm"]
    if not os.path.exists(bgm):
        return {"source": "missing bgm -> equal-tempered fallback"}
    pr = cfg["project"]
    m0 = float(pr["m0"])
    start = max(0.0, m0 - 2.0)
    window = float(pr["duration"]) + float(pr.get("drop_at", 0)) + 6.0
    doc = beat.analyse(bgm, start=start, dur=window,
                       ffmpeg=cfg["paths"]["ffmpeg"])
    for key in ("beats", "downbeats"):
        doc[key] = [round(start + t, 4) for t in doc.get(key, [])]
    for o in doc.get("onsets", []):
        o["t"] = round(start + o["t"], 4)
    for b in doc.get("bands", {}).values():
        b["times"] = [round(start + t, 4) for t in b.get("times", [])]
    for s in doc.get("sections", []):
        s["time"] = round(start + s["time"], 4)
    doc["window"]["start"] = start
    doc["source_note"] = "auto analysed by lib/beat.py, times shifted by window start"
    with io.open(music_path(cfg), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=2))
    return {"source": "lib/beat.py", "bpm": doc["tempo"]["bpm"],
            "beats": len(doc["beats"]), "downbeats": len(doc["downbeats"]),
            "onsets": len(doc["onsets"]), "window": [start, round(start + window, 2)]}


def prepare(cfg):
    d = cache_dir(cfg)
    videos = _videos(cfg)
    overlays = _overlays(cfg)
    music = _analyse_bgm(cfg)
    doc = {
        "version": 1,
        "videos_dir": cfg["paths"]["videos"],
        "overlays_dir": cfg["paths"]["overlays"],
        "videos": videos,
        "overlays": overlays,
        "music": music,
    }
    with io.open(os.path.join(d, "assets.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False, indent=2))
    return doc
