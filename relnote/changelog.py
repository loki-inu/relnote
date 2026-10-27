"""Prepend a release section to a CHANGELOG.md file (Keep a Changelog style).

Git-free and stdlib only. The section body reuses relnote's grouping; the
file keeps its existing header and older sections untouched.
"""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_HEADER = (
    "# Changelog\n"
    "\n"
    "All notable changes to this project are documented in this file.\n"
    "\n"
)

SECTION_RE = re.compile(r"^## ", re.MULTILINE)

# "(#123)" as left by GitHub squash merges ("feat: thing (#123)").
PR_REF_RE = re.compile(r"\(#(\d+)\)")


class ChangelogError(Exception):
    """Raised when the changelog cannot be updated safely."""


def _heading_re(title: str) -> re.Pattern[str]:
    escaped = re.escape(title)
    return re.compile(
        rf"^##[ \t]+\[?{escaped}\]?(?:[ \t]|$)",
        re.MULTILINE,
    )


def link_pr_refs(line: str, repo: str) -> str:
    """Link `(#123)` to the pull request on github.com/<repo>.

    GitHub autolinks `#123` in Release bodies but not in CHANGELOG.md
    files, so the changelog gets explicit links. Code spans are left alone.
    """
    parts = line.split("`")
    for i in range(0, len(parts), 2):
        parts[i] = PR_REF_RE.sub(
            lambda m: f"([#{m.group(1)}](https://github.com/{repo}/pull/{m.group(1)}))",
            parts[i],
        )
    return "`".join(parts)


def section_from_notes(
    notes: str, *, title: str, date: str | None, repo: str | None = None
) -> str:
    """Turn relnote github-format notes into a `## [title] - date` section.

    Drops the "What's changed" heading and the Range footer, keeps the
    category headings, bullets, and the full-changelog compare link.
    With `repo` ("owner/name"), `(#123)` in bullets links to the PR.
    """
    lines = notes.splitlines()
    if lines and lines[0].strip() == "## What's changed":
        lines = lines[1:]
    body: list[str] = []
    footer: list[str] = []
    in_footer = False
    for line in lines:
        if line.strip() == "---":
            in_footer = True
            continue
        if in_footer:
            if line.startswith("**Full changelog:**"):
                footer.append(line)
            continue
        if repo and line.lstrip().startswith("- "):
            line = link_pr_refs(line, repo)
        body.append(line)
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()

    head = f"## [{title}]"
    if date:
        head += f" - {date}"
    out = [head, ""]
    out.extend(body)
    if footer:
        out.append("")
        out.extend(footer)
    out.append("")
    return "\n".join(out) + "\n"


def prepend_section(existing: str | None, section: str, *, title: str) -> str:
    """Insert `section` before the first `## ` heading of `existing`."""
    if existing is None or not existing.strip():
        return DEFAULT_HEADER + section
    if _heading_re(title).search(existing):
        raise ChangelogError(f"changelog already has a section for {title}")
    match = SECTION_RE.search(existing)
    if match is None:
        head = existing if existing.endswith("\n") else existing + "\n"
        if not head.endswith("\n\n"):
            head += "\n"
        return head + section
    return existing[: match.start()] + section + existing[match.start() :]


def update_changelog(
    path: str | Path,
    notes: str,
    *,
    title: str,
    date: str | None,
    repo: str | None = None,
) -> None:
    dest = Path(path)
    if not dest.parent.exists():
        raise ChangelogError(f"changelog directory does not exist: {dest.parent}")
    existing = None
    eol = "\n"
    if dest.exists():
        # newline="" keeps CRLF/LF as on disk, so the file keeps its line endings
        # on every OS (no whole-file CRLF rewrite on Windows, no LF rewrite of a
        # CRLF file elsewhere). A new file gets LF.
        with open(dest, encoding="utf-8", newline="") as fh:
            raw = fh.read()
        if "\r\n" in raw:
            eol = "\r\n"
        existing = raw.replace("\r\n", "\n")
    section = section_from_notes(notes, title=title, date=date, repo=repo)
    text = prepend_section(existing, section, title=title)
    if eol != "\n":
        text = text.replace("\n", eol)
    try:
        with open(dest, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    except OSError as exc:
        raise ChangelogError(f"cannot write {dest}: {exc}") from exc
