"""relnote CLI — `python3 -m relnote` or `python3 relnote/__main__.py`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from relnote import __version__
    from relnote.format import classify, group_commits, render, select
    from relnote.git import GitError, collect_commits, github_compare_url, last_tag
else:
    from . import __version__
    from .format import classify, group_commits, render, select
    from .git import GitError, collect_commits, github_compare_url, last_tag


EPILOG = """
relnote reads the current git repository (or --repo) and turns a commit
range into release notes you can paste into a GitHub Release body.

Default range
  Latest tag → HEAD. If the repo has no tags, the full history of
  --until (default HEAD) is used. Pass --since to start at any ref.

Grouping (Conventional Commits)
  feat / feat(scope)           Features
  fix  / fix(scope)            Fixes
  type!  or  BREAKING CHANGE   Breaking
  docs, chore, refactor, …     Other
  anything else                Other

Safety
  Merge commits are omitted unless you pass --include-merges.
  Subjects that look like tokens or keys are never printed.
  --no-bots drops dependabot, renovate, and authors containing "[bot]".
  Co-authored-by trailers are listed; names are not invented.

Exit status
  0  notes written to stdout (and to --output FILE, if given)
  1  not a git repository, unknown ref, no commits after filters,
     or --output parent directory does not exist

examples:
  python3 -m relnote
  python3 -m relnote --since v1.2.0
  python3 -m relnote --since v1.0.0 --max 25 --no-bots
  python3 -m relnote --format plain --include-merges
  python3 -m relnote --output /tmp/notes.md
  python3 relnote/__main__.py --repo /path/to/project
""".strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="relnote",
        description="Turn a git range into clean GitHub release notes.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--since",
        metavar="REF",
        help="start ref (default: latest tag, or full history if untagged)",
    )
    parser.add_argument(
        "--until",
        metavar="REF",
        default="HEAD",
        help="end ref (default: HEAD)",
    )
    parser.add_argument(
        "--format",
        choices=("github", "plain"),
        default="github",
        help="output format (default: github)",
    )
    parser.add_argument(
        "--max",
        dest="max_n",
        metavar="N",
        type=int,
        help="include at most N commits after filters (newest first)",
    )
    parser.add_argument(
        "--exclude-merges",
        dest="exclude_merges",
        action="store_true",
        default=True,
        help="omit merge commits (default: on)",
    )
    parser.add_argument(
        "--include-merges",
        dest="exclude_merges",
        action="store_false",
        help="include merge commits",
    )
    parser.add_argument(
        "--no-bots",
        action="store_true",
        help='drop commits from dependabot, renovate, or authors containing "[bot]"',
    )
    parser.add_argument(
        "--repo",
        metavar="PATH",
        default=".",
        help="repository path (default: current directory)",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="also write notes to FILE (UTF-8); still print to stdout",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"relnote {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_n is not None and args.max_n < 1:
        print("relnote: --max must be >= 1", file=sys.stderr)
        return 1

    try:
        since = args.since
        if since is None:
            since = last_tag(cwd=args.repo)
        raw = collect_commits(
            since=since,
            until=args.until,
            exclude_merges=args.exclude_merges,
            cwd=args.repo,
        )
        classified = [
            classify(
                commit.subject,
                commit.body,
                author_name=commit.author_name,
                author_email=commit.author_email,
                short_hash=commit.short,
                full_hash=commit.hash,
            )
            for commit in raw
        ]
        chosen = select(classified, no_bots=args.no_bots, max_n=args.max_n)
        if not chosen:
            left = since or "(start)"
            print(
                f"relnote: no commits in range {left}..{args.until}",
                file=sys.stderr,
            )
            return 1

        omitted = sum(
            1
            for item in classified
            if item.secret or (args.no_bots and item.bot)
        )
        text = render(
            group_commits(chosen),
            format=args.format,
            since=since,
            until=args.until,
            compare_url=github_compare_url(since, args.until, cwd=args.repo),
            omitted=omitted,
        )
        if text and not text.endswith("\n"):
            text += "\n"
        if args.output:
            dest = Path(args.output)
            parent = dest.parent
            if not parent.exists():
                print(
                    f"relnote: output directory does not exist: {parent}",
                    file=sys.stderr,
                )
                return 1
            try:
                dest.write_text(text, encoding="utf-8")
            except OSError as exc:
                print(f"relnote: cannot write {dest}: {exc}", file=sys.stderr)
                return 1
        sys.stdout.write(text)
        return 0
    except GitError as exc:
        print(f"relnote: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
