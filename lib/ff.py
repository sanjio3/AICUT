# -*- coding: utf-8 -*-
"""ffmpeg invocation layer: ${ENV:-default} expansion, timeout retry, encoding."""
import io
import os
import re
import subprocess

ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def load_dotenv(cfg_path):
    """Read a .env file next to the config without pulling in python-dotenv.
    Environment variables that already exist win, so CI-injected values are
    never overridden by a local file."""
    path = os.path.join(os.path.dirname(os.path.abspath(cfg_path)), ".env")
    if not os.path.exists(path):
        return
    with io.open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip().strip('"').strip("'")
            if value:
                os.environ[key] = value


def expand(value, extra=None):
    if not isinstance(value, str):
        return value

    def sub(m):
        key, default = m.group(1), m.group(2)
        val = (extra or {}).get(key) or os.environ.get(key)
        return str(val) if val is not None else (default or "")

    return ENV_RE.sub(sub, value)


def expand_tree(node, extra=None):
    if isinstance(node, dict):
        return {k: expand_tree(v, extra) for k, v in node.items()}
    if isinstance(node, list):
        return [expand_tree(v, extra) for v in node]
    return expand(node, extra)


def load_config(path="params.yaml"):
    import yaml
    load_dotenv(path)
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return expand_tree(cfg)


def run(cmd, timeout=300, tries=2, cwd=None):
    """Run in the foreground with retries. On failure the tail of the ffmpeg
    error is raised instead of being swallowed."""
    last = "unknown"
    for _ in range(tries):
        try:
            p = subprocess.run([str(x) for x in cmd],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               timeout=timeout, cwd=cwd)
        except subprocess.TimeoutExpired:
            last = "timeout after %ds" % timeout
            continue
        if p.returncode == 0:
            return p
        last = p.stderr.decode("utf-8", "ignore")[-1600:]
    raise RuntimeError("command failed: %s\n%s" %
                       (" ".join(str(x) for x in cmd[:10]), last))


def encode(ffmpeg, inputs, fc, out, dur, cfg):
    """Uniform per-shot output. -t guarantees the clip length equals the
    duration the plan asked for."""
    pr = cfg["project"]
    cmd = [ffmpeg, "-y", "-v", "error"] + [str(x) for x in inputs]
    cmd += ["-filter_complex", fc, "-map", "[out]",
            "-t", "%.4f" % dur, "-r", str(pr["fps"]),
            "-c:v", "libx264", "-crf", str(pr["crf"]),
            "-preset", pr.get("preset", "medium"),
            "-pix_fmt", "yuv420p", "-an", str(out)]
    run(cmd)
    return out
