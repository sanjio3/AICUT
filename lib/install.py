# -*- coding: utf-8 -*-
"""Install the standard skills under skills/ into a directory the host scans.

The host only scans `~/.workbuddy/skills/` (user scope) and
`<workspace>/.workbuddy/skills/` (project scope). The `skills/` directory in
this repository is the source; installing is only a copy, and the source
remains the single truth. While installing, the `$AICUT_ROOT` placeholder in
SKILL.md is replaced with the absolute path of this repository, so the host can
locate aicut.py from any workspace.
"""
import argparse
import io
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "skills")
PLACEHOLDER = "$AICUT_ROOT"


def _kernel_files():
    """The runtime that has to travel with a self-contained install."""
    out = []
    lib_dir = os.path.join(ROOT, "lib")
    if os.path.isdir(lib_dir):
        for fn in sorted(os.listdir(lib_dir)):
            if fn.endswith(".py"):
                out.append((os.path.join("lib", fn),
                            os.path.join(lib_dir, fn)))
    for fn in ("aicut.py", "params.yaml"):
        p = os.path.join(ROOT, fn)
        if os.path.exists(p):
            out.append((fn, p))
    return out


def _front_name(skill_dir):
    import re
    import yaml
    p = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(p):
        return os.path.basename(skill_dir)
    text = io.open(p, "r", encoding="utf-8").read()
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return os.path.basename(skill_dir)
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return os.path.basename(skill_dir)
    return str(meta.get("name") or os.path.basename(skill_dir))


def _skills(only=None):
    out = []
    if not os.path.isdir(SRC):
        return out
    for name in sorted(os.listdir(SRC)):
        if name.startswith(("_", ".")):
            continue
        d = os.path.join(SRC, name)
        if not os.path.isdir(d) or not os.path.exists(os.path.join(d, "SKILL.md")):
            continue
        if only and name not in only:
            continue
        out.append((name, d, _front_name(d)))
    return out


def install(target, force=False, dry_run=False, only=None, quiet=False,
            with_kernel=False):
    skills = _skills(only)
    if not skills:
        print("no skills found under %s" % SRC)
        return 1
    print("source : %s" % SRC)
    print("target : %s" % target)
    print("root   : %s" % ROOT)
    if with_kernel:
        print("kernel : included, so the skill runs on its own")
    if dry_run:
        print("(dry-run: nothing will be written)")
    rc = 0
    for effect, src_dir, skill_name in skills:
        dst = os.path.join(target, skill_name)
        exists = os.path.exists(dst)
        status = "overwrite" if exists else "create"
        if exists and not force and not dry_run:
            print("SKIP    %-24s -> %s (exists, use --force)" % (effect, dst))
            continue
        print("%-7s %-24s -> %s" % (status.upper(), effect, dst))
        if dry_run:
            continue
        if exists and force:
            shutil.rmtree(dst)
        shutil.copytree(src_dir, dst,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        sk = os.path.join(dst, "SKILL.md")
        text = io.open(sk, "r", encoding="utf-8").read()
        if with_kernel:
            # A self-contained install: the kernel travels with the skill, so
            # the placeholder points at the directory the skill lives in.
            for rel, path in _kernel_files():
                kdst = os.path.join(dst, rel)
                os.makedirs(os.path.dirname(kdst), exist_ok=True)
                shutil.copy2(path, kdst)
            if PLACEHOLDER in text:
                io.open(sk, "w", encoding="utf-8").write(
                    text.replace(PLACEHOLDER, "the directory this skill is in"))
        elif PLACEHOLDER in text:
            io.open(sk, "w", encoding="utf-8").write(
                text.replace(PLACEHOLDER, ROOT.replace("\\", "/")))
        print("        installed")
    if not dry_run:
        print("done. restart the host or reload skills to pick them up.")
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(prog="install")
    ap.add_argument("--target", default=None, help="target skills directory")
    ap.add_argument("--project", default=None,
                    help="install into <dir>/.workbuddy/skills instead")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None, help="comma-separated effect names")
    ap.add_argument("--with-kernel", action="store_true",
                    help="also install lib/ and aicut.py so the skill runs "
                         "without the repository")
    a = ap.parse_args(argv)
    if a.project:
        target = os.path.join(os.path.abspath(a.project), ".workbuddy", "skills")
    elif a.target:
        target = os.path.abspath(a.target)
    else:
        target = os.path.expanduser(os.path.join("~", ".workbuddy", "skills"))
    only = [x.strip() for x in a.only.split(",")] if a.only else None
    return install(target, force=a.force, dry_run=a.dry_run, only=only,
                   with_kernel=a.with_kernel)


if __name__ == "__main__":
    sys.exit(main())
