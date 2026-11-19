#!/usr/bin/env bash
# Run the secret scan exactly as the CI job does, and prove it still catches a
# hardcoded credential.
#
# The pattern in the workflow is POSIX ERE. A pattern that matches nothing
# looks exactly like a clean tree, so this script also stages a probe with a
# real-looking secret and checks that the scan finds it.
set -u
cd "$(dirname "$0")/.."

PAT='(C:\\Users|/Users/|/home/[a-z]|AppData|BEGIN [A-Z ]*PRIVATE KEY|(ghp_|gho_|ghu_|ghs_|ghr_|github_pat_|glpat-|xox[baprs]-|sk-[A-Za-z0-9]|AKIA|AIza|ASIA)[A-Za-z0-9_+./-]{10,}|(password|passwd|secret|token|api[_-]?key|credential|auth)[a-zA-Z_-]*[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'\s]{8,}["'"'"'])'

EXCL=(":(exclude)docs/demo/*" ":(exclude).github/workflows/*"
      ":(exclude)tools/posix_ere_test.py"
      ":(exclude)tools/check_secret_scan.py")

probe() {
  local desc="$1" expect="$2" body="$3"
  local tmp="tools/_scan_probe.py"
  printf '%s\n' "$body" > "$tmp"
  git add -f "$tmp" >/dev/null 2>&1
  local out
  out=$(git grep -niE "$PAT" -- "$tmp" "${EXCL[@]}" 2>/dev/null || true)
  git rm --cached -f "$tmp" >/dev/null 2>&1
  rm -f "$tmp"
  if [ -n "$out" ]; then
    if [ "$expect" = "caught" ]; then
      echo "  OK       $desc (caught, as required)"
    else
      echo "  PROBLEM  $desc was flagged but should not be"
      echo "$out" | sed 's/^/            /'
    fi
  else
    if [ "$expect" = "caught" ]; then
      echo "  PROBLEM  $desc was not caught, a real leak would slip through"
    else
      echo "  OK       $desc (not flagged, as required)"
    fi
  fi
}

echo "--- the current tree must be clean ---"
if git grep -niE "$PAT" -- . "${EXCL[@]}"; then
  echo "  PROBLEM  the tree has a hit"
else
  echo "  OK       clean"
fi

echo
echo "--- the scan must still catch a real leak ---"
probe "a hardcoded api key" caught \
'API_KEY = "sk-abcdef1234567890abcdef"'
probe "a hardcoded password" caught \
'password = "hunter2000xyz"'
probe "a github token" caught \
'token: ghp_abcdefghijklmnopqrstuvwxyz012345'
probe "an aws key" caught \
'secret = "AKIAIOSFODNN7EXAMPLE"'
probe "a private key block" caught \
'-----BEGIN RSA PRIVATE KEY-----'
probe "a local path" caught \
'C:/Users/dell/AppData/Local/ffmpeg.exe'

echo
echo "--- code that is not a leak must stay clean ---"
probe "code parsing a credential" not-caught \
'for line in out.stdout.splitlines():
    if line.startswith("password="):
        return line[len("password="):]'
probe "the word in prose" not-caught \
'# the password is read from the git credential store'
probe "a call, not a literal" not-caught \
'secret = compute_secret()'
probe "read from the environment" not-caught \
'auth_token = os.environ["TOKEN"]'
