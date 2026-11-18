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

# The WorkBuddy open platform requires these frontmatter fields on a listing.
# A skill in this repository is authored for the agent, not for a market, so
# the market build adds whatever is missing instead of forcing every author to
# carry fields that only a listing needs.
MARKET_REQUIRED = ("name", "display_name", "display_name_en", "description",
                    "description_zh", "description_en", "allowed-tools",
                    "examples_zh", "examples_en", "author", "version")


def _split_triggers(triggers):
    """Split trigger phrases into Chinese and English halves."""
    zh, en = [], []
    for t in triggers:
        s = str(t).strip()
        if not s:
            continue
        has_cjk = any("一" <= c <= "鿿" for c in s)
        (zh if has_cjk else en).append(s)
    return zh, en


def _market_meta(meta, skill_name):
    """Return a frontmatter dict that satisfies the marketplace requirements."""
    out = dict(meta or {})
    out.setdefault("display_name", out.get("name", skill_name))
    out.setdefault("display_name_en", out.get("name", skill_name))
    out.setdefault("description_zh", out.get("description", ""))
    out.setdefault("description_en", out.get("description", ""))
    out.setdefault("author", "AICUT contributors")
    out.setdefault("version", "0.1.0")
    out.setdefault("allowed-tools", "Bash, Read, Write, Edit")
    zh, en = _split_triggers(out.get("triggers") or [])
    out.setdefault("examples_zh", zh[:3] or ["用这个特效剪一段片子"])
    out.setdefault("examples_en", en[:3] or ["cut a clip with this effect"])
    # The market shows one short Chinese description, so make sure it exists
    # even when the repository description is English only.
    if not out.get("description_zh"):
        out["description_zh"] = out.get("description", "")
    return out


def _market_front(text, meta, skill_name):
    """Rebuild the frontmatter block with the market fields added."""
    import yaml
    m = FRONT.match(text)
    if not m:
        return text
    body = text[m.end():]
    merged = _market_meta(meta, skill_name)
    block = yaml.safe_dump(merged, allow_unicode=True, sort_keys=False,
                           default_flow_style=False).rstrip()
    # The packaged archive carries the kernel, so the placeholder points at the
    # directory the skill was unpacked into rather than at a repository path.
    body = body.replace("`$AICUT_ROOT`", "the directory this skill was unpacked into")
    body = body.replace("$AICUT_ROOT",
                        "the directory this skill was unpacked into")
    return "---\n%s\n---\n%s" % (block, body)


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


def _kernel_files():
    """The runtime a skill needs in order to actually do something.

    A marketplace install gives the user the skill folder only, so the kernel
    has to travel with it. The kernel is small enough to carry (a few hundred
    kilobytes of Python) and is what makes the packaged skill executable
    rather than a description.
    """
    out = []
    lib_dir = os.path.join(ROOT, "lib")
    if os.path.isdir(lib_dir):
        for fn in sorted(os.listdir(lib_dir)):
            if not fn.endswith(".py"):
                continue
            out.append(("lib/" + fn, os.path.join(lib_dir, fn)))
    for fn in ("aicut.py", "params.yaml"):
        p = os.path.join(ROOT, fn)
        if os.path.exists(p):
            out.append((fn, p))
    return out


def build(name, out_dir, force=False, market=False, with_kernel=False):
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
    suffix = "-market" if market else ""
    out_path = os.path.join(out_dir, "%s%s.zip" % (stem, suffix))
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel, path in _files(skill_dir):
            if market and rel == "SKILL.md":
                text = io.open(path, "r", encoding="utf-8").read()
                zf.writestr(rel, _market_front(text, meta, name))
            else:
                zf.write(path, rel)
        if with_kernel:
            for rel, path in _kernel_files():
                zf.write(path, rel)
    return out_path, problems


def build_all(out_dir, force=False, market=False, with_kernel=False):
    """Package every skill. Returns a list of (name, path, problems)."""
    results = []
    if not os.path.isdir(SRC):
        return results
    for name in sorted(os.listdir(SRC)):
        if name.startswith(("_", ".")):
            continue
        if not os.path.isdir(os.path.join(SRC, name)):
            continue
        path, problems = build(name, out_dir, force=force, market=market,
                               with_kernel=with_kernel)
        results.append((name, path, problems))
    return results
