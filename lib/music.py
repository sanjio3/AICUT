# -*- coding: utf-8 -*-
"""卡点层。优先读已分析好的 music JSON；缺失时用等距网格兜底（精度较低）。"""
import io
import json
import math
import os


class Grid(object):
    def __init__(self, beats, downbeats, bpm, source):
        self.beats = list(beats)
        self.downbeats = list(downbeats)
        self.bpm = float(bpm)
        self.source = source

    def frames(self, fps, m0, dur):
        """窗口内的拍点帧号，浮点秒在这里才换算成帧。"""
        out = []
        end = m0 + dur + 1e-6
        for b in self.beats:
            if m0 - 1e-6 <= b <= end:
                f = int(round((b - m0) * fps))
                if 0 < f < int(dur * fps):
                    out.append(f)
        return sorted(set(out))

    def down_frames(self, fps, m0, dur):
        out = []
        for b in self.downbeats:
            if m0 - 1e-6 <= b <= m0 + dur + 1e-6:
                f = int(round((b - m0) * fps))
                if 0 < f < int(dur * fps):
                    out.append(f)
        return sorted(set(out))

    def beat_error_frames(self, cut_frames, fps):
        """渲后回测：每个切点距最近拍点的帧差。"""
        if not self.beats:
            return []
        m0 = self._m0
        errs = []
        for f in cut_frames:
            t = m0 + f / float(fps)
            errs.append(round(min(abs(t - b) for b in self.beats) * fps, 2))
        return errs

    def bind(self, m0):
        self._m0 = m0
        return self


def load(cfg):
    pr = cfg["project"]
    # prepare 自动分析出的 music.json 优先于人工指定的 AICUT_MUSIC_JSON；
    # 两者都没有时才退到等距网格，保证零预处理也能跑通链路。
    cache = os.path.join(cfg["paths"]["runs"], "_cache", "music.json")
    path = cache if os.path.exists(cache) else cfg["paths"]["music_json"]
    m0 = float(pr["m0"])
    fallback_bpm = float(pr.get("bpm_fallback", 129.2))
    if os.path.exists(path):
        with io.open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        g = Grid(doc.get("beats", []), doc.get("downbeats", []),
                 (doc.get("tempo") or {}).get("bpm", fallback_bpm), path)
        return g.bind(m0)

    bpm = fallback_bpm
    period = 60.0 / bpm
    n = int(math.ceil((float(pr["duration"]) + 2.0) / period)) + 1
    beats = [m0 + i * period for i in range(n)]
    down = [beats[i] for i in range(0, len(beats), 4)]
    g = Grid(beats, down, bpm, "equal-tempered fallback")
    return g.bind(m0)


def density(t):
    """每拍切几刀的曲线，沿用 v30 实测：两拍一刀 → 每拍一刀 → 每拍两刀 → 收尾。"""
    if t < 8.0:
        return 0.5
    if t < 14.0:
        return 1.0
    if t < 20.0:
        return 1.5
    if t < 40.0:
        return 2.0
    return 1.0
