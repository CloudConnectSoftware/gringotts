"""
gringotts.cli.app — Platform vault wizard for the modern platform.

IP vault: operations/repos.yaml (source repos).
Key vault: operations/secrets-registry.yaml + config-manifest.yaml + vault/ (gitignored).
No old_cloudtrade_repos.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from gringotts import __version__
from gringotts import git_ops
from gringotts.registry import load_registry
from gringotts.vault_registry import (
    default_vault_dir,
    load_config_manifest,
    load_secrets_registry,
    secret_status,
    vault_file_for_scope,
)
from gringotts.workspace import REGISTRY_PATH, default_workspace, hermione_root

console = Console()

app = typer.Typer(
    name="gringotts",
    help="Gringotts — IP vault (repos) + Key vault (secrets/config) for the modern platform.",
    add_completion=True,
    no_args_is_help=True,
)

repos_app = typer.Typer(help="Inspect the canonical repo registry")
sync_app = typer.Typer(help="Fetch, pull, and push registered repos")
keys_app = typer.Typer(help="Key vault — secret registry and local vault status")
config_app = typer.Typer(help="Config manifest — local config files and templates")
hermione_app = typer.Typer(help="Hermione documentation helpers")
app.add_typer(repos_app, name="repos")
app.add_typer(sync_app, name="sync")
app.add_typer(keys_app, name="keys")
app.add_typer(config_app, name="config")
app.add_typer(hermione_app, name="hermione")


def _load(scope: str, registry_file: Optional[Path]) -> tuple:
    registry = load_registry(registry_file)
    repos = registry.repos_for_scope(scope)
    return registry, repos


def _status_table(rows: list[git_ops.RepoStatus], title: str) -> Table:
    table = Table(title=title, show_header=True)
    table.add_column("Repo", style="cyan")
    table.add_column("Branch")
    table.add_column("HEAD")
    table.add_column("Sync")
    table.add_column("Policy", style="dim")
    for row in rows:
        policy = "pull_only" if not row.entry.may_push else "push_ok"
        table.add_row(
            row.entry.name,
            row.branch or "—",
            row.head or "—",
            row.sync_label,
            policy,
        )
    return table


@app.command()
def version():
    """Show gringotts version."""
    console.print(
        json.dumps(
            {
                "name": "gringotts",
                "version": __version__,
                "registry": str(REGISTRY_PATH),
            },
            indent=2,
        )
    )


@app.command()
def plan(
    scope: str = typer.Option("matador", "--scope", "-s"),
    registry_file: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Show registry path, workspace, and repos in a scope."""
    registry, repos = _load(scope, registry_file)
    console.print(Panel.fit(
        f"Registry: [cyan]{registry.source_path}[/]\n"
        f"Workspace: [cyan]{registry.workspace}[/]\n"
        f"Scope: [cyan]{scope}[/] — {len(repos)} repo(s)\n"
        f"Legacy [dim]old_cloudtrade_repos[/] is [bold]excluded[/] by design.",
        title="Gringotts Plan",
        border_style="yellow",
    ))
    table = Table(show_header=True)
    table.add_column("Repo", style="cyan")
    table.add_column("Track")
    table.add_column("Group")
    table.add_column("Owner")
    table.add_column("Policy")
    for entry in repos:
        table.add_row(
            entry.name,
            entry.tracking_branch,
            entry.group,
            entry.owner,
            "pull_only" if not entry.may_push else "push_master",
        )
    console.print(table)


