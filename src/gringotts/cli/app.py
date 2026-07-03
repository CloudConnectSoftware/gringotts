"""
gringotts.cli.app — Repo vault wizard for the modern platform.

Canonical registry in operations/repos.yaml. No old_cloudtrade_repos.
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
from gringotts.workspace import REGISTRY_PATH, hermione_root

console = Console()

app = typer.Typer(
    name="gringotts",
    help="Gringotts — repo registry and sync for the modern platform (not legacy).",
    add_completion=True,
    no_args_is_help=True,
)

repos_app = typer.Typer(help="Inspect the canonical repo registry")
sync_app = typer.Typer(help="Fetch, pull, and push registered repos")
hermione_app = typer.Typer(help="Hermione documentation helpers")
app.add_typer(repos_app, name="repos")
app.add_typer(sync_app, name="sync")
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