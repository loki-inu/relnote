# itch.io listing — relnote

Paste-ready. Do not add download counts, reviews, or other social proof that does not exist.

## Title

relnote

## Short text / tagline

Turn a git range into clean GitHub release notes.

## First screen (page body)

relnote is a small Python CLI. Point it at a git repo. It reads from the last tag (or any `--since` ref) to HEAD, groups conventional commits into Features, Fixes, Breaking, and Other, and prints GitHub-flavored markdown you can paste into a Release.

Source, issues, and `pip` install live on GitHub:

https://github.com/loki-inu/relnote

```
pip install git+https://github.com/loki-inu/relnote.git
relnote --help
```

No pip dependencies. Python 3.11+ stdlib + git. Merge commits are skipped by default. Dependabot / renovate / `[bot]` can be dropped with `--no-bots`. Subjects that look like tokens are never printed.

This page is a download of the same files. It is not a hosted service and it does not create the GitHub Release for you.

## What's included

- `relnote/` — the CLI (`python3 -m relnote` or `python3 relnote/__main__.py`)
- `tests/test_format.py` — stdlib unit tests
- `samples/example-output.md` — generated from a synthetic commit list
- `README.md`, `PRODUCT.md`, MIT `LICENSE`
- `pyproject.toml` — installable as the `relnote` console script

## Who it's for

Developers who cut releases and are tired of pasting `git log`. You already have Python and git.

## What it's not

- Not git-cliff, release-please, or a GitHub App
- Not a changelog file writer
- Not a secret scanner for the whole tree
- Not a hosted release service

## Price note

Free / pay-what-you-want. Suggested $9 if you want to support the project. The same files are free on GitHub. No invented launch discount.

## Classification

Tool / software. English.
