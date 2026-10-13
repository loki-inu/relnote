#!/usr/bin/env bash
# Smoke-test a built single-file relnote (default: dist/relnote).
#
#   scripts/smoke-zipapp.sh [path/to/relnote] [expected-version]
#
# Checks --version, then generates notes and --next-version in a throwaway
# git repository that lives outside the source tree.
set -euo pipefail

bin="$(cd "$(dirname "${1:-dist/relnote}")" && pwd)/$(basename "${1:-dist/relnote}")"
expected="${2:-}"

echo "== $bin --version"
version="$("$bin" --version)"
echo "$version"
if [ -n "$expected" ] && [ "$version" != "relnote $expected" ]; then
  echo "expected 'relnote $expected'" >&2
  exit 1
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
repo="$work/repo"
mkdir -p "$repo"
cd "$repo"
export GIT_AUTHOR_NAME="Ada Lovelace" GIT_AUTHOR_EMAIL="ada@example.com"
export GIT_COMMITTER_NAME="Ada Lovelace" GIT_COMMITTER_EMAIL="ada@example.com"
git init -q --initial-branch=main
git -c commit.gpgsign=false commit -q --allow-empty -m "feat: first release"
git tag v1.0.0
git -c commit.gpgsign=false commit -q --allow-empty -m "fix(cli): handle empty ranges"
git -c commit.gpgsign=false commit -q --allow-empty -m "feat: add --next-version"

echo "== notes (cwd = temp repo)"
notes="$("$bin")"
printf '%s\n' "$notes"
grep -q '^### Features' <<<"$notes"
grep -q 'add --next-version' <<<"$notes"
grep -q 'handle empty ranges' <<<"$notes"
# shellcheck disable=SC2016  # the backticks are literal markdown from relnote
grep -qF 'Range: `v1.0.0`' <<<"$notes"

echo "== --next-version (cwd = elsewhere, --repo)"
cd "$work"
next="$("$bin" --repo "$repo" --next-version)"
echo "$next"
[ "$next" = "v1.1.0" ]

echo "smoke test passed"
