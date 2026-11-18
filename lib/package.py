# -*- coding: utf-8 -*-
"""Package a standard skill into a distributable zip.

Skill marketplaces expect one archive per skill, with SKILL.md at the root
of the archive and a valid frontmatter block (at least `name` and
`description`). The runtime is not shipped with the skill: AICUT's kernel
stays in this repository and is installed separately, which is what keeps a
published skill small and lets the kernel be updated without republishing
every skill.

Layout of the produced zip:

    SKILL.md
    scripts/build.py
    references/params.yaml
    references/pitfalls.md
    README.md              (optional, from the skill directory)
"""
import io
import os
import re
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "skills")
FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)

INCLUDE = ("SKILL.md",)
INCLUDE_DIRS = ("scripts", "references")
SKIP_DIRS = ("__pycache__",)
SKIP_SUFFIX = (".pyc", ".pyo")


def _front(skill_dir):
    import yaml
    p = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(p):
        return {}
    text = io.open(p, "r", encoding="utf-8").read()
    m = FRONT.match(text)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _files(skill_dir):
    out = []
    for rel in INCLUDE:
        p = os.path.join(skill_dir, rel)
        if os.path.exists(p):
            out.append((rel, p))
    for d in INCLUDE_DIRS:
        base = os.path.join(skill_dir, d)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for fn in sorted(files):
                if fn.endswith(SKIP_SUFFIX):
                    continue
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, skill_dir).replace(os.sep, "/")
                out.append((rel, p))
    return out


def check(skill_dir):
    """Return a list of problems that would make the archive unusable."""
    problems = []
    sk = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(sk):
        return ["SKILL.md missing"]
    meta = _front(skill_dir)
    if not meta:
        problems.append("SKILL.md has no valid YAML frontmatter")
    else:
        for key in ("name", "description"):
            if not meta.get(key):
                problems.append("frontmatter is missing '%s'" % key)
    if not os.path.exists(os.path.join(skill_dir, "scripts", "build.py")):
        problems.append("scripts/build.py missing")
    if not os.path.exists(os.path.join(skill_dir, "references", "params.yaml")):
        problems.append("references/params.yaml missing")
    return problems


def build(name, out_dir, force=False):
    """Package one skill. Returns (path, problems)."""
    skill_dir = os.path.join(SRC, name)
    if not os.path.isdir(skill_dir):
        return None, ["skill not found: %s" % name]
    problems = check(skill_dir)
    if problems and not force:
        return None, problems
    meta = _front(skill_dir)
    stem = str(meta.get("name") or name)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "%s.zip" % stem)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, path in _files(skill_dir):
            zf.write(path, rel)
    return out_path, problems


def build_all(out_dir, force=False):
    """Package every skill. Returns a list of (name, path, problems)."""
    results = []
    if not os.path.isdir(SRC):
        return results
    for name in sorted(os.listdir(SRC)):
        if name.startswith(("_", ".")):
            continue
        if not os.path.isdir(os.path.join(SRC, name)):
            continue
        path, problems = build(name, out_dir, force=force)
        results.append((name, path, problems))
    return results
