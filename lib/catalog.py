# -*- coding: utf-8 -*-
"""Scan the standard skills under skills/ and summarise them for viewing and
debugging.

**Routing is done by the host agent.** The host reads each skill's
`description` (when to use it), judges the user's wording semantically and
loads the matching SKILL.md. The `triggers` field here is only an optional
accelerator and a debugging aid, no longer the single source of runtime
routing. When triggers are missing, keywords are derived from the description
so a new skill is still discoverable without them.
"""
import io
import os
import re

import yaml

FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
SKIP_PREFIX = ("_", ".")
ROOT = "skills"


def parse_front(path):
    with io.open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    m = FRONT.match(text)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _derive_triggers(meta):
    """Derive fallback keywords from the description when triggers are absent."""
    explicit = [str(x).strip() for x in (meta.get("triggers") or []) if str(x).strip()]
    if explicit:
        return explicit
    desc = str(meta.get("description") or "")
    quoted = re.findall(r"「([^」]{2,12})」", desc)
    if quoted:
        return quoted
    words = re.findall(r"[\u4e00-\u9fa5]{2,6}", desc)
    seen, out = set(), []
    for w in words[:8]:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def scan(root=ROOT):
    out = {}
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        if name.startswith(SKIP_PREFIX):
            continue
        d = os.path.join(root, name)
        sk = os.path.join(d, "SKILL.md")
        if not os.path.isdir(d) or not os.path.exists(sk):
            continue
        meta = parse_front(sk)
        out[name] = {
            "name": meta.get("name") or name,
            "triggers": _derive_triggers(meta),
            "description": str(meta.get("description") or "").strip(),
            "version": str(meta.get("version") or "0.0.0"),
            "agent_created": bool(meta.get("agent_created")),
            "path": sk.replace("\\", "/"),
            "has_scripts": os.path.exists(os.path.join(d, "scripts")),
            "has_references": os.path.exists(os.path.join(d, "references")),
        }
    return out


def routes(root=ROOT):
    """Map trigger words (lower case) to skill names, and report duplicates."""
    table, conflicts = {}, []
    for name, meta in scan(root).items():
        for t in meta["triggers"]:
            key = t.strip().lower()
            if not key:
                continue
            if key in table and table[key] != name:
                conflicts.append((key, table[key], name))
            else:
                table[key] = name
    return table, conflicts


def lookup(words, root=ROOT):
    """Trigger words found in the user's wording to the matching skill names,
    order preserving and deduplicated. For debugging reference only."""
    table, _ = routes(root)
    low = (words or "").lower()
    hits = []
    for trigger, name in sorted(table.items(), key=lambda kv: -len(kv[0])):
        if trigger in low and name not in hits:
            hits.append(name)
    return hits


def report(root=ROOT):
    items = scan(root)
    table, conflicts = routes(root)
    lines = ["%d skills, %d triggers (host routes by description)" %
             (len(items), len(table))]
    for name, meta in items.items():
        lines.append("  %-22s v%-7s %s" %
                     (name, meta["version"],
                      ", ".join(meta["triggers"]) or "(no triggers)"))
        lines.append("      %s" % meta["path"])
    if conflicts:
        lines.append("CONFLICTS:")
        for key, a, b in conflicts:
            lines.append("  '%s' claimed by %s and %s" % (key, a, b))
    else:
        lines.append("conflicts: none")
    return "\n".join(lines)