@app.command()
def status(
    scope: str = typer.Option("matador", "--scope", "-s"),
    registry_file: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Git status for every repo in a scope (fetch first)."""
    registry, repos = _load(scope, registry_file)
    rows = [git_ops.fetch_repo(registry, entry) for entry in repos]
    console.print(_status_table(rows, f"Gringotts Status — scope '{scope}'"))


@repos_app.command("list")
def repos_list(
    scope: str = typer.Option("matador", "--scope", "-s"),
    registry_file: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """List repos in a scope from the registry (no git calls)."""
    _, repos = _load(scope, registry_file)
    for entry in repos:
        policy = "pull_only" if not entry.may_push else "push_master"
        console.print(
            f"  [cyan]{entry.name}[/]  track={entry.tracking_branch}  "
            f"owner={entry.owner}  {policy}"
        )


@repos_app.command("scopes")
def repos_scopes(registry_file: Optional[Path] = typer.Option(None, "--registry", "-r")):
    """List available sync scopes."""
    registry = load_registry(registry_file)
    for name, spec in registry.scopes.items():
        desc = spec.get("description", "")
        console.print(f"  [cyan]{name}[/] — {desc}")


@sync_app.command("pull")
def sync_pull(
    scope: str = typer.Option("matador", "--scope", "-s"),
    registry_file: Optional[Path] = typer.Option(None, "--registry", "-r"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Fetch and fast-forward pull every repo in scope."""
    registry, repos = _load(scope, registry_file)
    rows: list[git_ops.RepoStatus] = []
    for entry in repos:
        rows.append(git_ops.pull_repo(registry, entry, dry_run=dry_run))
    console.print(_status_table(rows, f"Gringotts Pull — scope '{scope}'"))


@sync_app.command("push")
def sync_push(
    scope: str = typer.Option("michael-push", "--scope", "-s"),
    registry_file: Optional[Path] = typer.Option(None, "--registry", "-r"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    """Push repos that are ahead of origin (push_master policy only)."""
    registry, repos = _load(scope, registry_file)
    rows: list[git_ops.RepoStatus] = []
    for entry in repos:
        rows.append(git_ops.push_repo(registry, entry, dry_run=dry_run))
    console.print(_status_table(rows, f"Gringotts Push — scope '{scope}'"))


@sync_app.command("fetch")
def sync_fetch(
    scope: str = typer.Option("matador", "--scope", "-s"),
    registry_file: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Fetch origin for every repo in scope (no pull)."""
    registry, repos = _load(scope, registry_file)
    rows = [git_ops.fetch_repo(registry, entry) for entry in repos]
    console.print(_status_table(rows, f"Gringotts Fetch — scope '{scope}'"))


@keys_app.command("scopes")
def keys_scopes():
    """List secret scopes in the Key Vault registry."""
    registry = load_secrets_registry()
    for name, spec in registry.scopes.items():
        console.print(f"  [cyan]{name}[/] — {spec.description}")


@keys_app.command("plan")
def keys_plan(
    scope: str = typer.Option("matador-aci", "--scope", "-s"),
):
    """Show Key Vault registry path, local vault dir, and secrets for a scope."""
    registry = load_secrets_registry()
    if scope not in registry.scopes:
        known = ", ".join(sorted(registry.scopes))
        console.print(f"[red]Unknown scope '{scope}'. Choose: {known}[/red]")
        raise typer.Exit(1)
    spec = registry.scopes[scope]
    vault_dir = default_vault_dir()
    vault_path = vault_file_for_scope(registry, scope, vault_dir)
    console.print(Panel.fit(
        f"Registry: [cyan]{registry.source_path}[/]\n"
        f"Vault dir: [cyan]{vault_dir}[/]\n"
        f"Scope: [cyan]{scope}[/] — {len(spec.secrets)} secret(s)\n"
        f"Vault file: [cyan]{vault_path}[/]\n"
        f"Doc: [dim]{spec.doc}[/]",
        title="Gringotts Key Vault",
        border_style="yellow",
    ))


@keys_app.command("list")
def keys_list(
    scope: str = typer.Option("matador-aci", "--scope", "-s"),
):
    """List secrets registered for a scope (names only — never values)."""
    registry = load_secrets_registry()
    if scope not in registry.scopes:
        known = ", ".join(sorted(registry.scopes))
        console.print(f"[red]Unknown scope '{scope}'. Choose: {known}[/red]")
        raise typer.Exit(1)
    table = Table(title=f"Secrets — scope '{scope}'", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Wizard")
    table.add_column("Required")
    table.add_column("Notes", style="dim")
    for entry in registry.scopes[scope].secrets:
        req = str(entry.required)
        table.add_row(entry.name, entry.wizard, req, entry.notes[:60])
    console.print(table)


@keys_app.command("status")
def keys_status_cmd(
    scope: str = typer.Option("matador-aci", "--scope", "-s"),
):
    """Report which registered secrets are present in the local vault file."""
    registry = load_secrets_registry()
    if scope not in registry.scopes:
        known = ", ".join(sorted(registry.scopes))
        console.print(f"[red]Unknown scope '{scope}'. Choose: {known}[/red]")
        raise typer.Exit(1)
    vault_dir = default_vault_dir()
    vault_path = vault_file_for_scope(registry, scope, vault_dir)
    rows = secret_status(registry, scope, vault_dir)
    table = Table(title=f"Key Vault Status — scope '{scope}'", show_header=True)
    table.add_column("Secret", style="cyan")
    table.add_column("Wizard")
    table.add_column("Required")
    table.add_column("Local")
    missing_required = 0
    for row in rows:
        label = "[green]set[/]" if row["present"] else "[red]missing[/]"
        req = str(row["required"])
        if row["required"] is True and not row["present"]:
            missing_required += 1
        table.add_row(row["name"], row["wizard"], req, label)
    console.print(table)
    if not vault_path.is_file():
        console.print(f"[yellow]Vault file not found: {vault_path}[/yellow]")
        console.print("Create it from Hermione secrets.md — values never go in git.")
    elif missing_required:
        console.print(f"[yellow]{missing_required} required secret(s) missing locally.[/yellow]")
    else:
        console.print("[green]All required secrets present in local vault file.[/green]")


@config_app.command("list")
def config_list():
    """List tracked config files (templates and gitignored local paths)."""
    manifest = load_config_manifest()
    workspace = default_workspace()
    table = Table(title="Config manifest", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Repo")
    table.add_column("Path")
    table.add_column("Scope")
    table.add_column("Gitignored")
    for entry in manifest.files:
        table.add_row(
            entry.id,
            entry.repo,
            entry.path,
            entry.scope,
            "yes" if entry.gitignored else "no",
        )
    console.print(table)
    console.print(f"Workspace: [cyan]{workspace}[/]")


@config_app.command("status")
def config_status():
    """Show whether each manifest config file exists (and template if applicable)."""
    manifest = load_config_manifest()
    workspace = default_workspace()
    table = Table(title="Config status", show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Local")
    table.add_column("Template")
    for entry in manifest.files:
        local = workspace / entry.repo / entry.path
        local_label = "[green]yes[/]" if local.is_file() else "[red]no[/]"
        if entry.template:
            tmpl = workspace / entry.repo / entry.template
            tmpl_label = "[green]yes[/]" if tmpl.is_file() else "[red]no[/]"
        else:
            tmpl_label = "—"
        table.add_row(entry.id, local_label, tmpl_label)
    console.print(table)


@hermione_app.command("paths")
def hermione_paths(
    registry_file: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Show key Hermione doc paths for Michael's coordination lane."""
    registry = load_registry(registry_file)
    root = hermione_root(registry.workspace)
    docs = root / "docs"
    lines = [
        f"Hermione root: [cyan]{root}[/]",
        "",
        "[bold]Matador thread (main):[/]",
        f"  {docs / 'operations' / 'matador.md'}",
        f"  {docs / 'operations' / 'matador' / 'standup.md'}",
        f"  {docs / 'operations' / 'matador' / 'michael.md'}",
        "",
        "[bold]Ideas parking lot (side quests):[/]",
        f"  {docs / 'operations' / 'ideas' / 'index.md'}",
        "",
        "[bold]Team docs (do not overwrite from coordination):[/]",
        f"  {docs / 'projects' / 'modern' / 'nostradamus.md'}  (Josh)",
        f"  {docs / 'projects' / 'modern' / 'palantir.md'}     (Cameron)",
        "",
        "After editing: [cyan]gringotts hermione build[/]",
    ]
    console.print(Panel("\n".join(lines), title="Hermione Paths", border_style="magenta"))


@hermione_app.command("build")
def hermione_build(
    registry_file: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Rebuild Hermione HTML site from markdown."""
    registry = load_registry(registry_file)
    root = hermione_root(registry.workspace)
    if not (root / "pyproject.toml").is_file():
        console.print(f"[red]Hermione not found at {root}[/red]")
        raise typer.Exit(1)
    console.print(Panel.fit(f"Building site in [cyan]{root / 'site'}[/]", title="Hermione Build"))
    result = subprocess.run(
        ["uv", "run", "hermione", "dev", "build"],
        cwd=root,
        check=False,
    )
    if result.returncode != 0:
        raise typer.Exit(result.returncode)
    console.print("[green]Site built.[/green] Open hermione/site/index.html")


if __name__ == "__main__":
    app()