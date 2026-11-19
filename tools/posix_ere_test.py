#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Work out a secret-scan pattern that behaves, using git grep itself.

The CI job runs `git grep -niE`, which is POSIX ERE and case insensitive.
Python's `re` is a different dialect: `[[:space:]]` works in ERE but not in
`re`, and `\\s` works in `re` but not in ERE. Testing a pattern with the
wrong engine is how a rule ends up silently matching nothing.

So the candidates are checked here by running the real command the CI job
runs, against a staged probe file.

Run it after changing the pattern in .github/workflows/ci.yml.
"""
import os
import subprocess
import sys

LOCAL_PATHS = r"C:\\Users|/Users/|/home/[a-z]|AppData"
PRIVATE_KEY = r"BEGIN [A-Z ]*PRIVATE KEY"
# A credential that is hardcoded is almost always a known token format.
KNOWN_PREFIX = (r"(ghp_|gho_|ghu_|ghs_|ghr_|github_pat_|glpat-|xox[baprs]-|"
                r"sk-[A-Za-z0-9]|AKIA|AIza|ASIA)[A-Za-z0-9_+./-]{10,}")
# A name followed by a quoted string of some length. The quotes matter: they
# separate a literal from a call such as compute_secret().
QUOTED = (r"(password|passwd|secret|token|api[_-]?key|credential|auth)"
          r"[a-zA-Z_-]*[[:space:]]*[:=][[:space:]]*"
          r"[\"'][^\"'\s]{8,}[\"']")

PATTERNS = {
    "full": "(%s|%s|%s|%s)" % (LOCAL_PATHS, PRIVATE_KEY, KNOWN_PREFIX,
                                QUOTED),
}

CASES = [
    ('API_KEY = "sk-abcdef1234567890abcdef"', True, "hardcoded api key"),
    ('password = "hunter2000xyz"', True, "hardcoded password"),
    ('token: ghp_abcdefghijklmnopqrstuvwxyz012345', True, "bearer token"),
    ('-----BEGIN RSA PRIVATE KEY-----', True, "private key block"),
    ('secret = "AKIAIOSFODNN7EXAMPLE"', True, "aws key"),
    ('for line in out.stdout.splitlines():\n'
     '    if line.startswith("password="):\n'
     '        return line[len("password="):]',
     False, "code parsing a credential"),
    ('# the password is read from the git credential store',
     False, "the word in prose"),
    ('secret = compute_secret()', False, "a call, not a literal"),
    ('auth_token = os.environ["TOKEN"]', False, "read from the environment"),
    ('C:/Users/dell/AppData/Local/ffmpeg.exe', True, "a local path"),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join("tools", "_scan_probe.py")


def git_grep(pattern, paths):
    """Run the same command the CI job runs."""
    cmd = ["git", "grep", "-niE", pattern, "--"] + paths
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return proc.stdout.strip()


def probe(pattern, text):
    """Stage a probe file and see whether the pattern finds it."""
    full = os.path.join(ROOT, PROBE)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    subprocess.run(["git", "add", "-f", PROBE], cwd=ROOT,
                   capture_output=True, text=True)
    try:
        return bool(git_grep(pattern, [PROBE]))
    finally:
        subprocess.run(["git", "rm", "--cached", "-f", PROBE], cwd=ROOT,
                       capture_output=True, text=True)
        try:
            os.remove(full)
        except OSError:
            pass


def main():
    ok = True
    for name, pat in PATTERNS.items():
        failures = []
        for text, want_caught, desc in CASES:
            got = probe(pat, text)
            if got != want_caught:
                failures.append("%s (want %s, got %s)" % (
                    desc, "caught" if want_caught else "clean",
                    "caught" if got else "clean"))
        print("pattern %s: %s" % (name, "PASS" if not failures else "fail"))
        for f in failures:
            print("    %s" % f)
        ok = ok and not failures
    print()
    print("the pattern to use in the workflow:")
    print(PATTERNS["full"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
