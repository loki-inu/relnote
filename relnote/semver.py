"""Suggest the next semantic version from classified commits."""

from __future__ import annotations

import re
from typing import Iterable

VERSION_RE = re.compile(r"^(?P<v>v?)(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:[-+].*)?$")


class VersionError(Exception):
    """The base tag is not a semantic version."""


def bump_kind(categories: Iterable[str]) -> str:
    """'major' if anything breaks, 'minor' for any feature, else 'patch'."""
    seen = set(categories)
    if "breaking" in seen:
        return "major"
    if "features" in seen:
        return "minor"
    return "patch"


def next_version(base_tag: str | None, kind: str, *, prefix: str = "") -> str:
    """Return the next tag name.

    *base_tag* is the previous release tag (or None for a first release,
    which gives ``<prefix or v>0.1.0``). *prefix* is stripped before parsing
    and put back on the result, so ``api/v1.2.3`` with prefix ``api/``
    becomes ``api/v1.3.0``. While the major version is 0, a breaking change
    bumps the minor version (0.y.z is unstable by definition).
    """
    if base_tag is None:
        return f"{prefix or 'v'}0.1.0"
    rest = base_tag
    if prefix:
        if not base_tag.startswith(prefix):
            raise VersionError(f"tag {base_tag!r} does not start with {prefix!r}")
        rest = base_tag[len(prefix):]
    match = VERSION_RE.match(rest)
    if not match:
        raise VersionError(f"tag {base_tag!r} is not a semantic version (x.y.z)")
    major = int(match.group("major"))
    minor = int(match.group("minor"))
    patch = int(match.group("patch"))
    if kind == "major" and major == 0:
        kind = "minor"
    if kind == "major":
        major, minor, patch = major + 1, 0, 0
    elif kind == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{prefix}{match.group('v')}{major}.{minor}.{patch}"
