# -*- coding: utf-8 -*-
"""渲染层：逐镜独立出片 + 内容哈希缓存 + concat + 混音。"""
import hashlib
import importlib.util
import io
import json
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import assets
from .ff import encode, run


def load_effect(name):
    path = os.path.abspath(os.path.join("effects", name, "run.py"))
    if not os.path.exists(path):
        raise RuntimeError("effect not found: %s" % name)
    spec = importlib.util.spec_from_file_location("aicut_effect_%s" % name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def effect_code_hash(name):
    """effect 的 run.py 改了，缓存必须失效，否则改代码看不到新画面。"""
    if name == "base":
        return "base"
    p = os.path.abspath(os.path.join("effects", name, "run.py"))
    if not os.path.exists(p):
        return "missing"
    with open(p, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()[:10]


def shot_key(shot, caps, assets_index=None):
    payload = {
        "src": shot["src"], "seg": shot["seg"], "speed": shot["speed"],
        "effect": shot["effect"], "params": shot["params"],
        "caps": caps["hash"],
        # 叠加素材是从 prepare 索引里查出来的，索引变了缓存必须失效
        "overlays": (assets_index or {}).get("overlays", {}),
        "effect_code": effect_code_hash(shot["effect"]),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def base_chain(shot, cfg, caps):
    """基础链输出 [g]。推镜幅度来自 card 旋钮，保证每帧都有像素变化。"""
    pr = cfg["project"]
    w, h, fps = int(pr["width"]), int(pr["height"]), int(pr["fps"])
    p = shot["params"]
    push = float(p.get("push_px", 22))
    hz = float(p.get("shake_hz", 0.14))
    contrast = float(p.get("contrast", 1.13))
    zw, zh = int(w * 1.16), int(h * 1.16)
    d = max(0.05, shot["dur"])
    x = "46+%.1f*min(t/%.4f,1)+2*sin(%.4f*t)" % (push, d, 6.2832 * hz)
    y = "50+%.1f*min(t/%.4f,1)+1.4*cos(%.4f*t)" % (push * .64, d, 6.2832 * hz)
    parts = ["[0:v]setpts=PTS-STARTPTS,fps=%d," % fps,
             "scale=%d:%d:flags=lanczos," % (zw, zh),
             "crop=%d:%d:'%s':'%s',setsar=1," % (w, h, x, y),
             "eq=contrast=%.3f:saturation=1.24," % contrast]
    if caps["filters"].get("tpad", False):
        parts.append("tpad=stop_mode=clone:stop_duration=1,")
    parts.append("format=yuv420p[g]")
    return "".join(parts)


def render_shot(shot, cfg, caps, shots_dir, assets_index=None):
    # 文件名就是内容哈希，缓存跨 run 共享：用户调一个参数只让命中的镜头失效。
    key = shot_key(shot, caps, assets_index)
    out = os.path.join(shots_dir, key + ".mp4")
    if os.path.exists(out) and os.path.getsize(out) > 600:
        return out, True

    src = os.path.join(cfg["paths"]["videos"], shot["src"])
    s, e = shot["seg"]
    inputs = ["-ss", "%.4f" % s, "-t", "%.4f" % max(0.04, e - s), "-i", src]
    chain = [base_chain(shot, cfg, caps)]
    if shot["effect"] != "base":
        mod = load_effect(shot["effect"])
        p = dict(shot["params"])
        # 内部字段（下划线开头）不属于用户可调旋钮，只给 effect 运行期取用
        p["_overlays"] = cfg["paths"]["overlays"]
        p["_assets"] = assets_index or {}
        p["_geom"] = {"w": cfg["project"]["width"],
                      "h": cfg["project"]["height"],
                      "fps": cfg["project"]["fps"]}
        extra, lines = mod.build(shot, p, caps)
        inputs += [str(x) for x in extra]
        chain += list(lines)
    else:
        chain.append("[g]null[out]")
    fc = ";".join(chain)
    encode(cfg["paths"]["ffmpeg"], inputs, fc, out, shot["dur"], cfg)
    return out, False


def render_all(plan, cfg, caps, run_dir):
    shots_dir = os.path.abspath(os.path.normpath(
        os.path.join(cfg["paths"]["runs"], "_cache", "shots")))
    os.makedirs(shots_dir, exist_ok=True)
    files = [None] * len(plan["shots"])
    hits = [0]
    idx = assets.load_index(cfg)

    def job(sh):
        return sh["index"], render_shot(sh, cfg, caps, shots_dir, idx)

    with ThreadPoolExecutor(max_workers=int(cfg["project"]["workers"])) as ex:
        futs = [ex.submit(job, sh) for sh in plan["shots"]]
        done = 0
        for fu in as_completed(futs):
            i, (path, cached) = fu.result()
            files[i] = path
            hits[0] += int(cached)
            done += 1
            if done % 20 == 0 or done == len(futs):
                print("[render] %d/%d shots, %d cached" %
                      (done, len(futs), hits[0]), flush=True)
    return files, hits[0]


def finish(files, plan, cfg, run_dir):
    ff = cfg["paths"]["ffmpeg"]
    lst = os.path.join(run_dir, "list.txt")
    with io.open(lst, "w", encoding="utf-8") as fh:
        for f in files:
            # 旧版 ffmpeg 的 concat demuxer 会把盘符开头的绝对路径当相对路径拼接，
            # 必须写相对 list.txt 所在目录的路径。
            rel = os.path.relpath(str(f), os.path.dirname(lst)).replace("\\", "/")
            fh.write("file '%s'\n" % rel)
    silent = os.path.join(run_dir, "silent.mp4")
    # 该构建按 cwd 解析 concat 的 file 条目，显式把 cwd 设成 run 目录，
    # -i 与输出都用相对文件名，避免盘符路径被误判。
    run([ff, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "list.txt",
         "-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-pix_fmt", "yuv420p", "silent.mp4"], cwd=run_dir)

    out = os.path.join(run_dir, "final.mp4")
    bgm = cfg["paths"]["bgm"]
    if os.path.exists(bgm):
        run([ff, "-y", "-v", "error", "-i", silent,
             "-ss", "%.3f" % float(cfg["project"]["m0"]), "-i", bgm,
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
             "-b:a", "192k", "-ar", "48000", "-shortest",
             "-movflags", "+faststart", out])
    else:
        run([ff, "-y", "-v", "error", "-i", silent, "-c:v", "copy", out])
    return out
