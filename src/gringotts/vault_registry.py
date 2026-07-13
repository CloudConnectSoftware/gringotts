"""Load Key Vault registries (secrets + config manifest)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from gringotts.workspace import GRINGOTTS_ROOT

SECRETS_REGISTRY_PATH = GRINGOTTS_ROOT / "operations" / "secrets-registry.yaml"
CONFIG_MANIFEST_PATH = GRINGOTTS_ROOT / "operations" / "config-manifest.yaml"


@dataclass(frozen=True)
class SecretEntry:
    name: str
    wizard: str
    required: bool | str
    notes: str = ""


@dataclass(frozen=True)
class SecretScope:
    name: str
    description: str
    doc: str
    vault_file: str
    secrets: list[SecretEntry]


@dataclass(frozen=True)
class ConfigFileEntry:
    id: str
    repo: str
    path: str
    template: str | None
    gitignored: bool
    scope: str
    description: str


@dataclass
class KeyVaultRegistry:
    scopes: dict[str, SecretScope]
    source_path: Path


@dataclass
class ConfigManifest:
    files: list[ConfigFileEntry]
    source_path: Path


def default_vault_dir() -> Path:
    env = os.environ.get("GRINGOTTS_VAULT")
    if env:
        return Path(env).resolve()
    return GRINGOTTS_ROOT / "vault"


def load_secrets_registry(path: Path | None = None) -> KeyVaultRegistry:
    source = path or SECRETS_REGISTRY_PATH
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    scopes: dict[str, SecretScope] = {}
    for name, spec in (data.get("scopes") or {}).items():
        secrets = [
            SecretEntry(
                name=s["name"],
                wizard=s.get("wizard", ""),
                required=s.get("required", False),
                notes=s.get("notes", ""),
            )
            for s in spec.get("secrets", [])
        ]
        scopes[name] = SecretScope(
            name=name,
            description=spec.get("description", ""),
            doc=spec.get("doc", ""),
            vault_file=spec.get("vault_file", f"{name}.env"),
            secrets=secrets,
        )
    return KeyVaultRegistry(scopes=scopes, source_path=source)


def load_config_manifest(path: Path | None = None) -> ConfigManifest:
    source = path or CONFIG_MANIFEST_PATH
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    files = [
        ConfigFileEntry(
            id=raw["id"],
            repo=raw.get("repo", ""),
            path=raw["path"],
            template=raw.get("template"),
            gitignored=bool(raw.get("gitignored", False)),
            scope=raw.get("scope", ""),
            description=raw.get("description", ""),
        )
        for raw in data.get("config_files", [])
    ]
    return ConfigManifest(files=files, source_path=source)


def parse_dotenv_keys(path: Path) -> set[str]:
    """Return variable names defined in a KEY=value dotenv file."""
    if not path.is_file():
        return set()
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line)
        if match:
            keys.add(match.group(1))
    return keys


def vault_file_for_scope(registry: KeyVaultRegistry, scope: str, vault_dir: Path | None = None) -> Path:
    vault_dir = vault_dir or default_vault_dir()
    spec = registry.scopes[scope]
    return vault_dir / spec.vault_file


def secret_status(registry: KeyVaultRegistry, scope: str, vault_dir: Path | None = None) -> list[dict[str, Any]]:
    spec = registry.scopes[scope]
    vault_path = vault_file_for_scope(registry, scope, vault_dir)
    present = parse_dotenv_keys(vault_path) if vault_path.suffix == ".env" else set()
    if vault_path.is_file() and vault_path.suffix != ".env":
        present = {"__file__"}

    rows: list[dict[str, Any]] = []
    for entry in spec.secrets:
        if vault_path.suffix != ".env":
            has = vault_path.is_file()
        else:
            has = entry.name in present
        rows.append(
            {
                "name": entry.name,
                "wizard": entry.wizard,
                "required": entry.required,
                "present": has,
                "notes": entry.notes,
            }
        )
    return rows