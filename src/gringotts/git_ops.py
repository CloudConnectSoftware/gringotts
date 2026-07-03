"""Git operations for registered repos."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from gringotts.registry import Registry, RepoEntry


@dataclass
class RepoStatus:
    entry: RepoEntry
    path: Path
    is_git: bool
    branch: str = ""
    head: str = ""
    remote_head: str = ""
    ahead: int = 0
    behind: int = 0
    dirty: int = 0
    untracked: int = 0
    error: str = ""

    @property
    def sync_label(self) -> str:
        if self.error:
            return f"ERROR: {self.error}"
        if not self.is_git:
            return "NO GIT"
        if self.ahead == 0 and self.behind == 0 and self.dirty == 0:
            return "OK"
        parts: list[str] = []
        if self.ahead:
            parts.append(f"ahead {self.ahead}")
        if self.behind:
            parts.append(f"behind {self.behind}")
        if self.dirty:
            parts.append(f"dirty {self.dirty}")
        return ", ".join(parts) if parts else "OK"


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def repo_path(registry: Registry, entry: RepoEntry) -> Path:
    return registry.workspace / entry.name


def inspect_repo(registry: Registry, entry: RepoEntry) -> RepoStatus:
    path = repo_path(registry, entry)
    status = RepoStatus(entry=entry, path=path, is_git=(path / ".git").exists())
    if not status.is_git:
        return status

    branch = _run_git(path, "rev-parse", "--abbrev-ref", "HEAD")
    if branch.returncode != 0:
        status.error = branch.stderr.strip() or "cannot read branch"
        return status
    status.branch = branch.stdout.strip()

    head = _run_git(path, "rev-parse", "--short", "HEAD")
    if head.returncode == 0:
        status.head = head.stdout.strip()

    remote_ref = f"origin/{entry.tracking_branch}"
    remote = _run_git(path, "rev-parse", "--short", remote_ref)
    if remote.returncode == 0:
        status.remote_head = remote.stdout.strip()

    ahead = _run_git(path, "rev-list", "--count", f"{remote_ref}..HEAD")
    behind = _run_git(path, "rev-list", "--count", f"HEAD..{remote_ref}")
    if ahead.returncode == 0 and behind.returncode == 0:
        status.ahead = int(ahead.stdout.strip())
        status.behind = int(behind.stdout.strip())

    porcelain = _run_git(path, "status", "--porcelain")
    if porcelain.returncode == 0:
        lines = [ln for ln in porcelain.stdout.splitlines() if ln.strip()]
        status.dirty = sum(1 for ln in lines if not ln.startswith("??"))
        status.untracked = sum(1 for ln in lines if ln.startswith("??"))

    return status


def fetch_repo(registry: Registry, entry: RepoEntry) -> RepoStatus:
    path = repo_path(registry, entry)
    status = inspect_repo(registry, entry)
    if not status.is_git:
        status.error = "not a git repository"
        return status
    result = _run_git(path, "fetch", "origin", "--prune")
    if result.returncode != 0:
        status.error = result.stderr.strip() or "fetch failed"
    return inspect_repo(registry, entry) if result.returncode == 0 else status


def pull_repo(registry: Registry, entry: RepoEntry, *, dry_run: bool = False) -> RepoStatus:
    status = fetch_repo(registry, entry)
    if status.error or not status.is_git:
        return status
    if status.behind == 0:
        return status
    if dry_run:
        status.error = f"would pull {status.behind} commit(s)"
        return status

    path = repo_path(registry, entry)
    if status.dirty:
        status.error = "dirty working tree — commit or stash before pull"
        return status

    pull = _run_git(path, "pull", "--ff-only", "origin", entry.tracking_branch)
    if pull.returncode != 0:
        status.error = pull.stderr.strip() or "pull failed"
        return status
    return inspect_repo(registry, entry)


def push_repo(registry: Registry, entry: RepoEntry, *, dry_run: bool = False) -> RepoStatus:
    if not entry.may_push:
        status = inspect_repo(registry, entry)
        status.error = "pull_only — gringotts will not push this repo"
        return status

    status = inspect_repo(registry, entry)
    if not status.is_git:
        status.error = "not a git repository"
        return status
    if status.dirty:
        status.error = "dirty working tree — commit before push"
        return status
    if status.ahead == 0:
        return status
    if dry_run:
        status.error = f"would push {status.ahead} commit(s)"
        return status

    path = repo_path(registry, entry)
    push = _run_git(path, "push", "origin", status.branch)
    if push.returncode != 0:
        status.error = push.stderr.strip() or "push failed"
        return status
    return inspect_repo(registry, entry)