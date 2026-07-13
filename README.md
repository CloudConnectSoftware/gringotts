# Gringotts

**Gringotts** — the platform vault wizard. Two vaults, one CLI.

| Vault | Holds | Registry |
|-------|-------|----------|
| **IP vault** | Source code repos | `operations/repos.yaml` |
| **Key vault** | Secrets, keys, local config | `operations/secrets-registry.yaml`, `operations/config-manifest.yaml`, `vault/` (gitignored) |

Does **not** manage `old_cloudtrade_repos` (legacy = feature branches only, human discretion).

See `operations/VAULT.md` for the full design.

## Quick start

```powershell
cd gringotts
uv sync

# IP vault — repos
gringotts plan --scope matador
gringotts status --scope matador
gringotts sync pull --scope matador
gringotts sync push --scope michael-push

# Key vault — secrets (names only in git; values in vault/)
gringotts keys plan --scope matador-aci
gringotts keys list --scope matador-aci
gringotts keys status --scope matador-aci
gringotts config list
gringotts config status

gringotts hermione build
```

## Local vault

Copy `vault/README.md` layout. Populate `vault/matador-aci.env` with `KEY=value` lines
from [Hermione matador secrets](../hermione/docs/operations/matador/secrets.md).
Override location with `GRINGOTTS_VAULT`.

## Registry scopes

| Scope | Use |
|-------|-----|
| `matador` | All Operation Matador repos — status + pull |
| `michael-push` | Repos Michael may push to `master`/`main` |
| `matador-aci` | Matador container secret names + local vault checklist |
| `irc-client` | Company IRC portkey client config |

## Hermione

Michael's coordination docs live in Hermione. After edits:

```powershell
gringotts hermione build
```

See `hermione/docs/operations/ideas/` for parked side quests (always link back to Matador).