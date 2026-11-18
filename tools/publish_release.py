# -*- coding: utf-8 -*-
"""Publish the skill packages as GitHub release assets.

One release per version. Re-running this script after a change replaces the
archives in place: an asset with the same name is deleted and uploaded
again, so the download URLs stay valid and a listing never accumulates
stale copies.

Usage:
  python tools/publish_release.py --tag v0.4.0
  python tools/publish_release.py --tag v0.4.0 --dry-run
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.github.com"
REPO = "sanjio3/AICUT"
DIST = os.path.join(ROOT, "dist")


def token():
    """Read the stored GitHub credential without printing it."""
    out = subprocess.run(
        ["git", "-c", "credential.interactive=false", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n", capture_output=True,
        text=True, cwd=ROOT)
    for line in out.stdout.splitlines():
        if line.startswith("password="):
            return line[len("password="):]
    raise SystemExit("no stored GitHub credential")


TOK = None


def api(method, path, payload=None, tries=4, timeout=600,
        allow_404=False):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    for i in range(tries):
        req = urllib.request.Request(API + path, data=data, method=method)
        req.add_header("Authorization", "Bearer " + TOK)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "aicut-publish")
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            if e.code == 404 and allow_404:
                return {}
            if e.code in (500, 502, 503, 504) and i + 1 < tries:
                time.sleep(2 + i * 2)
                continue
            raise SystemExit("%s %s -> %s\n%s" % (method, path, e.code, msg[:600]))
        except Exception as exc:                                # noqa: BLE001
            if i + 1 < tries:
                time.sleep(2 + i * 2)
                continue
            raise SystemExit("%s %s -> %r" % (method, path, exc))


def upload_asset(release_id, path, dry_run=False):
    """Upload one archive, replacing an asset of the same name."""
    name = os.path.basename(path)
    existing = api("GET", "/repos/%s/releases/%s/assets" % (REPO, release_id))
    old = None
    for a in existing if isinstance(existing, list) else []:
        if a["name"] == name:
            old = a
            break
    if old:
        print("  replace %s (id=%d, %d bytes)" %
              (name, old["id"], old["size"]))
        if not dry_run:
            api("DELETE", "/repos/%s/releases/assets/%d" % (REPO, old["id"]))
    else:
        print("  upload %s" % name)
    if dry_run:
        return
    # The asset name goes in the query string. Without it the upload host
    # tries to infer a name from the request and answers "Invalid name for
    # request".
    url = ("https://uploads.github.com/repos/%s/releases/%s/assets?name=%s"
           % (REPO, release_id, urllib.parse.quote(name)))
    with open(path, "rb") as fh:
        payload = fh.read()

    # The upload host is reached through a proxy on this machine, so the
    # connection drops from time to time. A retry costs nothing.
    last = None
    for attempt in range(4):
        req = urllib.request.Request(url, data=payload, method="POST")
        req.add_header("Authorization", "Bearer " + TOK)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "aicut-publish")
        req.add_header("Content-Type", "application/zip")
        req.add_header("Content-Length", str(len(payload)))
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                body = r.read().decode("utf-8")
                print("    ok, %d bytes" % len(payload))
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            if e.code in (500, 502, 503, 504) and attempt < 3:
                last = "HTTP %s" % e.code
                time.sleep(3 + attempt * 3)
                continue
            raise SystemExit("upload %s -> %s\n%s" % (name, e.code, msg[:600]))
        except Exception as exc:                                # noqa: BLE001
            last = repr(exc)
            if attempt < 3:
                time.sleep(3 + attempt * 3)
                continue
            raise SystemExit("upload %s -> %s" % (name, last))
    raise SystemExit("upload %s failed after 4 attempts: %s" % (name, last))


def main():
    global TOK
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="release tag, for example v0.4.0")
    ap.add_argument("--title", default=None)
    ap.add_argument("--notes-file", default=None,
                    help="markdown file with the release notes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-assets", action="store_true",
                    help="create the release but skip the archives")
    a = ap.parse_args()

    TOK = token()

    notes = ""
    if a.notes_file and os.path.exists(a.notes_file):
        with open(a.notes_file, "r", encoding="utf-8") as fh:
            notes = fh.read()
    if not notes:
        notes = "Skill packages for AICUT.\n\nSee the README for usage."

    title = a.title or a.tag

    # Find the release by tag, create it when it does not exist yet.
    rel = api("GET", "/repos/%s/releases/tags/%s" % (REPO, a.tag),
              allow_404=True)
    if not rel.get("id"):
        print("create release %s" % a.tag)
        if a.dry_run:
            print("  (dry-run, not created)")
            return 0
        rel = api("POST", "/repos/%s/releases" % REPO, {
            "tag_name": a.tag,
            "name": title,
            "body": notes,
            "draft": False,
            "prerelease": False,
        })
    else:
        print("update release %s" % a.tag)
        if not a.dry_run:
            api("PATCH", "/repos/%s/releases/%s" % (REPO, rel["id"]),
                {"name": title, "body": notes,
                 "draft": False, "prerelease": False})
    print("  url: %s" % rel.get("html_url"))

    if a.no_assets:
        return 0

    files = sorted(glob.glob(os.path.join(DIST, "*.zip")))
    if not files:
        raise SystemExit("no archives in %s, run: python aicut.py package --market"
                         % DIST)
    print("assets (%d):" % len(files))
    for f in files:
        upload_asset(rel["id"], f, dry_run=a.dry_run)

    if not a.dry_run:
        final = api("GET", "/repos/%s/releases/tags/%s" % (REPO, a.tag))
        print()
        print("release: %s" % final.get("html_url"))
        for asset in final.get("assets", []):
            print("  %-46s %8d bytes  %s" %
                  (asset["name"], asset["size"], asset["browser_download_url"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
