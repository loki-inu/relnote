"""Classify commits and render release notes.

This module is git-free. Feed it subjects (and optional bodies / authors);
it groups Conventional Commits and prints GitHub-flavored markdown or plain
text. Secret-looking subjects are flagged so the CLI can drop them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable, Sequence

CATEGORIES = ("breaking", "features", "fixes", "other")

CATEGORY_HEADINGS = {
    "breaking": "Breaking",
    "features": "Features",
    "fixes": "Fixes",
    "other": "Other",
}

CONV_RE = re.compile(
    r"""
    ^(?P<type>
        feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert
    )
    (?:\((?P<scope>[^)]*)\))?
    (?P<bang>!)?
    :[ \t]*
    (?P<description>.+?)
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

BREAKING_FOOTER_RE = re.compile(
    r"^BREAKING[ -]CHANGE:[ \t]*(?P<note>.+)",
    re.IGNORECASE | re.MULTILINE,
)

COAUTHOR_RE = re.compile(
    r"^Co-authored-by:[ \t]*(?P<name>[^<\n]+?)(?:[ \t]+<(?P<email>[^>\n]+)>)?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

SECRET_PATTERNS = (
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgho_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghu_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghs_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghr_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bsk_test_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\brk_live_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|bearer)[ \t]*[=:][ \t]*\S{8,}"
    ),
)

BOT_MARKERS = ("dependabot", "renovate", "[bot]")


def looks_like_secret(text: str) -> bool:
    """True if *text* looks like it contains a token or key."""
    if not text:
        return False
    return any(pattern.search(text) for pattern in SECRET_PATTERNS)


def is_bot(author_name: str = "", author_email: str = "", subject: str = "") -> bool:
    """True if name, email, or subject looks like dependabot / renovate / [bot]."""
    blob = f"{author_name} {author_email} {subject}".lower()
    return any(marker in blob for marker in BOT_MARKERS)


def parse_coauthors(body: str) -> list[tuple[str, str]]:
    """Return (name, email) pairs from Co-authored-by trailers. Does not invent."""
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    if not body:
        return found
    for match in COAUTHOR_RE.finditer(body):
        name = (match.group("name") or "").strip()
        email = (match.group("email") or "").strip()
        if not name and not email:
            continue
        key = (name.lower(), email.lower())
        if key in seen:
            continue
        seen.add(key)
        found.append((name, email))
    return found


def parse_conventional(subject: str) -> dict | None:
    """Parse a Conventional Commits subject. None if it is not conventional."""
    if not subject:
        return None
    match = CONV_RE.match(subject.strip())
    if not match:
        return None
    scope = (match.group("scope") or "").strip() or None
    return {
        "type": match.group("type").lower(),
        "scope": scope,
        "breaking": bool(match.group("bang")),
        "description": match.group("description").strip(),
    }


@dataclass
class Classified:
    category: str
    description: str
    short_hash: str = ""
    full_hash: str = ""
    author_name: str = ""
    author_email: str = ""
    coauthors: list[tuple[str, str]] = field(default_factory=list)
    ctype: str | None = None
    scope: str | None = None
    breaking_note: str | None = None
    secret: bool = False
    bot: bool = False

    @property
    def authors(self) -> list[str]:
        """Primary author then co-authors, de-duplicated, nothing invented."""
        names: list[str] = []
        seen: set[str] = set()

        def add(label: str) -> None:
            label = label.strip()
            if not label:
                return
            key = label.lower()
            if key in seen:
                return
            seen.add(key)
            names.append(label)

        add(self.author_name)
        for name, email in self.coauthors:
            add(name or email)
        return names


def classify(
    subject: str,
    body: str = "",
    *,
    author_name: str = "",
    author_email: str = "",
    short_hash: str = "",
    full_hash: str = "",
) -> Classified:
    """Classify one commit. Secret-looking subjects are flagged, not rewritten."""
    subject = (subject or "").strip()
    body = body or ""
    secret = looks_like_secret(subject)
    bot = is_bot(author_name, author_email, subject)
    parsed = parse_conventional(subject) if subject else None

    breaking_note = None
    footer = BREAKING_FOOTER_RE.search(body)
    if footer:
        note = footer.group("note").strip()
        if note and looks_like_secret(note):
            breaking_note = "(omitted: looked like a secret)"
        elif note:
            breaking_note = note

    is_breaking = bool(parsed and parsed["breaking"]) or bool(footer)

    if parsed:
        description = parsed["description"]
        ctype = parsed["type"]
        scope = parsed["scope"]
    else:
        description = subject
        ctype = None
        scope = None

    if is_breaking:
        category = "breaking"
    elif ctype == "feat":
        category = "features"
    elif ctype == "fix":
        category = "fixes"
    else:
        category = "other"

    return Classified(
        category=category,
        description=description,
        short_hash=short_hash,
        full_hash=full_hash,
        author_name=author_name,
        author_email=author_email,
        coauthors=parse_coauthors(body),
        ctype=ctype,
        scope=scope,
        breaking_note=breaking_note,
        secret=secret,
        bot=bot,
    )


