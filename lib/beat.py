#!/usr/bin/env python3
"""Music structure parser: tempo, per-band onsets, beats, phrase boundaries.

Why this exists: the previous rounds cut on a spectral-flux onset list built from
one mixed band. That cannot tell a kick from a hi-hat, so every cut, every flash
and every background change landed on the same layer of the rhythm — the mix
looked busy but never "on the beat" in the way the reference does. Separating
the bands and the tempo is what makes a layered decision table possible.

Outputs music_structure.json with:
  tempo      bpm, beat period, confidence, beat/downbeat times
  bands      low/mid/high onset times and counts
  energy     0.25s RMS curve plus section boundaries with their jump size
  onsets     merged onset list with the dominant band of each hit
"""
import argparse
import json
import subprocess
import sys

import numpy as np

FFMPEG = None       # 由 prepare 传入 cfg["paths"]["ffmpeg"]，仓库内不硬编码本机路径
SR = 22050
N_FFT = 1024
HOP = 256

BANDS = {
    "low": (30.0, 160.0),     # kick, bass
    "mid": (160.0, 1200.0),   # snare body, vocal
    "high": (1200.0, 7000.0),  # hats, cymbals, sibilance
}


def decode(path, start=None, dur=None, ffmpeg=None):
    ff = ffmpeg or FFMPEG or "ffmpeg"
    cmd = [ff, "-v", "error"]
    if start is not None:
        cmd += ["-ss", "%.3f" % start]
    cmd += ["-i", path]
    if dur is not None:
        cmd += ["-t", "%.3f" % dur]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def stft_mag(x):
    win = np.hanning(N_FFT).astype(np.float32)
    frames = 1 + max(0, (len(x) - N_FFT) // HOP)
    out = np.empty((frames, N_FFT // 2 + 1), dtype=np.float32)
    for i in range(frames):
        seg = x[i * HOP:i * HOP + N_FFT]
        if len(seg) < N_FFT:
            seg = np.pad(seg, (0, N_FFT - len(seg)))
        out[i] = np.abs(np.fft.rfft(seg * win))
    return out


def band_flux(mag, freqs, lo, hi):
    sel = (freqs >= lo) & (freqs < hi)
    band = mag[:, sel]
    # Log compression keeps quiet hats visible next to a loud kick.
    band = np.log1p(band * 10.0)
    diff = np.diff(band, axis=0, prepend=band[:1])
    flux = np.maximum(diff, 0.0).sum(axis=1)
    return flux


def pick_peaks(env, min_gap, delta=1.2):
    """Adaptive-threshold peak picking.

    A fixed multiple of the local median over-detects on dense material: at
    160bpm sixteeth notes are 94ms apart, so any gap small enough to keep them
    also lets the noise floor through. This uses mean + delta*std over a 0.35s
    window and a strict local-max test instead.
    """
    n = len(env)
    if n < 5:
        return []
    win = 15
    pad = np.pad(env, (win, win), mode="edge")
    csum = np.concatenate([[0.0], np.cumsum(pad)])
    csum2 = np.concatenate([[0.0], np.cumsum(pad ** 2)])
    peaks = []
    for i in range(1, n - 1):
        lo, hi = i, i + 2 * win
        s = csum[hi] - csum[lo]
        s2 = csum2[hi] - csum2[lo]
        m = s / (2 * win)
        var = max(0.0, s2 / (2 * win) - m * m)
        thr = m + delta * np.sqrt(var)
        if env[i] > thr and env[i] >= env[i - 1] and env[i] > env[i + 1]:
            # Strict local max over +-2 frames so a single hit yields one peak.
            if env[i] >= env[max(0, i - 2):i + 3].max():
                peaks.append(i)
    out = []
    for p in peaks:
        if out and (p - out[-1]) < min_gap:
            if env[p] > env[out[-1]]:
                out[-1] = p
        else:
            out.append(p)
    return out


def estimate_tempo(env, frame_rate, lo_bpm=60.0, hi_bpm=200.0):
    """Autocorrelation tempo. Returns bpm, lag in frames, confidence 0..1."""
    e = env - env.mean()
    if not np.any(e):
        return None, None, 0.0
    ac = np.correlate(e, e, mode="full")[len(e) - 1:]
    ac = ac / (ac[0] + 1e-9)
    lo_lag = int(frame_rate * 60.0 / hi_bpm)
    hi_lag = int(frame_rate * 60.0 / lo_bpm)
    hi_lag = min(hi_lag, len(ac) - 2)
    if hi_lag <= lo_lag:
        return None, None, 0.0
    seg = ac[lo_lag:hi_lag + 1]
    lag = lo_lag + int(np.argmax(seg))
    bpm = 60.0 * frame_rate / lag
    return round(bpm, 2), lag, round(float(ac[lag]), 3)


def grid_phase_score(onset_times, period, tol=0.06):
    """Best phase plus the share of onsets landing within tol of that grid."""
    if not onset_times or not period or period <= 0:
        return 0.0, 0.0
    best_phase, best_hits = 0.0, -1
    steps = 24
    for k in range(steps):
        ph = period * k / steps
        hits = 0
        for t in onset_times:
            r = (t - ph) % period
            if min(r, period - r) <= tol:
                hits += 1
        if hits > best_hits:
            best_hits, best_phase = hits, ph
    return best_phase, best_hits / float(len(onset_times))


def refine_tempo(ac_bpm, low_times, all_times):
    """Cross-check the autocorrelation tempo against the kick interval.

    Autocorrelation happily locks onto half or double the real pulse, so the
    candidates are scored by how many onsets actually land on the grid they
    imply. The winner is reported together with the runner-up.
    """
    cands = []
    io = [b - a for a, b in zip(low_times, low_times[1:]) if 0.05 < b - a < 1.2]
    io_med = float(np.median(io)) if io else None
    if ac_bpm:
        cands.append((ac_bpm, "autocorrelation"))
    if io_med:
        for mult, tag in ((1.0, "kick=beat"), (2.0, "kick=8th"), (0.5, "kick=half")):
            bpm = 60.0 / (io_med * mult)
            if 50.0 <= bpm <= 220.0:
                cands.append((bpm, tag))
    scored = []
    for bpm, tag in cands:
        period = 60.0 / bpm
        phase, score = grid_phase_score(all_times, period)
        scored.append({"bpm": round(bpm, 2), "basis": tag,
                       "grid_score": round(score, 3), "phase": round(phase, 4)})
    scored.sort(key=lambda s: (-s["grid_score"], abs(s["bpm"] - (ac_bpm or 120.0))))
    return scored


def beat_grid(env, lag, frame_rate, duration):
    """Place beats on the phase that collects the most onset energy."""
    best_phase, best_score = 0.0, -1.0
    for phase in np.arange(0.0, lag, 0.5):
        idx = np.arange(phase, len(env), lag).astype(int)
        idx = idx[idx < len(env)]
        if len(idx) == 0:
            continue
        score = float(env[idx].sum())
        if score > best_score:
            best_score, best_phase = score, float(phase)
    times = []
    t = best_phase / frame_rate
    while t < duration:
        times.append(round(float(t), 3))
        t += lag / frame_rate
    return times


def sections(rms, centroid, frame_rate, hop_sec=0.5):
    """Novelty-based segmentation on a coarse grid.

    A boundary is where the coarse feature vector turns: the similarity between
    the 2s before and the 2s after drops, and the drop has to be a local minimum
    so slow fades do not produce a boundary every window.
    """
    step = max(1, int(round(hop_sec * frame_rate)))
    idx = np.arange(0, len(rms), step)
    f_rms = rms[idx]
    f_cen = centroid[idx]
    def norm(a):
        a = np.asarray(a, dtype=np.float64)
        return (a - a.mean()) / (a.std() + 1e-9)
    feats = np.stack([norm(f_rms), norm(f_cen)], axis=1)
    w = 4  # 4 coarse steps = 2s
    sim = []
    for i in range(w, len(feats) - w):
        a = feats[i - w:i].mean(axis=0)
        b = feats[i:i + w].mean(axis=0)
        cos = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))
        sim.append((i, cos))
    bounds = []
    for j in range(1, len(sim) - 1):
        i, c = sim[j]
        if c < 0.55 and c <= sim[j - 1][1] and c <= sim[j + 1][1]:
            t = i * step / frame_rate
            bounds.append({"time": round(float(t), 3), "similarity": round(c, 3),
                           "rms_before": round(float(f_rms[max(0, i - w)]), 5),
                           "rms_after": round(float(f_rms[min(len(f_rms) - 1, i + w)]), 5)})
    # Keep the strongest boundary within each 2s window: a bar-level loud/quiet
    # swing is not a scene change, and 1s-apart boundaries are always that.
    bounds.sort(key=lambda b: b["similarity"])
    kept = []
    for b in bounds:
        if all(abs(b["time"] - k["time"]) >= 2.0 for k in kept):
            kept.append(b)
    kept.sort(key=lambda b: b["time"])
    return kept


def analyse(path, start=None, dur=None, ffmpeg=None):
    x = decode(path, start, dur, ffmpeg)
    if len(x) < N_FFT * 2:
        raise SystemExit("audio too short: %d samples" % len(x))
    duration = len(x) / float(SR)
    mag = stft_mag(x)
    frame_rate = SR / float(HOP)
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)

    fluxes, peaks = {}, {}
    for name, (lo, hi) in BANDS.items():
        f = band_flux(mag, freqs, lo, hi)
        fluxes[name] = f
        # 120ms minimum gap: fast hi-hats are ~16ths at 160bpm = 94ms, so use a
        # band-specific gap instead of one global value.
        gap = int(round(frame_rate * (0.075 if name == "high" else 0.12)))
        peaks[name] = pick_peaks(f, gap)

    # Merge per-band peaks into a single hit list, tagging the dominant band.
    merged = {}
    for name, ps in peaks.items():
        f = fluxes[name]
        for p in ps:
            t = round(p / frame_rate, 3)
            key = None
            for k in merged:
                if abs(k - t) <= 0.045:
                    key = k
                    break
            if key is None:
                merged[t] = {"t": t, "band": name, "strength": float(f[p])}
            elif float(f[p]) > merged[key]["strength"]:
                merged[key] = {"t": key, "band": name, "strength": float(f[p])}
    onsets = [merged[k] for k in sorted(merged)]

    total = sum(fluxes.values())
    # Tempo from the percussive bands only. Hi-hats fire twice as often as the
    # kick and pull the autocorrelation to a doubled tempo.
    perc = fluxes["low"] + fluxes["mid"]
    ac_bpm, _, conf = estimate_tempo(perc, frame_rate)
    low_times = [p / frame_rate for p in peaks["low"]]
    candidates = refine_tempo(ac_bpm, low_times, [o["t"] for o in onsets])
    bpm = ac_bpm
    if candidates and candidates[0]["grid_score"] >= 0.35:
        bpm = candidates[0]["bpm"]
    lag = frame_rate * 60.0 / bpm if bpm else None
    beats = beat_grid(perc, lag, frame_rate, duration) if lag else []
    downbeats = []
    if len(beats) >= 8:
        # 4/4 assumed: the downbeat phase is the one whose beats carry the most
        # low-band energy. Reported so the decision table can put scene changes
        # on bars rather than on every kick.
        best_phase, best_sum = 0, -1.0
        for phase in range(4):
            idx = [int(round(b * frame_rate)) for b in beats[phase::4]]
            idx = [i for i in idx if 0 <= i < len(fluxes["low"])]
            s = float(sum(fluxes["low"][i] for i in idx))
            if s > best_sum:
                best_sum, best_phase = s, phase
        downbeats = [b for k, b in enumerate(beats) if k % 4 == best_phase]

    rms = np.sqrt(np.convolve(x ** 2, np.ones(N_FFT) / N_FFT, mode="same")[::HOP])[:len(mag)]
    centroid = (mag * freqs).sum(axis=1) / (mag.sum(axis=1) + 1e-9)
    bounds = sections(rms, centroid, frame_rate)

    iois = np.diff([o["t"] for o in onsets]) if len(onsets) > 1 else np.array([])
    return {
        "source": path,
        "window": {"start": start, "duration": round(duration, 3)},
        "sample_rate": SR,
        "frame_rate": round(frame_rate, 3),
        "tempo": {"bpm": bpm, "beat_period": round(60.0 / bpm, 4) if bpm else None,
                  "confidence": conf, "beat_count": len(beats),
                  "candidates": candidates},
        "beats": beats,
        "downbeats": downbeats,
        "bands": {name: {"range_hz": list(BANDS[name]), "count": len(ps),
                         "times": [round(p / frame_rate, 3) for p in ps]}
                  for name, ps in peaks.items()},
        "onsets": onsets,
        "onsets_per_second": round(len(onsets) / duration, 3),
        "inter_onset": {"mean": round(float(iois.mean()), 4) if len(iois) else None,
                         "median": round(float(np.median(iois)), 4) if len(iois) else None},
        "energy": {"mean_rms": round(float(rms.mean()), 5),
                    "peak_rms": round(float(rms.max()), 5),
                    "curve_0p25s": [round(float(v), 5) for v in rms[::max(1, int(0.25 * frame_rate))]]},
        "sections": bounds,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--start", type=float, default=None)
    ap.add_argument("--dur", type=float, default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    doc = analyse(args.input, args.start, args.dur)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    t = doc["tempo"]
    print("[music] %s" % args.input)
    print("[music] dur %.2fs  bpm %s  conf %s  beats %d  onsets %d (%.2f/s)" % (
        doc["window"]["duration"], t["bpm"], t["confidence"], t["beat_count"],
        len(doc["onsets"]), doc["onsets_per_second"]))
    for name, b in doc["bands"].items():
        print("[music]   %-4s %-12s %d" % (name, b["range_hz"], b["count"]))
    print("[music] sections %d: %s" % (len(doc["sections"]),
                                        [s["time"] for s in doc["sections"]][:8]))
    print("[music] wrote", args.out)


if __name__ == "__main__":
    sys.exit(main())
