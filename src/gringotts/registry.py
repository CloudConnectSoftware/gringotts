"""Load the canonical repo registry and resolve scopes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from gringotts.workspace import REGISTRY_PATH, default_workspace


@dataclass(frozen=True)
class RepoEntry:
    name: str
    tracking_branch: str
    group: str
    owner: str = "unknown"
    role: str = ""
    sync_policy: str = "push_master"  # push_master | pull_only

    @property
    def may_push(self) -> bool:
        return self.sync_policy == "push_master"


@dataclass
class Registry:
    workspace: Path
    groups: dict[str, dict[str, Any]]
    scopes: dict[str, dict[str, Any]]
    source_path: Path

    def repos_for_scope(self, scope: str) -> list[RepoEntry]:
        if scope not in self.scopes:
            known = ", ".join(sorted(self.scopes))
            raise KeyError(f"Unknown scope '{scope}'. Choose: {known}")

        spec = self.scopes[scope]
        seen: dict[str, RepoEntry] = {}

        for group_name in spec.get("groups", []):
            group = self.groups.get(group_name)
            if not group:
                continue
            for raw in group.get("repos", []):
                entry = _repo_from_raw(raw, group_name=group_name)
                seen[entry.name] = entry

        for raw in spec.get("repos", []):
            entry = _repo_from_raw(raw, group_name="(scope)")
            if entry.name in seen:
                seen[entry.name] = RepoEntry(
                    name=entry.name,
                    tracking_branch=entry.tracking_branch,
                    group=seen[entry.name].group,
                    owner=seen[entry.name].owner,
                    role=seen[entry.name].role,
                    sync_policy=seen[entry.name].sync_policy,
                )
            else:
                seen[entry.name] = entry

        return sorted(seen.values(), key=lambda r: r.name.lower())


def _repo_from_raw(raw: dict[str, Any] | str, *, group_name: str) -> RepoEntry:
    if isinstance(raw, str):
        raw = {"name": raw, "tracking_branch": "master"}
    return RepoEntry(
        name=raw["name"],
        tracking_branch=raw.get("tracking_branch", "master"),
        group=group_name,
        owner=raw.get("owner", "unknown"),
        role=raw.get("role", ""),
        sync_policy=raw.get("sync_policy", "push_master"),
    )


def load_registry(path: Path | None = None) -> Registry:
    registry_path = path or REGISTRY_PATH
    with registry_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    workspace_raw = data.get("workspace")
    workspace = Path(workspace_raw).resolve() if workspace_raw else default_workspace()

    return Registry(
        workspace=workspace,
        groups=data.get("groups", {}),
        scopes=data.get("scopes", {}),
        source_path=registry_path.resolve(),
    )