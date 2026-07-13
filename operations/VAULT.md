# Gringotts — two vaults

Gringotts is the **platform vault wizard**: one tool, two concerns.

| Vault | What | Registry | Values |
|-------|------|----------|--------|
| **IP vault** | Source code repos | `operations/repos.yaml` | GitHub (`gringotts sync pull/push`) |
| **Key vault** | Secrets, keys, local config | `operations/secrets-registry.yaml`, `operations/config-manifest.yaml` | `vault/` (gitignored) + Azure ACI secure env |

Legacy `old_cloudtrade_repos` stays **outside** both vaults — feature branches only.

## IP vault (shipped v0.1)

- Canonical list of modern-platform repos, owners, sync policy
- Scopes: `matador`, `michael-push`, …
- Commands: `plan`, `status`, `sync pull`, `sync push`

## Key vault (v0.2+)

**Problem today:** secret names are documented in Hermione (`matador/secrets.md`) and
scattered across repo `.env.example` files; actual values sit in Portal, ad-hoc notes,
gitignored yaml, and Cameron's pain-point ACI setup. No single executable checklist.

**Gringotts owns:**

1. **Secret registry** — machine-readable list of env vars per scope (`matador-aci`, `irc-client`, …)
2. **Config manifest** — which gitignored config files exist, which example to copy
3. **Local vault** — `vault/<scope>.env` on each machine; `keys status` reports missing keys
4. **Future:** `keys materialize` → generate repo `.env` for local dev; portkey reads vault for deploy checklists

**What Gringotts does NOT do (yet):**

- Store production secrets in git (ever)
- Replace Azure Key Vault for Ridcully runtime (`KeyVaultUri` remains the legacy bridge)
- Push secrets to ACI automatically (portkey human deploy gate stays)

## Command map (target)

| Command | Vault |
|---------|-------|
| `gringotts repos list` | IP |
| `gringotts sync pull` | IP |
| `gringotts keys plan/list/status` | Key |
| `gringotts config list/status` | Key |
| `gringotts hermione build` | Meta |

## Relationship to other docs

| Doc | Role |
|-----|------|
| `hermione/.../matador/secrets.md` | Human SSOT for matador env vars |
| Each repo `.env.example` | Per-wizard authoritative field list |
| `gringotts/operations/secrets-registry.yaml` | Executable index + `keys status` input |

Hermione prose wins for *meaning*; gringotts registry wins for *automation*.