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


class ChangelogError(Exception):
    """Raised when the changelog cannot be updated safely."""


def _heading_re(title: str) -> re.Pattern[str]:
    escaped = re.escape(title)
    return re.compile(
        rf"^##[ \t]+\[?{escaped}\]?(?:[ \t]|$)",
        re.MULTILINE,
    )


def section_from_notes(notes: str, *, title: str, date: str | None) -> str:
    """Turn relnote github-format notes into a `## [title] - date` section.

    Drops the "What's changed" heading and the Range footer, keeps the
    category headings, bullets, and the full-changelog compare link.
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


def update_changelog(path: str | Path, notes: str, *, title: str, date: str | None) -> None:
    dest = Path(path)
    if not dest.parent.exists():
        raise ChangelogError(f"changelog directory does not exist: {dest.parent}")
    existing = dest.read_text(encoding="utf-8") if dest.exists() else None
    section = section_from_notes(notes, title=title, date=date)
    try:
        dest.write_text(prepend_section(existing, section, title=title), encoding="utf-8")
    except OSError as exc:
        raise ChangelogError(f"cannot write {dest}: {exc}") from exc
