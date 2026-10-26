# relnote

[![relnote on OSSDrop](https://ossdrop.com/badge/relnote)](https://ossdrop.com/tool/relnote)

Also listed in [awesome-release-management](https://github.com/miguelsalva/awesome-release-management) (Changelog Generators), [awesome-cli-apps-in-a-csv](https://github.com/toolleeo/awesome-cli-apps-in-a-csv) (git), [awesome-efficient-devtools](https://github.com/ejboy/awesome-efficient-devtools) (Fast CLI Tools), [git-extra-commands](https://github.com/unixorn/git-extra-commands) (External Git Utilities), [awesome-docs](https://github.com/testthedocs/awesome-docs) (GitHub Actions), [awesome-cli-tui-software](https://github.com/lgaggini/awesome-cli-tui-software) (git), [awesome-github](https://github.com/fffaraz/awesome-github) (Git), [awesome-devops](https://github.com/frimik/awesome-devops) (Command Line and Tooling), [awesome-versioning](https://github.com/quad/awesome-versioning) (Tools), [awesome-gh-extensions](https://github.com/myzkey/awesome-gh-extensions) (auto-updated gh CLI extensions, via [gh-relnote](https://github.com/loki-inu/gh-relnote)), [scoop.sh](https://scoop.sh/#/apps?q=relnote&o=false) app search (Windows, via [loki-inu/scoop-bucket](https://github.com/loki-inu/scoop-bucket)), and [conda-forge](https://anaconda.org/conda-forge/relnote) ([feedstock](https://github.com/conda-forge/relnote-feedstock); also on [prefix.dev](https://prefix.dev/channels/conda-forge/packages/relnote)).

Turn a git range into clean GitHub release notes.

```bash
python3 -m relnote
```

```markdown
## What's changed

### Breaking

- replace JSON store with SQLite (`a11a11a`) — Ada Lovelace, Sam Rivera
  - BREAKING CHANGE: harbor dump --json now writes NDJSON.

### Features

- **cli:** add harbor sync --dry-run (`b22b22b`) — Ada Lovelace
- import Netscape bookmark files (`c33c33c`) — Grace Hopper

### Fixes

- do not drop tags that contain commas (`d44d44d`) — Ada Lovelace
- **parser:** accept single-quoted hrefs (`e55e55e`) — Sam Rivera, Grace Hopper

### Other

- **docs:** document the XBEL importer (`f66f66f`) — Grace Hopper
- **refactor:** split store module from cli (`333cccc`) — Ada Lovelace
- Initial floating-window layout for the TUI (`555eeee`) — Sam Rivera

---

Range: `v0.9.0` → `v1.0.0`.

_3 commit(s) omitted (bots or secret-looking subjects)._
```

Synthetic example from a fake commit list for a fictional CLI called harbor — not taken from any real repository. See [samples/example-output.md](samples/example-output.md).

## Compared to `gh`, git-cliff, and swapnanil/relnotes

relnote is a stdlib Python changelog CLI (and GitHub Action) for offline conventional-commit release notes: no GitHub API, no config file. It groups commits into Features, Fixes, and Breaking.

Keep using `gh release create --generate-notes` when you want GitHub's official, PR-linked notes. Use [git-cliff](https://git-cliff.org/) when you want a full changelog file, Tera templates, and a config.

[swapnanil/relnotes](https://github.com/swapnanil/relnotes) is another stdlib Python conventional-commit notes CLI. Pick relnote for the GitHub Action and zero-config CI (`--quiet` / `--output`); pick that CLI if you want an optional `.relnotes.toml` or inferred semver bump.

Docs: https://loki-inu.github.io/relnote/ · Compare: https://loki-inu.github.io/relnote/compare.html · GitLab CI / Jenkins / any CI: https://loki-inu.github.io/relnote/ci.html · Monorepo (per-package tags): https://loki-inu.github.io/relnote/monorepo.html · Windows / PowerShell: https://loki-inu.github.io/relnote/windows.html · OSSDrop: https://ossdrop.com/tool/relnote

## Install

Python 3.11+, git on PATH, no third-party packages.

### Single file (no pip, no clone)

Each GitHub Release ships `relnote`, a self-contained Python [zipapp](https://docs.python.org/3/library/zipapp.html). Download it, make it executable, done:

```bash
mkdir -p ~/.local/bin
curl -fsSL -o ~/.local/bin/relnote https://github.com/loki-inu/relnote/releases/latest/download/relnote
chmod +x ~/.local/bin/relnote
relnote --version   # relnote 0.3.4
```

Pin a version with `releases/download/v0.3.4/relnote` instead of `releases/latest/download/relnote`. The same release has `SHA256SUMS` to check the download, and `relnote.pyz` (identical bytes) for `python relnote.pyz` on Windows:

```bash
curl -fsSL -O https://github.com/loki-inu/relnote/releases/download/v0.3.4/SHA256SUMS
grep ' relnote$' SHA256SUMS | sha256sum -c -
```

See [single-file install](https://loki-inu.github.io/relnote/single-file.html) for SHA256 checks, Windows (`relnote.pyz`), and mise. For GitLab CI, Jenkins, or any other CI, see [the CI page](https://loki-inu.github.io/relnote/ci.html). To build the file yourself: `python3 scripts/build_zipapp.py` writes `dist/relnote`, `dist/relnote.pyz`, and `dist/SHA256SUMS`.

With [mise](https://mise.jdx.dev/) the same file installs through the GitHub backend:

```bash
mise use -g 'github:loki-inu/relnote[bin=relnote]'
```

### Other ways

From a checkout of this repository:

```bash
python3 -m relnote --help
```

Or install the `relnote` console script from GitHub ([optional download on itch.io](https://loki-inu.itch.io/relnote)):

```bash
pip install git+https://github.com/loki-inu/relnote.git
relnote --help
```

With Homebrew on macOS or Linux ([loki-inu/homebrew-tap](https://github.com/loki-inu/homebrew-tap)):

```bash
brew install loki-inu/tap/relnote
```

With [pixi](https://pixi.sh) or conda from [conda-forge](https://anaconda.org/conda-forge/relnote) (any OS; pulls in Python and git for you):

```bash
pixi global install relnote
# or
conda install -c conda-forge relnote
```

On Windows with [Scoop](https://scoop.sh) ([loki-inu/scoop-bucket](https://github.com/loki-inu/scoop-bucket); needs Python 3.11+):

```powershell
scoop bucket add loki-inu https://github.com/loki-inu/scoop-bucket
scoop install loki-inu/relnote
```

In PowerShell, write files with `relnote --output notes.md` rather than `>` (Windows PowerShell 5.1 redirects as UTF-16). See [Windows and PowerShell](https://loki-inu.github.io/relnote/windows.html).

If you use the GitHub CLI, install it as a `gh` extension ([gh-relnote](https://github.com/loki-inu/gh-relnote)), which can also create the release:

```bash
gh extension install loki-inu/gh-relnote
gh relnote
gh relnote create v1.3.0 --draft
```

## Why not git log

Conventional commits already have the grouping; relnote just prints a Release body. stdlib-only, no config file.

## What it does

Reads the current repository, from the latest tag (or `--since <ref>`) to `HEAD`, and prints a GitHub Release body:

- **Features** — `feat` / `feat(scope)`
- **Fixes** — `fix` / `fix(scope)`
- **Breaking** — `feat!`, `fix!`, any `type!`, or a `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer
- **Other** — `docs`, `chore`, `refactor`, and anything that is not a conventional commit

Merge commits are omitted by default. So are `chore(release): v1.4.0` commits (the commit that cuts a release, e.g. from `examples/release.sh`), so notes generated on the tag push do not list it under Other; `--include-release-commits` keeps them. `Co-authored-by` trailers are listed; names are not invented. Subjects that look like tokens or keys are dropped, never printed.

## Examples

```bash
# latest tag → HEAD, GitHub markdown
python3 -m relnote

# explicit range
python3 -m relnote --since v1.2.0 --until v1.3.0

# cap length, hide dependabot / renovate / [bot]
python3 -m relnote --since v1.0.0 --max 25 --no-bots

# plain text
python3 -m relnote --format plain --include-merges

# write a file (still prints to stdout)
python3 -m relnote --output /tmp/notes.md

# CI: write a file, no stdout
python3 -m relnote --output notes.md --quiet

# keep CHANGELOG.md up to date (prepends "## [v1.3.0] - YYYY-MM-DD")
python3 -m relnote --since v1.2.0 --changelog CHANGELOG.md --changelog-title v1.3.0

# what should the next tag be? (feat → minor, fix → patch, breaking → major)
python3 -m relnote --next-version          # e.g. v1.4.0

# changelog section titled with the computed version
python3 -m relnote --changelog CHANGELOG.md --changelog-title "$(python3 -m relnote --next-version)"

# monorepo: one package's commits since its own tag (api/v1.2.0 → HEAD)
python3 -m relnote --path packages/api --tag-prefix api/v
python3 -m relnote --path packages/api --tag-prefix api/v --next-version   # api/v1.3.0

# another checkout
python3 relnote/__main__.py --repo /path/to/project
```

Paste stdout into a GitHub Release. If `origin` is a `github.com` remote, the footer includes a compare URL.

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--since REF` | latest tag, or full history | start of the range |
| `--until REF` | `HEAD` | end of the range |
| `--format github\|plain` | `github` | markdown vs plain text |
| `--max N` | no cap | newest N commits after filters |
| `--exclude-merges` | on | skip merge commits |
| `--include-merges` | off | keep merge commits |
| `--no-bots` | off | drop dependabot, renovate, `[bot]` |
| `--include-release-commits` | off | keep `chore(release): …` commits (left out by default, from v0.3.3) |
| `--path DIR` | whole repo | only commits touching DIR; repeat for several (monorepos) |
| `--tag-prefix PREFIX` | any tag | only tags starting with PREFIX (e.g. `api/v`, `web@`) count for the default `--since` and `--next-version` |
| `--next-version` | off | print the next semver tag instead of notes |
| `--repo PATH` | `.` | git working tree |
| `--output FILE` | off | also write notes to FILE (UTF-8); still print to stdout unless `--quiet` |
| `--changelog FILE` | off | prepend a `## [TITLE] - DATE` section to FILE (created with a `# Changelog` header if missing) |
| `--changelog-title TITLE` | `--until` if not `HEAD`; the tag on `HEAD` if there is one (v0.3.4+); else `Unreleased` | section title for `--changelog` |
| `--date YYYY-MM-DD` | today (UTC) | section date for `--changelog` |
| `--quiet` / `-q` | off | with `--output` or `--changelog`, do not print notes to stdout |
| `--help` | | this explanation |
| `--version` | | print `relnote 0.3.4` |

Exit `1` if the path is not a git repo, a ref does not exist, nothing remains after filters, `--output` / `--changelog` points at a missing parent directory, the changelog already has a section with that title, or `--next-version` finds a base tag that is not `x.y.z`. Exit `2` if `--quiet` is set without `--output` or `--changelog`.

If `--until` (default `HEAD`) is itself tagged, the default range starts at the tag before it, so running relnote right after `git tag v1.4.0` (or in a tag-push workflow) gives that release's notes. From v0.3.4 the range line and compare link then end at that tag (`v1.3.0...v1.4.0`) instead of `HEAD`, so a Release body stays correct after `main` moves on.

### Next version

`--next-version` reads the same range and prints one line: the previous tag bumped by the commits in it. Any breaking change (`type!:` or a `BREAKING CHANGE:` footer) bumps major, any `feat` bumps minor, anything else bumps patch. While the major version is `0`, a breaking change bumps minor. The `v` (and any `--tag-prefix`) is kept; with no previous tag it prints `v0.1.0`. relnote never creates the tag.

### Monorepos

`--path packages/api` keeps only commits that touch that directory (repeat `--path` for more). `--tag-prefix api/v` makes the default range start at the newest `api/v*` tag instead of the newest tag of any package. Together they give per-package notes, changelog sections, and next versions from one repo. Guide with tag conventions and a GitHub Actions matrix: [Release notes for a monorepo](https://loki-inu.github.io/relnote/monorepo.html).

### CHANGELOG.md

`--changelog` writes the same grouped notes into a Keep a Changelog style file. The new section goes above the newest `## ` entry; your header and older entries stay byte-for-byte the same. Running it twice for the same title is refused, so a re-run in CI cannot duplicate a release.

### One-command local release (standard-version style)

[`examples/release.sh`](examples/release.sh) does what `npx standard-version` did, with no Node: picks the next version, bumps `package.json` / `pyproject.toml` / `Cargo.toml` (`--bump-file`), prepends `CHANGELOG.md`, commits `chore(release): vX.Y.Z` and creates an annotated tag. `--dry-run`, `--release-as`, `--skip-commit`, `--skip-tag`, `--tag-prefix`. Nothing is pushed. Guide: [standard-version alternative](https://loki-inu.github.io/relnote/standard-version-alternative.html).

```sh
./release.sh --dry-run --bump-file package.json
./release.sh --bump-file package.json && git push --follow-tags
```

## GitHub Action

Use this repository from another workflow. Pin `loki-inu/relnote@v0.3.4` (any tag from v0.3.3 loads; v0.3.4 names a tag-push range after the pushed tag, so the compare link ends at `v1.4.0` instead of `HEAD`). In v0.1.1–v0.3.2, `action.yml` had an unquoted `: ` in an input description, and the runner refuses to load it ("Mapping values are not allowed in this context"); v0.3.3 fixes that, and CI now runs the action itself on Linux and Windows. The CLI in those tags is fine.

```yaml
name: Release notes

on:
  workflow_dispatch:

jobs:
  notes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - id: relnote
        uses: loki-inu/relnote@v0.3.4
      - name: Print notes
        env:
          NEXT: ${{ steps.relnote.outputs.next-version }}
          NOTES: ${{ steps.relnote.outputs.notes }}
        run: |
          echo "next: $NEXT"
          printf '%s\n' "$NOTES"
```

Optional inputs: `since`, `until`, `max`, `format` (default `github`), `no-bots` (default `true`), `repo`, `changelog` (path to prepend a section to, from v0.2.0), `changelog-title`, `path` (one directory per line, from v0.3.1), `tag-prefix`, `include-release-commits` (default `false`, from v0.3.3), `fail-on-empty` (default `false`, from v0.3.3). Outputs: `notes`, `next-version` (from v0.3.1; empty if the base tag is not semver), and `has-changes` (from v0.3.3).

**Nothing to release is not an error.** From v0.3.3, when there are no new commits after the filters (for example a monorepo package untouched since its last tag), the step succeeds with `has-changes` = `false` and empty `notes` and `next-version`, and writes no changelog section. Gate the release steps on it, or set `fail-on-empty: true` to fail as before. Real errors (unknown ref, not a git repo) still fail the step.

```yaml
      - id: relnote
        uses: loki-inu/relnote@v0.3.4
        with:
          path: packages/api
          tag-prefix: api/v
      - if: steps.relnote.outputs.has-changes == 'true'
        run: gh release create "$TAG" --notes "$NOTES"
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ steps.relnote.outputs.next-version }}
          NOTES: ${{ steps.relnote.outputs.notes }}
```

Pass outputs to `run:` steps through `env:` as above, not as `${{ … }}` inside the script: the notes contain backticks and commit subjects, which the shell would otherwise run.

A copy-paste workflow that opens a **draft** GitHub Release on tag push is in [examples/draft-release.yml](examples/draft-release.yml). Walkthrough (tag-push drafts, `has-changes` gating, monorepo matrix, CHANGELOG.md, FAQ): [GitHub Action guide](https://loki-inu.github.io/relnote/github-action.html).

Not on GitHub Actions? Download the single file and run it in GitLab CI, Jenkins, Buildkite, or CircleCI: [Release notes in GitLab CI, Jenkins or any CI](https://loki-inu.github.io/relnote/ci.html).

## What it is not

- Not a GitHub App. It does not create the Release or the tag, open a PR, or commit. `--next-version` only prints a suggestion. `--changelog` only edits the file on disk.
- Not a secret scanner for the tree. It only refuses to *print* commit subjects that look like tokens.
- Not a rewrite of your history and not a substitute for reading the diff.

## Licence and price

MIT. Copyright (c) 2026 loki-inu.

The useful core is here. A later paid band of **$9–15** (or free OSS plus Polar extras such as a workflow wrapper) is a listing decision, not part of this tree. No wallet, no signup, no checkout in this product.

