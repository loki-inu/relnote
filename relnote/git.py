"""Read commits from a local git repository via the git CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess


class GitError(Exception):
    """The working directory is not a repo, a ref is missing, or git failed."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass
class Commit:
    hash: str
    short: str
    author_name: str
    author_email: str
    parents: list[str]
    subject: str
    body: str

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1


RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"
PRETTY = (
    f"%H{FIELD_SEP}%h{FIELD_SEP}%an{FIELD_SEP}%ae"
    f"{FIELD_SEP}%P{FIELD_SEP}%s{FIELD_SEP}%b{RECORD_SEP}"
)


def run_git(args: list[str], cwd: str | Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitError("git is not installed or not on PATH") from exc


def repo_root(path: str | Path | None = None) -> Path:
    cwd = Path(path or ".").resolve()
    result = run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    if result.returncode != 0:
        raise GitError("not a git repository (or any parent)")
    return Path(result.stdout.strip())


def last_tag(cwd: str | Path | None = None) -> str | None:
    result = run_git(["describe", "--tags", "--abbrev=0"], cwd=cwd)
    if result.returncode != 0:
        return None
    tag = result.stdout.strip()
    return tag or None


def resolve_ref(ref: str, cwd: str | Path | None = None) -> str:
    result = run_git(["rev-parse", "--verify", f"{ref}^{{commit}}"], cwd=cwd)
    if result.returncode != 0:
        raise GitError(f"unknown ref: {ref}")
    return result.stdout.strip()


def github_compare_url(
    since: str | None,
    until: str,
    cwd: str | Path | None = None,
) -> str | None:
    if not since:
        return None
    result = run_git(["remote", "get-url", "origin"], cwd=cwd)
    if result.returncode != 0:
        return None
    owner_repo = _parse_github_remote(result.stdout.strip())
    if not owner_repo:
        return None
    return f"https://github.com/{owner_repo}/compare/{since}...{until}"


def _parse_github_remote(url: str) -> str | None:
    url = url.strip()
    patterns = (
        r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$",
        r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
        r"ssh://git@github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$",
    )
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
    return None


def parse_log(raw: str) -> list[Commit]:
    commits: list[Commit] = []
    if not raw or not raw.strip():
        return commits
    for record in raw.split(RECORD_SEP):
        record = record.strip("\n")
        if not record.strip():
            continue
        parts = record.split(FIELD_SEP)
        if len(parts) < 6:
            continue
        hash_, short, author_name, author_email, parents, subject = parts[:6]
        body = FIELD_SEP.join(parts[6:]) if len(parts) > 6 else ""
        commits.append(
            Commit(
                hash=hash_.strip(),
                short=short.strip(),
                author_name=author_name.strip(),
                author_email=author_email.strip(),
                parents=[parent for parent in parents.split() if parent],
                subject=subject.strip(),
                body=body.strip("\n"),
            )
        )
    return commits


def collect_commits(
    *,
    since: str | None = None,
    until: str = "HEAD",
    exclude_merges: bool = True,
    cwd: str | Path | None = None,
) -> list[Commit]:
    """Return commits in since..until (newest first). Raises GitError on failure."""
    repo_root(cwd)
    resolve_ref(until, cwd=cwd)
    if since:
        resolve_ref(since, cwd=cwd)
        rev_range = f"{since}..{until}"
    else:
        rev_range = until

    args = ["log", rev_range, f"--pretty=format:{PRETTY}"]
    if exclude_merges:
        args.insert(1, "--no-merges")
    result = run_git(args, cwd=cwd)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "git log failed").strip()
        raise GitError(detail)
    return parse_log(result.stdout)
