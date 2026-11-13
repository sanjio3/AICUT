# -*- coding: utf-8 -*-
"""素材池：配额轮转 + dHash 感知去重 + 静止画面过滤 + 三级降级。"""
import os
import random

import cv2
import numpy as np

from . import assets

VIDEO_EXT = (".mp4", ".mov", ".mkv", ".avi")


class Pool(object):
    def __init__(self, cfg, scalars, seed=271):
        self.dir = cfg["paths"]["videos"]
        self.quota = int(scalars["quota"])
        self.dhash_th = int(scalars["dhash_th"])
        self.motion_min = float(scalars["motion_min"])
        self.files = []
        if os.path.isdir(self.dir):
            self.files = sorted(f for f in os.listdir(self.dir)
                                if f.lower().endswith(VIDEO_EXT))
        self.cap, self.caps, self.used, self.hash = {}, {}, [], []
        self.dark = {}
        self.count = {f: 0 for f in self.files}
        self.rng = random.Random(seed)
        # prepare 生成的索引带整段亮度采样，直接复用，不必每次重开 23 个视频。
        idx = assets.load_index(cfg).get("videos") or {}
        for f in self.files:
            rec = idx.get(f)
            if rec and rec.get("duration"):
                self.cap[f] = float(rec["duration"])
                self.dark[f] = bool(rec.get("dark_span"))
                continue
            c = cv2.VideoCapture(os.path.join(self.dir, f))
            fps = c.get(cv2.CAP_PROP_FPS) or 24.0
            n = c.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
            c.release()
            self.cap[f] = n / fps if fps else 0.0
            self.dark[f] = False

    def _probe(self, fn, pos):
        """一次读取拿全部判据：整体亮度、中心亮度、运动量、dHash。"""
        c = self.caps.get(fn)
        if c is None:
            c = cv2.VideoCapture(os.path.join(self.dir, fn))
            self.caps[fn] = c
        c.set(cv2.CAP_PROP_POS_MSEC, pos * 1000.0)
        frames = []
        for _ in range(4):
            ok, fr = c.read()
            if not ok:
                break
            frames.append(fr)
        if not frames:
            return (100.0, 100.0, 99.0, None)
        gs = [cv2.cvtColor(cv2.resize(f, (160, 90)), cv2.COLOR_BGR2GRAY)
              for f in frames]
        mean = float(np.mean([g.mean() for g in gs]))
        cen = float(np.mean([g[6:-6, 10:-10].mean() for g in gs]))
        mot = (float(np.mean([np.abs(gs[i].astype(np.int16) - gs[i - 1]).mean()
                              for i in range(1, len(gs))]))
               if len(gs) > 1 else 99.0)
        small = cv2.cvtColor(cv2.resize(frames[0], (9, 8)), cv2.COLOR_BGR2GRAY)
        bits = (small[:, 1:] > small[:, :-1]).flatten()
        h = int("".join("1" if x else "0" for x in bits), 2)
        return (mean, cen, mot, h)

    def _dup(self, h, th):
        return any(bin(h ^ h2).count("1") <= th for h2 in self.hash)

    def _hit(self, fn, pos, need):
        for f2, p2, n2 in self.used:
            if f2 == fn and not (pos + need < p2 - .05 or pos > p2 + n2 + .05):
                return True
        return False

    def take(self, need):
        """严格条件找不到就逐级放宽，不直接抛错。"""
        for relax in (0, 1, 2):
            dth, mot_t = ((self.dhash_th, self.motion_min),
                          (self.dhash_th + 4, self.motion_min * 0.6),
                          (12, 0.0))[relax]
            order = [f for f in sorted(self.files, key=lambda f: self.count[f])
                     if self.count[f] < self.quota]
            # 配额用满后按总时长降序回落，长素材放最后
            order += sorted((f for f in self.files if f not in order),
                            key=lambda f: -self.cap.get(f, 0))
            for fn in order:
                dur = self.cap.get(fn, 0.0)
                if dur < need + .25:
                    continue
                # 整段有黑场的素材在严格轮次里直接跳过，降级轮次才允许，
                # 这是 v30 Pool.has_dark() 的索引版，用来压住 dark_pct。
                if relax == 0 and self.dark.get(fn):
                    continue
                for _ in range(40):
                    pos = self.rng.uniform(0.0, max(0.01, dur - need - .2))
                    if self._hit(fn, pos, need):
                        continue
                    mean, cen, mot, h = self._probe(fn, pos)
                    if mean > 205 or mean < 30 or cen < 26 or mot < mot_t:
                        continue
                    if h is not None and self._dup(h, dth):
                        continue
                    self.used.append((fn, pos, need))
                    self.count[fn] += 1
                    if h is not None:
                        self.hash.append(h)
                    return fn, (round(pos, 4), round(pos + need, 4))
        raise RuntimeError("pool exhausted: no usable source under %s" % self.dir)

    def repeat_ratio(self):
        """同一素材被复用的时长占比，用来量化「看着重复」。"""
        if not self.used:
            return 0.0
        by_file = {}
        for fn, pos, need in self.used:
            by_file[fn] = by_file.get(fn, 0.0) + need
        total = sum(by_file.values())
        return round(max(by_file.values()) / total, 4) if total else 0.0

    def close(self):
        for c in self.caps.values():
            c.release()
