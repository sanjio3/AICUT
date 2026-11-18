# -*- coding: utf-8 -*-
"""AICUT thin orchestration entry point.

The host agent invokes this directly through Bash. Nothing starts a service,
opens a port or keeps a process alive. All user-visible output is in English;
Chinese is used only for the runtime mapping of Chinese user speech to
parameters, which lives in params.yaml rather than in code.
"""
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

from lib import (assets, catalog, confirm as confirmmod, doctor, ff, music,  # noqa: E402
                 package as packagemod, plan as planmod, pool as poolmod, qa,
                 render, validate)
from lib import install as installmod  # noqa: E402


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
    # Must be normalised: a leftover "\./" in the path makes the old ffmpeg
    # concat demuxer resolve relative file entries against the wrong base.
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
    src = os.path.join(ROOT, "skills", "_template")
    dst = os.path.join(ROOT, "skills", name)
    if os.path.exists(dst):
        raise SystemExit("effect already exists: skills/%s" % name)
    shutil.copytree(src, dst)
    for fn in ("SKILL.md",
               os.path.join("scripts", "build.py"),
               os.path.join("references", "params.yaml"),
               os.path.join("references", "pitfalls.md")):
        p = os.path.join(dst, fn)
        with io.open(p, "r", encoding="utf-8") as fh:
            text = fh.read()
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(text.replace("<NAME>", name))
    print("created: skills/%s/" % name)
    print("  SKILL.md                    frontmatter, when to use, required sections")
    print("  scripts/build.py            build() pure function")
    print("  references/params.yaml      tunable knobs")
    print("  references/pitfalls.md      parameters, thresholds, pitfalls, boundaries")
    print("next:")
    print("  1. fill in SKILL.md triggers and the four required sections")
    print("  2. python aicut.py validate-effect %s" % name)
    print("  3. python aicut.py catalog  (confirm it is discoverable)")
    print("  4. python aicut.py install --dry-run  (see where it would go)")


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
    if doc.get("demo_fallback"):
        print("  note   : no media found, generated synthetic demo clips")
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
    plan_path = os.path.join(d, "plan.json")
    pl = confirmmod.write_plan(plan_path, pl, cfg)

    counts = {}
    for sh in pl["shots"]:
        counts[sh["effect"]] = counts.get(sh["effect"], 0) + 1
    blk = pl.get("confirmation") or {}
    print("run      : %s" % rid)
    print("shots    : %d  duration=%.2fs  beats=%d" %
          (len(pl["shots"]), pl["project"]["duration"], len(pl["beat_frames"])))
    print("effects  : %s" % ", ".join("%s=%d" % kv for kv in sorted(counts.items())))
    print("selection: %s" % (sel.get("effects") or "default rotation"))
    print("overrides: %s" % (ov or "none"))
    print("repeat   : %.4f" % pl["repeat_ratio"])
    print("plan     : %s" % os.path.join(d, "plan.json"))
    print("")
    print("NOT CONFIRMED YET. Ask the user these questions before rendering:")
    for i, q in enumerate(blk.get("questions") or [], 1):
        print("  %d. %s" % (i, q))
    print("")
    print("plan hash: %s" % blk.get("plan_hash"))
    print("after the user answers, run:")
    print("  python aicut.py confirm --run %s --hash %s"
          % (rid, blk.get("plan_hash")))
    print("then:")
    print("  python aicut.py render --run %s" % rid)


def cmd_confirm(args):
    cfg = config()
    d = run_dir(cfg, args.run)
    pf = os.path.join(d, "plan.json")
    if not os.path.exists(pf):
        raise SystemExit("plan.json missing: %s" % pf)
    blk = confirmmod.confirm(pf, args.hash, note=args.note)
    print("confirmed: %s" % blk.get("confirmed_at"))
    print("hash     : %s" % blk.get("confirmed_hash"))
    if args.note:
        print("note     : %s" % args.note)
    print("you can now run:")
    print("  python aicut.py render --run %s" % args.run)


def cmd_render(args):
    cfg = config()
    d = run_dir(cfg, args.run)
    pf = os.path.join(d, "plan.json")
    ok, pl, msg = confirmmod.check(pf)
    if not ok:
        raise SystemExit(
            "render refused: %s\n"
            "AICUT does not render without a user-confirmed plan. Put the "
            "questions above to the user, wait for the answer, then run "
            "`aicut.py confirm` and retry." % msg)
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


def cmd_install(args):
    if args.project:
        target = os.path.join(os.path.abspath(args.project), ".workbuddy", "skills")
    elif args.target:
        target = os.path.abspath(args.target)
    else:
        target = os.path.expanduser(os.path.join("~", ".workbuddy", "skills"))
    only = [x.strip() for x in args.only.split(",")] if args.only else None
    rc = installmod.install(target, force=args.force, dry_run=args.dry_run,
                            only=only, with_kernel=args.with_kernel)
    if rc:
        raise SystemExit(rc)


