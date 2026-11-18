# -*- coding: utf-8 -*-
"""Beat layer. Prefers an analysed music JSON; falls back to an equal-tempered
grid when none is available (lower precision)."""
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
        """Beat frame numbers inside the window; floating point seconds are
        converted to frames only here."""
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
        """Post-render check: frame distance from every cut to the nearest beat."""
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
    # The music.json produced by prepare takes priority over a manually
    # supplied AICUT_MUSIC_JSON. Only when neither exists does the beat grid
    # fall back to an equal-tempered grid, so the pipeline still runs with
    # zero preprocessing.
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
    """How many cuts per beat, following the shape measured in the reference
    cut: two per beat, then one per beat, then two per beat, then a tail."""
    if t < 8.0:
        return 0.5
    if t < 14.0:
        return 1.0
    if t < 20.0:
        return 1.5
    if t < 40.0:
        return 2.0
    return 1.0
