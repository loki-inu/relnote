# relnote

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

## Compared to `gh` and git-cliff

relnote runs offline, stdlib-only, with no GitHub API and no config file. It groups conventional commits into Features, Fixes, and Breaking.

Keep using `gh release create --generate-notes` when you want GitHub's official, PR-linked notes. Use [git-cliff](https://git-cliff.org/) when you want a full changelog file, Tera templates, and a config. relnote is the smaller offline alternative.

Docs: https://loki-inu.github.io/relnote/

## Install

Python 3.11+, git on PATH, no third-party packages.

From a checkout of this repository:

```bash
python3 -m relnote --help
```

Or install the `relnote` console script from GitHub ([optional download on itch.io](https://loki-inu.itch.io/relnote)):

```bash
pip install git+https://github.com/loki-inu/relnote.git
relnote --help
```

## Why not git log

Conventional commits already have the grouping; relnote just prints a Release body. stdlib-only, no config file.

## What it does

Reads the current repository, from the latest tag (or `--since <ref>`) to `HEAD`, and prints a GitHub Release body:

- **Features** — `feat` / `feat(scope)`
- **Fixes** — `fix` / `fix(scope)`
- **Breaking** — `feat!`, `fix!`, any `type!`, or a `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer
- **Other** — `docs`, `chore`, `refactor`, and anything that is not a conventional commit

Merge commits are omitted by default. `Co-authored-by` trailers are listed; names are not invented. Subjects that look like tokens or keys are dropped, never printed.

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
| `--repo PATH` | `.` | git working tree |
| `--output FILE` | off | also write notes to FILE (UTF-8); still print to stdout unless `--quiet` |
| `--quiet` / `-q` | off | with `--output`, do not print notes to stdout |
| `--help` | | this explanation |
| `--version` | | print `relnote 0.1.5` |

Exit `1` if the path is not a git repo, a ref does not exist, nothing remains after filters, or `--output` points at a missing parent directory. Exit `2` if `--quiet` is set without `--output`.

## GitHub Action

Use this repository from another workflow. The action first shipped in **v0.1.1** — pin `loki-inu/relnote@v0.1.5` or `@main` for current. The `v0.1.0` tag is CLI-only.

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
        uses: loki-inu/relnote@v0.1.5
      - name: Print notes
        run: printf '%s\n' "${{ steps.relnote.outputs.notes }}"
```

Optional inputs: `since`, `until`, `max`, `format` (default `github`), `no-bots` (default `true`), `repo`.

A copy-paste workflow that opens a **draft** GitHub Release on tag push is in [examples/draft-release.yml](examples/draft-release.yml).

## What it is not

- Not a GitHub App. It does not create the Release, open a PR, or bump versions.
- Not a secret scanner for the tree. It only refuses to *print* commit subjects that look like tokens.
- Not a rewrite of your history and not a substitute for reading the diff.

## Licence and price

MIT. Copyright (c) 2026 loki-inu.

The useful core is here. A later paid band of **$9–15** (or free OSS plus Polar extras such as a workflow wrapper) is a listing decision, not part of this tree. No wallet, no signup, no checkout in this product.