def cmd_package(args):
    cfg = config()
    out = args.out or os.path.join(ROOT, "dist")
    market = bool(args.market)
    with_kernel = bool(args.with_kernel) or market
    # The marketplace publishes a folder named after the skill, so that is the
    # default shape. --flat is for importers that want SKILL.md at the root.
    fold = not args.flat
    if args.effect:
        path, problems = packagemod.build(args.effect, out, force=args.force,
                                         market=market,
                                         with_kernel=with_kernel, fold=fold)
        if path is None:
            for p in problems:
                print("ERROR   %s" % p)
            raise SystemExit(1)
        for p in problems:
            print("WARN    %s" % p)
        print("package : %s" % path)
        print("size    : %d bytes" % os.path.getsize(path))
        if args.check:
            packagemod.verify(path)
        return
    results = packagemod.build_all(out, force=args.force, market=market,
                                   with_kernel=with_kernel, fold=fold)
    if not results:
        print("no skills found under %s" % packagemod.SRC)
        return
    print("output  : %s" % out)
    if market:
        print("mode    : market (marketplace frontmatter fields, kernel included)")
    if fold:
        print("mode    : marketplace shape (a folder named after the skill)")
    else:
        print("mode    : flat (SKILL.md at the archive root)")
    for name, path, problems in results:
        if path is None:
            print("FAILED  %-22s %s" % (name, "; ".join(problems)))
        else:
            print("OK      %-22s %s (%d bytes)" %
                  (name, path, os.path.getsize(path)))
            for p in problems:
                print("        WARN  %s" % p)
            if args.check:
                packagemod.verify(path)


def cmd_publish(args):
    """Publish the skill packages as GitHub release assets."""
    import subprocess
    script = os.path.join(ROOT, "tools", "publish_release.py")
    if not os.path.exists(script):
        raise SystemExit("publish script missing: %s" % script)
    notes = args.notes_file
    if notes is None:
        default = os.path.join(ROOT, "docs",
                               "release-notes-%s.md" % args.tag)
        if os.path.exists(default):
            notes = default
    cmd = [sys.executable, script, "--tag", args.tag]
    if notes:
        cmd += ["--notes-file", notes]
    if args.dry_run:
        cmd.append("--dry-run")
    raise SystemExit(subprocess.call(cmd, cwd=ROOT))


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

    p = sub.add_parser("confirm")
    p.add_argument("--run", required=True)
    p.add_argument("--hash", default=None,
                   help="plan hash printed by `plan` (optional but safer)")
    p.add_argument("--note", default=None,
                   help="what the user decided, stored with the confirmation")

    p = sub.add_parser("qa")
    p.add_argument("--run", required=True)

    p = sub.add_parser("diff")
    p.add_argument("--a", required=True)
    p.add_argument("--b", required=True)

    p = sub.add_parser("install")
    p.add_argument("--target", default=None,
                   help="target skills directory (default ~/.workbuddy/skills)")
    p.add_argument("--project", default=None,
                   help="install into <dir>/.workbuddy/skills")
    p.add_argument("--only", default=None, help="comma-separated effect names")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--with-kernel", action="store_true",
                   help="also install lib/ and aicut.py so the skill runs "
                        "without the repository")

    p = sub.add_parser("publish")
    p.add_argument("--tag", required=True,
                   help="release tag, for example v0.4.0")
    p.add_argument("--notes-file", default=None,
                   help="markdown file with the release notes")
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("package")
    p.add_argument("--effect", default=None,
                   help="package one skill; omit to package all of them")
    p.add_argument("--out", default=None, help="output directory (default ./dist)")
    p.add_argument("--force", action="store_true",
                   help="package even when the contract check reports problems")
    p.add_argument("--market", action="store_true",
                   help="add the frontmatter fields a skill marketplace requires")
    p.add_argument("--flat", action="store_true",
                   help="put SKILL.md at the archive root instead of inside a "
                        "folder named after the skill")
    p.add_argument("--check", action="store_true",
                   help="verify each archive against what an importer expects")
    p.add_argument("--with-kernel", action="store_true",
                   help="include lib/ and aicut.py so the package is executable")

    args = ap.parse_args()
    handlers = {"doctor": cmd_doctor, "prepare": cmd_prepare,
                "catalog": cmd_catalog, "new-effect": cmd_new_effect,
                "validate-effect": cmd_validate,
                "params": cmd_params,
                "attribute": cmd_attribute, "plan": cmd_plan,
                "render": cmd_render, "qa": cmd_qa, "diff": cmd_diff,
                "confirm": cmd_confirm,
                "install": cmd_install, "package": cmd_package,
                "publish": cmd_publish}
    if not args.action:
        ap.print_help()
        return
    handlers[args.action](args)


if __name__ == "__main__":
    main()
