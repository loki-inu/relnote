#!/usr/bin/env bash
# release.sh: cut a release locally from conventional commits, the way
# `npx standard-version` did (bump, CHANGELOG.md, commit, tag), with relnote.
#
#   examples/release.sh                    # next version from commits
#   examples/release.sh --dry-run          # show version, files, and notes only
#   examples/release.sh --release-as v2.0.0
#   examples/release.sh --bump-file package.json --bump-file pyproject.toml
#   examples/release.sh --tag-prefix api/v -- --path packages/api
#
# Needs bash, git, Python 3.11+ and relnote on PATH (or RELNOTE="python3 relnote.pyz").
# Docs: https://loki-inu.github.io/relnote/standard-version-alternative.html
set -euo pipefail

usage() {
  cat <<'USAGE'
usage: release.sh [options] [-- relnote flags]

  --release-as TAG     use TAG instead of relnote --next-version
  --changelog FILE     changelog to prepend to (default: CHANGELOG.md)
  --bump-file FILE     set the first "version" value in FILE (package.json,
                       pyproject.toml, Cargo.toml, ...); repeatable
  --tag-prefix PREFIX  monorepo tag prefix, passed to relnote (e.g. api/v)
  --skip-commit        update files but do not commit (implies --skip-tag)
  --skip-tag           commit but do not tag
  --dry-run            print what would happen; change nothing
  -h, --help           show this help

Anything after -- goes to every relnote call (e.g. --path packages/api).
Nothing is pushed. Afterwards: git push --follow-tags
USAGE
}

RELNOTE_CMD=${RELNOTE:-relnote}
read -r -a RELNOTE_BIN <<<"$RELNOTE_CMD"

release_as=""
changelog="CHANGELOG.md"
bump_files=()
tag_prefix=""
skip_commit=0
skip_tag=0
dry_run=0
extra=()

while [ $# -gt 0 ]; do
  case "$1" in
    --release-as) release_as=${2:?--release-as needs a tag}; shift 2 ;;
    --changelog) changelog=${2:?--changelog needs a file}; shift 2 ;;
    --bump-file) bump_files+=("${2:?--bump-file needs a file}"); shift 2 ;;
    --tag-prefix) tag_prefix=${2:?--tag-prefix needs a prefix}; shift 2 ;;
    --skip-commit) skip_commit=1; skip_tag=1; shift ;;
    --skip-tag) skip_tag=1; shift ;;
    --dry-run) dry_run=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; extra=("$@"); break ;;
    *) echo "release.sh: unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

die() { echo "release.sh: $*" >&2; exit 1; }

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repository"
if [ "$dry_run" -eq 0 ] && [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  die "working tree has uncommitted changes; commit or stash them first"
fi

rn=("${RELNOTE_BIN[@]}")
[ -n "$tag_prefix" ] && rn+=(--tag-prefix "$tag_prefix")
rn+=("${extra[@]+"${extra[@]}"}")

if [ -z "$release_as" ] && [ -n "$(git tag --points-at HEAD --list "${tag_prefix}*")" ]; then
  die "HEAD is already tagged ($(git tag --points-at HEAD --list "${tag_prefix}*" | head -n 1)); nothing to release"
fi

if [ -n "$release_as" ]; then
  next=$release_as
else
  next=$("${rn[@]}" --next-version) || die "relnote --next-version failed (nothing to release?)"
fi
case "$next" in
  "$tag_prefix"*) ;;
  *) die "tag $next does not start with --tag-prefix $tag_prefix" ;;
esac
if git rev-parse -q --verify "refs/tags/$next" >/dev/null; then
  die "tag $next already exists"
fi

# Version number without the tag prefix or a leading v (v1.4.0 -> 1.4.0).
number=${next#"$tag_prefix"}
number=${number#v}

echo "next: $next"
echo "changelog: $changelog"
for f in "${bump_files[@]+"${bump_files[@]}"}"; do
  [ -f "$f" ] || die "--bump-file $f: no such file"
  echo "bump: $f -> $number"
done

if [ "$dry_run" -eq 1 ]; then
  echo "commit: $([ "$skip_commit" -eq 1 ] && echo skipped || echo "chore(release): $next")"
  echo "tag: $([ "$skip_tag" -eq 1 ] && echo skipped || echo "$next")"
  echo "--- notes ---"
  "${rn[@]}"
  exit 0
fi

for f in "${bump_files[@]+"${bump_files[@]}"}"; do
  python3 - "$f" "$number" <<'PY'
import re, sys
path, number = sys.argv[1], sys.argv[2]
# newline="" keeps the file's own line endings (LF or CRLF) on every OS.
text = open(path, encoding="utf-8", newline="").read()
# First "version": "x" (JSON) or version = "x" (TOML), at line start.
pattern = re.compile(r'^(\s*"?version"?\s*[:=]\s*")([^"]*)(")', re.MULTILINE)
new, count = pattern.subn(lambda m: m.group(1) + number + m.group(3), text, count=1)
if not count:
    sys.exit(f"release.sh: no version line found in {path}")
open(path, "w", encoding="utf-8", newline="").write(new)
PY
done

"${rn[@]}" --changelog "$changelog" --changelog-title "$next" --quiet

if [ "$skip_commit" -eq 1 ]; then
  echo "updated files; not committed (--skip-commit)"
  exit 0
fi

git add -- "$changelog" "${bump_files[@]+"${bump_files[@]}"}"
git commit -q -m "chore(release): $next"
echo "committed: chore(release): $next"

if [ "$skip_tag" -eq 0 ]; then
  git tag -a "$next" -m "$next"
  echo "tagged: $next"
fi
echo "next step: git push --follow-tags"
