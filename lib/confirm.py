# -*- coding: utf-8 -*-
"""Render gate: a plan must be confirmed by the user before it can be rendered.

Why this exists
---------------
AICUT is an agent skill, not a batch tool. The agent must ask the user how to
cut before burning compute or producing a video the user did not ask for. A
prose instruction ("please ask the user first") is not enforceable, because
the agent is the one reading it.

So the gate lives in code instead:

  1. `plan` writes plan.json plus a `confirmation` block. The block records the
     plan's content hash and the questions that still need an answer.
  2. `render` refuses to run unless a confirmation exists and its hash still
     matches the current plan.
  3. `confirm` is the only thing that writes a valid confirmation. It can only
     be run with the plan hash printed by `plan`, so the agent has to surface
     that hash to the user and come back with the user's answer.

An agent that skips the conversation cannot render: it would have to invent a
hash, and the plan it invented it for is not the plan on disk.
"""
import datetime
import hashlib
import json
import os

CONFIRM_KEY = "confirmation"


def plan_hash(plan):
    """Content hash of the parts of a plan that affect the rendered output.

    The confirmation block itself is excluded, otherwise confirming would
    change the hash and invalidate the confirmation.
    """
    payload = {
        "project": plan.get("project"),
        "shots": plan.get("shots"),
        "beat_frames": plan.get("beat_frames"),
        "repeat_ratio": plan.get("repeat_ratio"),
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def questions(plan, cfg=None):
    """Questions the agent must put to the user before rendering.

    Kept deliberately short and answerable: the user is being asked to approve
    a cut, not to configure a renderer.
    """
    shots = plan.get("shots") or []
    effects = []
    for sh in shots:
        if sh.get("effect") not in effects:
            effects.append(sh.get("effect"))
    dur = float((plan.get("project") or {}).get("duration") or 0.0)
    q = []
    if effects:
        q.append("Which effects should be used? Plan uses: %s"
                 % ", ".join(str(e) for e in effects))
    q.append("Target duration: %.2fs. Keep it, or change it?" % dur)
    q.append("Which part of the music should the cut follow? "
             "(e.g. start at the drop, or from the first beat)")
    q.append("Any look you do not want? (e.g. too dark, too blurry, "
             "too repetitive)")
    return q


def stamp():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def write_plan(path, plan, cfg=None):
    """Write plan.json with a fresh, unconfirmed confirmation block."""
    plan = dict(plan)
    plan[CONFIRM_KEY] = {
        "status": "pending",
        "plan_hash": plan_hash(plan),
        "questions": questions(plan, cfg),
        "requested_at": stamp(),
        "confirmed_at": None,
        "confirmed_hash": None,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
    return plan


def read_plan(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def confirm(path, plan_hash_value, note=None):
    """Mark a plan as confirmed. Returns the updated confirmation block."""
    plan = read_plan(path)
    block = plan.get(CONFIRM_KEY) or {}
    current = plan_hash(plan)
    if plan_hash_value and plan_hash_value != current:
        raise SystemExit(
            "plan hash mismatch.\n"
            "  on disk : %s\n"
            "  given   : %s\n"
            "The plan changed since it was proposed. Re-run plan, then ask the "
            "user again." % (current, plan_hash_value))
    block = dict(block)
    block["status"] = "confirmed"
    block["confirmed_at"] = stamp()
    block["confirmed_hash"] = current
    if note:
        block["note"] = note
    plan[CONFIRM_KEY] = block
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
    return block


def check(path):
    """Return (ok, plan, message). ok is False when rendering must not proceed."""
    if not os.path.exists(path):
        return False, None, "plan.json missing: %s" % path
    try:
        plan = read_plan(path)
    except Exception as exc:                                    # noqa: BLE001
        return False, None, "plan.json unreadable: %s" % exc
    block = plan.get(CONFIRM_KEY)
    if not block:
        return False, plan, (
            "plan has no confirmation block. This plan was produced by an "
            "older version; re-run `plan` to get a confirmable plan.")
    if block.get("status") != "confirmed":
        return False, plan, (
            "plan is not confirmed yet.\n"
            "Ask the user these questions first, then run:\n"
            "  python aicut.py confirm --run <id> --hash %s\n"
            % block.get("plan_hash"))
    if block.get("confirmed_hash") != plan_hash(plan):
        return False, plan, (
            "plan changed after it was confirmed (hash %s != %s).\n"
            "Re-run plan, ask the user again, then confirm."
            % (block.get("confirmed_hash"), plan_hash(plan)))
    return True, plan, "confirmed at %s" % block.get("confirmed_at")
