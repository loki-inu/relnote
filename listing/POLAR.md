# Polar listing — relnote

Paste-ready. Do not add stars, user counts, or testimonials that do not exist.

## Title

relnote

## One-liner

Turn a git range into clean GitHub release notes.

## First screen

A stdlib Python CLI for the five minutes before you click "Publish release". relnote reads `last-tag..HEAD` (or `--since` / `--until`), groups conventional commits into Features, Fixes, Breaking, and Other, and prints markdown that belongs in a GitHub Release body.

Source: https://github.com/loki-inu/relnote

Delivery: the repository / zip. Not a hosted API. Not usage-metered.

## What's included

- `relnote` package — `python3 -m relnote` or `pip install git+https://github.com/loki-inu/relnote.git`
- Flags: `--format github|plain`, `--max N`, `--exclude-merges` (default on), `--include-merges`, `--no-bots`, `--repo`
- Co-authored-by listed only when the trailer is present
- Secret-looking subjects omitted
- Tests and a synthetic sample so you can judge the output before running it on your tree

## Who it's for

Anyone cutting a release. Polar is the fiat rail when the seller account can complete Stripe Identity / Connect.

Optional later extras (not in this zip): a GitHub Action wrapper, extra formats. Price those separately if they exist.

## What it's not

- Not a replacement for release-please, semantic-release, or git-cliff
- Not a GitHub App and not a version bumper
- Not a KYC workaround
- Not VAT or income-tax advice. Polar as merchant of record does not file the seller's return

## Price note

$9–15 one-time for the CLI, or free on GitHub with paid extras later. No invented launch discount. Pick one story and keep it honest.
