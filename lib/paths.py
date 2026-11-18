# -*- coding: utf-8 -*-
"""Where a skill lives on disk.

Two layouts exist and the kernel has to work with both:

  Repository layout
      skills/<name>/SKILL.md
      Several skills live side by side. This is the development layout and the
      one the installer copies from.

  Packaged layout
      SKILL.md at the root, next to lib/ and aicut.py
      A marketplace install unpacks one skill together with the kernel, so the
      skill sits at the root. This is what a user gets after installing from a
      skill market.

Every module that needs to find a skill goes through here, so the two layouts
never diverge.
"""
import os

SKILLS_DIR = "skills"
# A skill at the root is detected by its references/params.yaml.
ROOT_MARKER = os.path.join("references", "params.yaml")


def is_root_layout():
    """True when the current directory holds a single skill at its root."""
    return os.path.exists(ROOT_MARKER)


def skills_root():
    """The directory that holds skill folders, or None in the packaged layout."""
    if is_root_layout():
        return None
    if os.path.isdir(SKILLS_DIR):
        return SKILLS_DIR
    return None


def skill_dir(effect_id):
    """Absolute or relative path to a skill directory, or None when unknown."""
    if not effect_id or effect_id == "base":
        return None
    nested = os.path.join(SKILLS_DIR, effect_id)
    if os.path.isdir(nested):
        return nested
    if is_root_layout():
        # In the packaged layout there is exactly one skill, and it may be
        # addressed by its directory name or by the name in its frontmatter.
        root_name = _root_skill_name()
        if root_name and (root_name == effect_id or
                          root_name.endswith("-" + effect_id)):
            return "."
    return None


def _root_skill_name():
    """The name declared in the frontmatter of the root-layout skill."""
    import io
    import re
    p = "SKILL.md"
    if not os.path.exists(p):
        return None
    text = io.open(p, "r", encoding="utf-8").read()
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return None
    try:
        import yaml
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return None
    return str(meta.get("name") or "") or None


def resolves_to(effect_id):
    """True when effect_id addresses a discoverable skill in either layout."""
    if not effect_id or effect_id == "base":
        return False
    if os.path.isdir(os.path.join(SKILLS_DIR, effect_id)):
        return True
    if is_root_layout():
        root_name = _root_skill_name()
        return bool(root_name) and (root_name == effect_id or
                                    root_name.endswith("-" + effect_id))
    return False


def list_skills():
    """Names of every discoverable skill, sorted."""
    root = skills_root()
    if root is None:
        if is_root_layout():
            import re
            import io
            p = os.path.join("SKILL.md")
            if os.path.exists(p):
                text = io.open(p, "r", encoding="utf-8").read()
                m = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
                if m:
                    try:
                        import yaml
                        meta = yaml.safe_load(m.group(1)) or {}
                        return [str(meta.get("name") or "skill")]
                    except yaml.YAMLError:
                        pass
            return []
        return []
    out = []
    for name in sorted(os.listdir(root)):
        if name.startswith(("_", ".")):
            continue
        if os.path.isdir(os.path.join(root, name)):
            out.append(name)
    return out


def build_script(effect_id):
    """Path to a skill's build.py, or None."""
    d = skill_dir(effect_id)
    if not d:
        return None
    p = os.path.join(d, "scripts", "build.py")
    return p if os.path.exists(p) else None


def skill_md(effect_id):
    """Path to a skill's SKILL.md, or None."""
    d = skill_dir(effect_id)
    if not d:
        return None
    p = os.path.join(d, "SKILL.md")
    return p if os.path.exists(p) else None


def references_dir(effect_id):
    """Path to a skill's references directory, or None."""
    d = skill_dir(effect_id)
    if not d:
        return None
    p = os.path.join(d, "references")
    return p if os.path.isdir(p) else None
