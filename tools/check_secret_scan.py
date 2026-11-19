#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run the secret scan exactly as the CI job does, and prove it still works.

The pattern in the workflow is POSIX ERE. A pattern that matches nothing
looks exactly like a clean tree, so this script stages probe files and runs
the same git grep against them: a hardcoded credential has to be caught, and
code that merely handles a credential has to stay clean.

Run it after changing the pattern in .github/workflows/ci.yml.
"""
import os
import subprocess
import sys

PATTERN = (
    r"(C:\\Users|/Users/|/home/[a-z]|AppData|BEGIN [A-Z ]*PRIVATE KEY"
    r"|(ghp_|gho_|ghu_|ghs_|ghr_|github_pat_|glpat-|xox[baprs]-|"
    r"sk-[A-Za-z0-9]|AKIA|AIza|ASIA)[A-Za-z0-9_+./-]{10,}"
    r"|(password|passwd|secret|token|api[_-]?key|credential|auth)"
    r"[a-zA-Z_-]*[[:space:]]*[:=][[:space:]]*[\"'][^\"'\s]{8,}[\"'])"
)

EXCLUDE = [":(exclude)docs/demo/*",
           ":(exclude).github/workflows/*",
           ":(exclude)tools/posix_ere_test.py",
           ":(exclude)tools/check_secret_scan.py"]

MUST_CATCH = [
    ("a hardcoded api key", 'API_KEY = "sk-abcdef1234567890abcdef"'),
    ("a hardcoded password", 'password = "hunter2000xyz"'),
    ("a github token", "token: ghp_abcdefghijklmnopqrstuvwxyz012345"),
    ("an aws key", 'secret = "AKIAIOSFODNN7EXAMPLE"'),
    ("a private key block", "-----BEGIN RSA PRIVATE KEY-----"),
    ("a local path", "C:/Users/dell/AppData/Local/ffmpeg.exe"),
]

MUST_NOT_CATCH = [
    ("code parsing a credential",
     'for line in out.stdout.splitlines():\n'
     '    if line.startswith("password="):\n'
     '        return line[len("password="):]'),
    ("the word in prose",
     "# the password is read from the git credential store"),
    ("a call, not a literal", "secret = compute_secret()"),
    ("read from the environment", 'auth_token = os.environ["TOKEN"]'),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROBE = os.path.join("tools", "_scan_probe.py")


def git_grep(paths):
    """Run the same command the CI job runs."""
    cmd = ["git", "grep", "-niE", PATTERN, "--"] + paths + EXCLUDE
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return proc.stdout.strip()


def probe(text):
    """Stage a probe file and see whether the pattern finds it."""
    full = os.path.join(ROOT, PROBE)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    subprocess.run(["git", "add", "-f", PROBE], cwd=ROOT,
                   capture_output=True, text=True)
    try:
        return bool(git_grep([PROBE]))
    finally:
        subprocess.run(["git", "rm", "--cached", "-f", PROBE], cwd=ROOT,
                       capture_output=True, text=True)
        try:
            os.remove(full)
        except OSError:
            pass


def main():
    problems = []

    print("--- the current tree must be clean ---")
    hits = git_grep(["."])
    if hits:
        print("  PROBLEM  the tree has a hit")
        for line in hits.splitlines():
            print("            %s" % line)
        problems.append("the tree has a hit")
    else:
        print("  OK       clean")

    print()
    print("--- the scan must still catch a real leak ---")
    for desc, body in MUST_CATCH:
        if probe(body):
            print("  OK       %s (caught, as required)" % desc)
        else:
            print("  PROBLEM  %s was not caught" % desc)
            problems.append(desc)

    print()
    print("--- code that is not a leak must stay clean ---")
    for desc, body in MUST_NOT_CATCH:
        if probe(body):
            print("  PROBLEM  %s was flagged" % desc)
            problems.append(desc)
        else:
            print("  OK       %s (not flagged, as required)" % desc)

    print()
    if problems:
        print("%d problem(s)" % len(problems))
        return 1
    print("the secret scan behaves as required")
    return 0


if __name__ == "__main__":
    sys.exit(main())
