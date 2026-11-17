# -*- coding: utf-8 -*-
"""扫描 skills/ 下的标准 skill，汇总成便于查看与调试的清单。

**真正的路由由宿主 Agent 完成**：宿主读取每个 skill 的 `description`（何时使用），
按用户原话做语义判断，命中后直接加载对应 SKILL.md。这里的 `triggers` 字段只是
可选的加速索引与调试辅助，不再是运行时唯一依据；缺 triggers 时从 description
抽取关键词兜底，保证新 skill 不写 triggers 也能被发现。
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
    """没有 triggers 字段时，从 description 里抽中文关键词兜底。"""
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
    """触发词（小写）到 skill 名的映射，并返回重复触发词的冲突列表。"""
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
    """用户原话里出现的触发词 -> 命中的 skill 名，保序去重。仅供调试参考。"""
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
