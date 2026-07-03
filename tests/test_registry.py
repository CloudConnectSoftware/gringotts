from pathlib import Path

import pytest
import yaml

from gringotts.registry import load_registry


def test_matador_scope_includes_runtime_and_meta(tmp_path: Path):
    registry_data = {
        "workspace": str(tmp_path),
        "groups": {
            "g1": {"repos": [{"name": "alpha", "tracking_branch": "master"}]},
            "g2": {"repos": [{"name": "beta", "tracking_branch": "main", "sync_policy": "pull_only"}]},
        },
        "scopes": {
            "matador": {"groups": ["g1", "g2"]},
            "michael-push": {"groups": ["g1"]},
        },
    }
    path = tmp_path / "repos.yaml"
    path.write_text(yaml.dump(registry_data), encoding="utf-8")

    registry = load_registry(path)
    matador = {r.name for r in registry.repos_for_scope("matador")}
    assert matador == {"alpha", "beta"}

    push = registry.repos_for_scope("michael-push")
    assert len(push) == 1
    assert push[0].name == "alpha"
    assert push[0].may_push is True

    beta = next(r for r in registry.repos_for_scope("matador") if r.name == "beta")
    assert beta.may_push is False


def test_unknown_scope_raises():
    registry = load_registry()
    with pytest.raises(KeyError, match="Unknown scope"):
        registry.repos_for_scope("not-a-real-scope")