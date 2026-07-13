# Gringotts local vault (gitignored)

This directory holds **secret values** and **local config** for Master's machine.

Nothing here is committed. The registry (`operations/secrets-registry.yaml`) and
config manifest (`operations/config-manifest.yaml`) describe *what* belongs here.

## Layout

| File | Scope | Format |
|------|-------|--------|
| `matador-aci.env` | `matador-aci` | `KEY=value` dotenv (one line per secret) |
| `irc-client.yaml` | `irc-client` | Copy from `portkey/portkey.irc.client.*.example.yaml` |

Override the vault root with `GRINGOTTS_VAULT` (absolute path).

## Commands

```powershell
gringotts keys plan --scope matador-aci
gringotts keys list --scope matador-aci
gringotts keys status --scope matador-aci
gringotts config list
gringotts config status
```

## Rules

- **IP vault** (`operations/repos.yaml`) — source repos; `gringotts sync pull`.
- **Key vault** (this folder + registries) — secrets and local config; never `sync push`.
- Production ACI values may also live in Azure Portal / `az container create --secure-environment-variables`.
  Gringotts tracks the canonical *names* either way.