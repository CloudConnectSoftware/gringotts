# Gringotts

**Gringotts** — the repo vault wizard. Canonical registry of modern-platform repos, with programmatic fetch/pull/push.

Does **not** manage `old_cloudtrade_repos` (legacy = feature branches only, human discretion).

## Quick start

```powershell
cd gringotts
uv sync

gringotts plan --scope matador
gringotts status --scope matador
gringotts sync pull --scope matador
gringotts sync push --scope michael-push
gringotts hermione build
```

## Registry

Source of truth: `operations/repos.yaml`

| Scope | Use |
|-------|-----|
| `matador` | All Operation Matador repos — status + pull |
| `michael-push` | Repos Michael may push to `master`/`main` |

## Hermione

Michael's coordination docs live in Hermione. After edits:

```powershell
gringotts hermione build
```

See `hermione/docs/operations/ideas/` for parked side quests (always link back to Matador).