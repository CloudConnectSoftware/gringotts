"""Resolve cc_repos workspace root."""

from __future__ import annotations

import os
from pathlib import Path

GRINGOTTS_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = GRINGOTTS_ROOT / "operations" / "repos.yaml"


def default_workspace() -> Path:
    env = os.environ.get("GRINGOTTS_WORKSPACE")
    if env:
        return Path(env).resolve()
    return GRINGOTTS_ROOT.parent


def hermione_root(workspace: Path) -> Path:
    return workspace / "hermione"