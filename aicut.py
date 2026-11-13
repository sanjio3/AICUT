# -*- coding: utf-8 -*-
"""AICUT 薄编排入口。宿主 Agent 用 Bash 直接调用，不启动服务、无常驻进程。"""
import argparse
import datetime
import io
import json
import os
import re
import shutil
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from lib import (assets, catalog, doctor, ff, music, plan as planmod,  # noqa: E402
                 pool as poolmod, qa, render, validate)


def config():
    os.chdir(ROOT)
    return ff.load_config(os.path.join(ROOT, "params.yaml"))


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, indent=2))


def write_yaml(path, obj):
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(yaml.safe_dump(obj, allow_unicode=True, sort_keys=True))


def read_overrides(path):
    if not path or not os.path.exists(path):
        return {}
    with io.open(path, "r", encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}
    return dict(doc.get("overrides") or {})


def parse_value(s):
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    try:
        return float(s) if ("." in s or "e" in s.lower()) else int(s)
    except ValueError:
        return s


def new_id():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:20]


def run_dir(cfg, rid):
    # 必须规范化：路径里残留 "\./" 会让旧版 ffmpeg 的 concat demuxer
    # 把相对 file 条目解析到错误的基准目录。
    d = os.path.abspath(os.path.normpath(
        os.path.join(ROOT, cfg["paths"]["runs"], rid)))
    os.makedirs(d, exist_ok=True)
    return d


def cmd_doctor(args):
    cfg = config()
    caps = doctor.probe(cfg["paths"]["ffmpeg"])
    write_json(os.path.join(ROOT, "runs", "_caps.json"), caps)
    print(doctor.report(caps))
    print("materials: %s" % cfg["paths"]["videos"])
    print("bgm      : %s" % cfg["paths"]["bgm"])


def cmd_catalog(args):
    config()
    print(catalog.report())
    if args.say:
        hits = catalog.lookup(args.say)
        print("say    : %s" % args.say)
        print("match  : %s" % (", ".join(hits) or "none"))
        if hits:
            print("plan   : python aicut.py plan --run <id> --effects %s"
                  % ",".join(hits))


def cmd_new_effect(args):
    config()
    name = args.name.strip()
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", name):
        raise SystemExit("effect name must be lowercase letters, digits or hyphens")
    src = os.path.join(ROOT, "effects", "_template")
    dst = os.path.join(ROOT, "effects", name)
    if os.path.exists(dst):
        raise SystemExit("effect already exists: effects/%s" % name)
    shutil.copytree(src, dst)
    for fn in ("SKILL.md", "run.py", "params.yaml"):
        p = os.path.join(dst, fn)
        with io.open(p, "r", encoding="utf-8") as fh:
            text = fh.read()
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(text.replace("<NAME>", name))
    print("created: effects/%s/ (SKILL.md, run.py, params.yaml)" % name)
    print("1. fill in triggers, the four required sections and params.yaml")
    print("2. python aicut.py validate-effect %s" % name)
    print("3. python aicut.py catalog  (confirm it is discoverable)")


def cmd_validate(args):
    config()
    if args.all or not args.name:
        results = validate.check_all()
    else:
        results = [validate.check(args.name)]
    print(validate.report(results))
    if any(not r["ok"] for r in results):
        raise SystemExit(1)


def cmd_prepare(args):
    cfg = config()
    doc = assets.prepare(cfg)
    vids = doc["videos"]
    dark = [f for f, r in vids.items() if r.get("dark_span")]
    ovs = doc["overlays"]
    print("videos   : %d indexed, %d contain dark spans (skipped in strict pass)" %
          (len(vids), len(dark)))
    if dark:
        print("  dark   : %s" % ", ".join(dark[:6]))
    print("overlays : %d found, %d classified as fire" %
          (len(ovs.get("all", [])), len(ovs.get("fire", []))))
    print("music    : %s" % doc["music"])
    print("cache    : %s" % assets.cache_dir(cfg))


def cmd_params(args):
    cfg = config()
    rows = planmod.param_table(cfg, args.effect)
    print("effect: %s" % (args.effect or "global"))
    for r in rows:
        if r["locked"]:
            rng = "locked"
        elif r["min"] is not None:
            rng = "[%s, %s]" % (r["min"], r["max"])
        else:
            rng = "free/enum"
        print("  %-38s = %-10s %-16s affects=%s%s" %
              (r["name"], str(r["current"]), rng,
               ",".join(r["affects"]) or "-",
               "  [LOCKED]" if r["locked"] else ""))
        if r["note"]:
            print("      note: %s" % r["note"])


def cmd_attribute(args):
    cfg = config()
    hits = planmod.attribute(cfg, args.say)
    if not hits:
        print("no attribution hit for: %s" % args.say)
        return
    for h in hits:
        print("  %s -> %s" % ("/".join(h["say"]), ", ".join(h["params"])))
        print("      %s" % h.get("hint", ""))