def select(
    items: Iterable[Classified],
    *,
    no_bots: bool = False,
    max_n: int | None = None,
) -> list[Classified]:
    """Drop secrets, empty subjects, and optionally bots. Honour --max."""
    chosen: list[Classified] = []
    for item in items:
        if item.secret:
            continue
        if not item.description and not item.breaking_note:
            continue
        if no_bots and item.bot:
            continue
        chosen.append(item)
        if max_n is not None and len(chosen) >= max_n:
            break
    return chosen


def group_commits(items: Sequence[Classified]) -> dict[str, list[Classified]]:
    """Bucket classified commits. Section order is Breaking, Features, Fixes, Other."""
    grouped: dict[str, list[Classified]] = {key: [] for key in CATEGORIES}
    for item in items:
        grouped.setdefault(item.category, []).append(item)
    return grouped


def _bullet_text(item: Classified, *, markdown: bool) -> str:
    desc = item.description or "(no subject)"
    if item.scope:
        desc = f"**{item.scope}:** {desc}" if markdown else f"{item.scope}: {desc}"
    elif item.category == "other" and item.ctype:
        desc = f"**{item.ctype}:** {desc}" if markdown else f"{item.ctype}: {desc}"

    if item.short_hash:
        desc = f"{desc} (`{item.short_hash}`)" if markdown else f"{desc} ({item.short_hash})"

    authors = item.authors
    if authors:
        desc = f"{desc} — {', '.join(authors)}"
    return desc


def render_github(
    grouped: dict[str, list[Classified]],
    *,
    since: str | None = None,
    until: str = "HEAD",
    compare_url: str | None = None,
    omitted: int = 0,
) -> str:
    """GitHub-flavored markdown suitable for a Release body."""
    lines: list[str] = ["## What's changed", ""]
    any_items = False
    for key in CATEGORIES:
        items = grouped.get(key) or []
        if not items:
            continue
        any_items = True
        lines.append(f"### {CATEGORY_HEADINGS[key]}")
        lines.append("")
        for item in items:
            lines.append(f"- {_bullet_text(item, markdown=True)}")
            if item.breaking_note:
                lines.append(f"  - BREAKING CHANGE: {item.breaking_note}")
        lines.append("")
    if not any_items:
        return ""

    left = since or "(start)"
    lines.append("---")
    lines.append("")
    lines.append(f"Range: `{left}` → `{until}`.")
    if compare_url:
        lines.append("")
        lines.append(f"**Full changelog:** {compare_url}")
    if omitted:
        lines.append("")
        lines.append(
            f"_{omitted} commit(s) omitted (bots or secret-looking subjects)._"
        )
    lines.append("")
    return "\n".join(lines)


def render_plain(
    grouped: dict[str, list[Classified]],
    *,
    since: str | None = None,
    until: str = "HEAD",
    compare_url: str | None = None,
    omitted: int = 0,
) -> str:
    """Plain text, same structure, no markdown emphasis."""
    lines: list[str] = ["What's changed", ""]
    any_items = False
    for key in CATEGORIES:
        items = grouped.get(key) or []
        if not items:
            continue
        any_items = True
        lines.append(CATEGORY_HEADINGS[key])
        for item in items:
            lines.append(f"  * {_bullet_text(item, markdown=False)}")
            if item.breaking_note:
                lines.append(f"    BREAKING CHANGE: {item.breaking_note}")
        lines.append("")
    if not any_items:
        return ""

    left = since or "(start)"
    lines.append(f"Range: {left} -> {until}")
    if compare_url:
        lines.append(f"Full changelog: {compare_url}")
    if omitted:
        lines.append(f"{omitted} commit(s) omitted (bots or secret-looking subjects).")
    lines.append("")
    return "\n".join(lines)


def render(
    grouped: dict[str, list[Classified]],
    format: str = "github",
    **meta: object,
) -> str:
    if format == "plain":
        return render_plain(grouped, **meta)  # type: ignore[arg-type]
    if format == "github":
        return render_github(grouped, **meta)  # type: ignore[arg-type]
    raise ValueError(f"unknown format: {format!r}")


def notes_from_rows(
    rows: Sequence[dict],
    *,
    no_bots: bool = False,
    max_n: int | None = None,
    format: str = "github",
    since: str | None = None,
    until: str = "HEAD",
    compare_url: str | None = None,
) -> str:
    """Classify a list of commit dicts and render. Used by tests and the sample."""
    classified = [
        classify(
            row.get("subject", ""),
            row.get("body", ""),
            author_name=row.get("author_name", ""),
            author_email=row.get("author_email", ""),
            short_hash=row.get("short_hash", ""),
            full_hash=row.get("full_hash", ""),
        )
        for row in rows
    ]
    chosen = select(classified, no_bots=no_bots, max_n=max_n)
    omitted = sum(
        1
        for item in classified
        if item.secret or (no_bots and item.bot)
    )
    return render(
        group_commits(chosen),
        format=format,
        since=since,
        until=until,
        compare_url=compare_url,
        omitted=omitted,
    )
