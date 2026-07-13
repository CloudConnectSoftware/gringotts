from pathlib import Path

import pytest
import yaml

from gringotts.vault_registry import (
    load_config_manifest,
    load_secrets_registry,
    parse_dotenv_keys,
    secret_status,
)


def test_load_secrets_registry_scope(tmp_path: Path):
    data = {
        "scopes": {
            "test": {
                "description": "Test scope",
                "vault_file": "test.env",
                "secrets": [
                    {"name": "FOO", "wizard": "foo", "required": True},
                    {"name": "BAR", "wizard": "bar", "required": False},
                ],
            }
        }
    }
    path = tmp_path / "secrets-registry.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    registry = load_secrets_registry(path)
    assert "test" in registry.scopes
    assert len(registry.scopes["test"].secrets) == 2


def test_secret_status_dotenv(tmp_path: Path):
    data = {
        "scopes": {
            "aci": {
                "vault_file": "aci.env",
                "secrets": [
                    {"name": "PRESENT", "wizard": "w", "required": True},
                    {"name": "ABSENT", "wizard": "w", "required": True},
                ],
            }
        }
    }
    reg_path = tmp_path / "secrets-registry.yaml"
    reg_path.write_text(yaml.dump(data), encoding="utf-8")
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "aci.env").write_text("PRESENT=secret\n", encoding="utf-8")

    registry = load_secrets_registry(reg_path)
    rows = secret_status(registry, "aci", vault_dir)
    by_name = {r["name"]: r["present"] for r in rows}
    assert by_name["PRESENT"] is True
    assert by_name["ABSENT"] is False


def test_parse_dotenv_keys_ignores_comments(tmp_path: Path):
    path = tmp_path / "x.env"
    path.write_text("# comment\nA=1\n\nB=two\n", encoding="utf-8")
    assert parse_dotenv_keys(path) == {"A", "B"}


def test_load_config_manifest(tmp_path: Path):
    data = {
        "config_files": [
            {
                "id": "sample",
                "repo": "portkey",
                "path": "foo.yaml",
                "template": "foo.example.yaml",
                "gitignored": True,
                "scope": "test",
            }
        ]
    }
    path = tmp_path / "config-manifest.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    manifest = load_config_manifest(path)
    assert len(manifest.files) == 1
    assert manifest.files[0].id == "sample"