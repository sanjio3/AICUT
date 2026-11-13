# -*- coding: utf-8 -*-
"""ffmpeg 调用面：${ENV:-default} 展开、超时重试、编码封装。"""
import io
import os
import re
import subprocess

ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def load_dotenv(cfg_path):
    """轻量读取与配置文件同目录的 .env，不引入 python-dotenv。
    已存在的进程环境变量优先，CI 注入的值不会被本机文件覆盖。"""
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
    """前台执行，超时重试。失败时把 ffmpeg 尾部错误抛出来，不静默吞掉。"""
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
    """逐镜统一出口。-t 限时保证片段长度严格等于 plan 给的 dur。"""
    pr = cfg["project"]
    cmd = [ffmpeg, "-y", "-v", "error"] + [str(x) for x in inputs]
    cmd += ["-filter_complex", fc, "-map", "[out]",
            "-t", "%.4f" % dur, "-r", str(pr["fps"]),
            "-c:v", "libx264", "-crf", str(pr["crf"]),
            "-preset", pr.get("preset", "medium"),
            "-pix_fmt", "yuv420p", "-an", str(out)]
    run(cmd)
    return out
