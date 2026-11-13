# -*- coding: utf-8 -*-
"""从各 effect 的 SKILL.md frontmatter 汇总路由表。

路由表不再写在根 SKILL.md 里：多人并行新增特效时，每个人只改自己目录的
triggers 字段，就不会在同一张共享文件上冲突。
"""
import io
import os
import re

import yaml

FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
SKIP_PREFIX = ("_", ".")


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


def scan(root="effects"):
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
            "triggers": [str(x).strip() for x in (meta.get("triggers") or [])],
            "description": str(meta.get("description") or "").strip(),
            "version": str(meta.get("version") or "0.0.0"),
            "path": sk.replace("\\", "/"),
        }
    return out


def routes(root="effects"):
    """触发词（小写）到 effect 名的映射，并返回重复触发词的冲突列表。"""
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


def lookup(words, root="effects"):
    """用户原话里出现的触发词 -> 命中的 effect 名，保序去重。"""
    table, _ = routes(root)
    low = (words or "").lower()
    hits = []
    for trigger, name in sorted(table.items(), key=lambda kv: -len(kv[0])):
        if trigger in low and name not in hits:
            hits.append(name)
    return hits


def report(root="effects"):
    items = scan(root)
    table, conflicts = routes(root)
    lines = ["%d effects, %d triggers" % (len(items), len(table))]
    for name, meta in items.items():
        lines.append("  %-22s v%-7s %s" %
                     (name, meta["version"], ", ".join(meta["triggers"]) or "(no triggers)"))
        lines.append("      %s" % meta["path"])
    if conflicts:
        lines.append("CONFLICTS:")
        for key, a, b in conflicts:
            lines.append("  '%s' claimed by %s and %s" % (key, a, b))
    else:
        lines.append("conflicts: none")
    return "\n".join(lines)