def cmd_plan(args):
    cfg = config()
    rid = args.run or new_id()
    d = run_dir(cfg, rid)
    pfile = os.path.join(d, "params.yaml")
    with_doc = {}
    if os.path.exists(pfile):
        with io.open(pfile, "r", encoding="utf-8") as fh:
            with_doc = yaml.safe_load(fh) or {}
    ov = dict(with_doc.get("overrides") or {})
    sel = dict(with_doc.get("selection") or {})
    if args.params:
        ov.update(read_overrides(args.params))
    if args.effects:
        sel["effects"] = [x.strip() for x in args.effects.split(",") if x.strip()]
    for kv in args.set or []:
        if "=" not in kv:
            raise SystemExit("--set expects key=value, got: %s" % kv)
        k, v = kv.split("=", 1)
        ov[k.strip()] = parse_value(v.strip())
    write_yaml(pfile, {"selection": sel, "overrides": ov})

    scalars = planmod.merged(cfg, None, ov, all_effects=True)
    write_yaml(os.path.join(d, "effective.yaml"), scalars)

    grid = music.load(cfg)
    p = poolmod.Pool(cfg, scalars["pool"])
    pl = planmod.build(cfg, grid, p, overrides=ov, duration=args.duration,
                       effects=sel.get("effects"))
    p.close()
    write_json(os.path.join(d, "plan.json"), pl)

    counts = {}
    for sh in pl["shots"]:
        counts[sh["effect"]] = counts.get(sh["effect"], 0) + 1
    print("run      : %s" % rid)
    print("shots    : %d  duration=%.2fs  beats=%d" %
          (len(pl["shots"]), pl["project"]["duration"], len(pl["beat_frames"])))
    print("effects  : %s" % ", ".join("%s=%d" % kv for kv in sorted(counts.items())))
    print("selection: %s" % (sel.get("effects") or "default rotation"))
    print("overrides: %s" % (ov or "none"))
    print("repeat   : %.4f" % pl["repeat_ratio"])
    print("plan     : %s" % os.path.join(d, "plan.json"))


def cmd_render(args):
    cfg = config()
    d = run_dir(cfg, args.run)
    pf = os.path.join(d, "plan.json")
    if not os.path.exists(pf):
        raise SystemExit("plan.json missing, run plan first: %s" % pf)
    with io.open(pf, "r", encoding="utf-8") as fh:
        pl = json.load(fh)
    caps = doctor.probe(cfg["paths"]["ffmpeg"])
    files, cached = render.render_all(pl, cfg, caps, d)
    out = render.finish(files, pl, cfg, d)
    print("render   : %d shots, %d cached (%.0f%% reused)" %
          (len(files), cached, 100.0 * cached / max(1, len(files))))
    print("output   : %s" % out)


def cmd_qa(args):
    cfg = config()
    d = run_dir(cfg, args.run)
    final = os.path.join(d, "final.mp4")
    if not os.path.exists(final):
        raise SystemExit("final.mp4 missing, run render first: %s" % final)
    with io.open(os.path.join(d, "plan.json"), "r", encoding="utf-8") as fh:
        pl = json.load(fh)
    r = qa.analyze(final, int(cfg["project"]["fps"]), pl)
    g = qa.gate(r, cfg)
    write_json(os.path.join(d, "qa.json"), r)
    write_json(os.path.join(d, "gate.json"), g)
    print("frames=%d dur=%.2fs V=%.1f dark=%.1f%% bright=%.1f%% dup=%.1f%%" %
          (r["frames"], r["duration"], r["V"], r["dark_pct"],
           r["bright_pct"], r["dup_pct"]))
    print("cut=%.2f/s motion p50=%.1f p90=%.1f laplacian=%.1f repeat=%.4f" %
          (r["cut_rate"], r["motion_p50"], r["motion_p90"],
           r["laplacian_var"], r["repeat_ratio"]))
    print("gate     : %s" % g["status"])
    for f in g["failures"]:
        print("  WARN   : %s" % f)


def cmd_diff(args):
    cfg = config()
    root = os.path.join(ROOT, cfg["paths"]["runs"])
    r = qa.diff(root, args.a, args.b)
    print("diff %s -> %s" % (r["run_a"], r["run_b"]))
    print("params changed:")
    if not r["params_changed"]:
        print("  (none)")
    for c in r["params_changed"]:
        print("  %-40s %s -> %s" % (c["param"], c["a"], c["b"]))
    print("metrics:")
    for m in r["metrics"]:
        print("  %-16s %8s -> %-8s  delta=%+s" %
              (m["metric"], m["a"], m["b"], m["delta"]))
    print("gate     : %s -> %s" % (r["gate_a"], r["gate_b"]))


def main():
    ap = argparse.ArgumentParser(prog="aicut")
    sub = ap.add_subparsers(dest="action")

    sub.add_parser("doctor")
    sub.add_parser("prepare")

    p = sub.add_parser("catalog")
    p.add_argument("--say", default=None)

    p = sub.add_parser("new-effect")
    p.add_argument("name")

    p = sub.add_parser("validate-effect")
    p.add_argument("name", nargs="?", default=None)
    p.add_argument("--all", action="store_true")

    p = sub.add_parser("params")
    p.add_argument("--effect", default=None)

    p = sub.add_parser("attribute")
    p.add_argument("--say", required=True)

    p = sub.add_parser("plan")
    p.add_argument("--run", default=None)
    p.add_argument("--params", default=None)
    p.add_argument("--effects", default=None,
                   help="comma-separated effect names the user actually asked for")
    p.add_argument("--duration", type=float, default=None)
    p.add_argument("--set", action="append", default=[])

    p = sub.add_parser("render")
    p.add_argument("--run", required=True)

    p = sub.add_parser("qa")
    p.add_argument("--run", required=True)

    p = sub.add_parser("diff")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)

    args = ap.parse_args()
    handlers = {"doctor": cmd_doctor, "prepare": cmd_prepare,
                "catalog": cmd_catalog, "new-effect": cmd_new_effect,
                "validate-effect": cmd_validate,
                "params": cmd_params,
                "attribute": cmd_attribute, "plan": cmd_plan,
                "render": cmd_render, "qa": cmd_qa, "diff": cmd_diff}
    if not args.action:
        ap.print_help()
        return
    handlers[args.action](args)


if __name__ == "__main__":
    main()
