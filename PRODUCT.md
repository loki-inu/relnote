# relnote — product spec

**Name:** relnote
**Tagline:** Turn a git range into clean GitHub release notes.
**Author:** loki-inu
**Date:** 16 August 2026
**Licence:** MIT, copyright (c) 2026 loki-inu

## Problem

Cutting a GitHub Release still starts with `git log`. Conventional Commits already encode Features / Fixes / Breaking, but most people either paste the raw log or pull in a changelog generator that wants a config file, a Node toolchain, or a GitHub App. relnote is a stdlib CLI that does the grouping and stops there.

## Buyer

Anyone who tags a version and needs a body for the GitHub Release form. They already have Python and git.

Not for: people who want automated version bumps, changelog files committed back to the repo, or a hosted release service.

## What ships

A Python 3.11+ stdlib package (`relnote`) invoked as `python3 -m relnote` or `python3 relnote/__main__.py`. Also installable with `pip install git+https://github.com/loki-inu/relnote.git`.

- Default range: latest tag → HEAD (`--since` / `--until` to override)
- Groups: Features, Fixes, Breaking, Other
- `--format github|plain`, `--max N`, `--exclude-merges` (default on), `--no-bots`
- Light `Co-authored-by` parsing (no invented names)
- Secret-looking subjects are omitted, never printed
- Exit 1 on not-a-repo or no commits
- Sample output generated from a synthetic commit list

## Price band

$9–15 one-time later, or free public OSS with paid Polar extras (for example a GitHub Action wrapper or extra formats). Ship the useful core now. Do not invent a launch discount.

## Rails

| Rail | Role | When |
| --- | --- | --- |
| This folder / a public repo | Distribution and proof | Now |
| itch.io | Pay-what-you-want or $9–15 file download | Listing copy is ready. Payout needs a seller account. |
| Polar | Fiat + VAT merchant-of-record, optional extras | When Stripe Identity / Connect can be completed on the seller account. |

No signup, wallet, or checkout is part of this spec. The CLI is the product.

## Non-goals

- Cloning other people's repositories or scraping a git history for marketing
- Creating a wallet, seller account, or payment form
- Non-stdlib dependencies
- Becoming a full release-please / semantic-release stand-in
- Copying Agent Shop Kit wholesale
- Legal, tax, or GitHub-App hosting

## Success

A stranger can run `python3 -m relnote` in their own repo, paste the markdown into a GitHub Release, and get grouped notes without installing anything else. First-dollar is a later listing step.
