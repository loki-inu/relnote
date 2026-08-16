# relnote

Turn a git range into clean GitHub release notes.

## Install

Python 3.11+, git on PATH, no third-party packages.

From a checkout of this repository:

```bash
python3 -m relnote --help
```

Or install the `relnote` console script from GitHub:

```bash
pip install git+https://github.com/loki-inu/relnote.git
relnote --help
```

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

# another checkout
python3 relnote/__main__.py --repo /path/to/project
```

Paste stdout into a GitHub Release. If `origin` is a `github.com` remote, the footer includes a compare URL. See [samples/example-output.md](samples/example-output.md) for a generated example from a **synthetic** commit list (a fictional CLI called harbor — not scraped from anyone's history).

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
| `--help` | | this explanation |
| `--version` | | print `relnote 0.1.0` |

Exit `1` if the path is not a git repo, a ref does not exist, or nothing remains after filters.

## What it is not

- Not git-cliff, conventional-changelog, release-please, or semantic-release. No config file, no plugin host, no changelog on disk.
- Not a GitHub App. It does not create the Release, open a PR, or bump versions.
- Not a secret scanner for the tree. It only refuses to *print* commit subjects that look like tokens.
- Not a rewrite of your history and not a substitute for reading the diff.

## Licence and price

MIT. Copyright (c) 2026 loki-inu.

The useful core is here. A later paid band of **$9–15** (or free OSS plus Polar extras such as a workflow wrapper) is a listing decision, not part of this tree. No wallet, no signup, no checkout in this product.
