"""Typer-based CLI for the Workflow Orchestrator.

Provides the ``workflow`` command with subcommands:
    - ``workflow run`` — Execute a YAML workflow.
    - ``workflow list`` — List available workflows.
    - ``workflow schedule`` — Schedule a workflow.
    - ``workflow scan`` — Scan a project directory.
    - ``workflow config`` — Manage configuration profiles.
    - ``workflow plugins`` — List registered plugins.
    - ``workflow reports`` — View execution reports.
    - ``workflow gui`` — Launch the interactive Rich menu (backward compat).

Usage:
    ```bash
    workflow run workflows/morning.yaml
    workflow list
    workflow scan .
    workflow config set active_profile home
    ```
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from workflow_orchestrator.engine import WorkflowEngine
from workflow_orchestrator.reports import list_reports, get_statistics, save_report
from workflow_orchestrator.scanner import ProjectScanner

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

app = typer.Typer(
    name="workflow",
    help="Workflow Orchestrator v2 — A reusable workflow automation framework.",
    add_completion=False,
)

console = Console()

# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@app.command()
def run(
    workflow_path: Annotated[
        str,
        typer.Argument(help="Path to the YAML workflow file"),
    ],
    profile: Annotated[
        str,
        typer.Option("--profile", "-p", help="Configuration profile to use"),
    ] = "default",
    context: Annotated[
        Optional[list[str]],
        typer.Option("--context", "-c", help="Context key=value pairs (can be repeated)"),
    ] = None,
) -> None:
    """Execute a YAML workflow file."""
    path = Path(workflow_path).expanduser().resolve()

    if not path.exists():
        console.print(f"[red]Error:[/] Workflow file not found: [yellow]{path}[/]")
        raise typer.Exit(code=1)

    from workflow_orchestrator.models import WorkflowDefinition
    from workflow_orchestrator.plugins.registry import default_registry

    # Discover plugins
    default_registry.discover()

    # Parse context
    ctx: dict[str, str] = {}
    if context:
        for item in context:
            if "=" in item:
                key, value = item.split("=", 1)
                ctx[key] = value

    with console.status(f"[bold cyan]Running workflow...[/]", spinner="dots"):
        workflow = WorkflowDefinition.from_yaml(path)
        engine = WorkflowEngine()
        report = engine.execute(workflow, context=ctx, profile=profile)

    # Save report
    report_path = save_report(report)

    # Display results
    _display_report(report, report_path)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@app.command()
def list_workflows(
    workflows_dir: Annotated[
        Optional[str],
        typer.Option("--dir", "-d", help="Directory containing YAML workflows"),
    ] = None,
) -> None:
    """List available workflow files."""
    search_dir = Path(workflows_dir).expanduser().resolve() if workflows_dir else _PROJECT_ROOT / "workflows"

    if not search_dir.exists():
        console.print(f"[yellow]Workflows directory not found: {search_dir}[/]")
        return

    yaml_files = sorted(search_dir.glob("*.yaml")) + sorted(search_dir.glob("*.yml"))

    if not yaml_files:
        console.print(f"[yellow]No YAML workflow files found in {search_dir}[/]")
        return

    table = Table(title=f"Available Workflows ({search_dir})")
    table.add_column("Name", style="cyan")
    table.add_column("File", style="green")
    table.add_column("Steps", justify="right")

    for f in yaml_files:
        try:
            from workflow_orchestrator.models import WorkflowDefinition
            wf = WorkflowDefinition.from_yaml(f)
            table.add_row(wf.name, f.name, str(len(wf.steps)))
        except Exception:
            table.add_row(f.stem, f.name, "[red]error[/]")

    console.print(table)


# ---------------------------------------------------------------------------
# schedule
# ---------------------------------------------------------------------------


@app.command()
def schedule(
    workflow_path: Annotated[
        str,
        typer.Argument(help="Path to the YAML workflow file"),
    ],
    schedule_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Schedule type: once, daily, weekly, startup, cron"),
    ] = "daily",
    time: Annotated[
        str,
        typer.Option("--time", help="Time in HH:MM format (for daily/weekly)"),
    ] = "09:00",
    day: Annotated[
        str,
        typer.Option("--day", help="Day of week (for weekly)"),
    ] = "mon",
    cron: Annotated[
        str,
        typer.Option("--cron", help="Cron expression (for cron type)"),
    ] = "",
) -> None:
    """Schedule a workflow for automatic execution."""
    path = Path(workflow_path).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]Error:[/] Workflow file not found: {path}")
        raise typer.Exit(code=1)

    from workflow_orchestrator.scheduler import WorkflowScheduler
    from workflow_orchestrator.plugins.registry import default_registry

    default_registry.discover()

    scheduler = WorkflowScheduler()
    scheduler.start()

    job_id = scheduler.add_job(
        str(path),
        schedule_type=schedule_type,
        time=time,
        day=day,
        cron_expression=cron,
    )

    if job_id:
        console.print(
            f"[green]✓[/] Scheduled '[cyan]{path.stem}[/]' "
            f"({schedule_type}) — Job ID: [yellow]{job_id}[/]"
        )
        console.print("Press Ctrl+C to stop.")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
            console.print("\n[yellow]Scheduler stopped.[/]")
    else:
        console.print("[red]Failed to schedule workflow.[/]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


@app.command()
def scan(
    path: Annotated[
        str,
        typer.Argument(help="Path to the project directory to scan"),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
) -> None:
    """Scan a project directory and report detected technologies."""
    project_path = Path(path).expanduser().resolve()
    if not project_path.exists():
        console.print(f"[red]Error:[/] Path not found: {project_path}")
        raise typer.Exit(code=1)

    with console.status(f"[bold cyan]Scanning project...[/]", spinner="dots"):
        scanner = ProjectScanner()
        info = scanner.scan(project_path)

    if json_output:
        import json
        console.print(json.dumps(info.to_dict(), indent=2))
        return

    # Display as Rich table
    table = Table(title=f"Project Scan: {info.name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Root", str(info.root))
    table.add_row("Languages", ", ".join(info.languages) or "[dim]none detected[/]")
    table.add_row("Git", "[green]✓[/]" if info.has_git else "[red]✗[/]")
    table.add_row("Docker", "[green]✓[/]" if info.has_docker else "[red]✗[/]")
    table.add_row("Package Manager", info.package_manager or "[dim]none[/]")
    table.add_row("Python", info.python_version or "[dim]not detected[/]")
    table.add_row("Node.js", info.node_version or "[dim]not detected[/]")
    table.add_row("Java", info.java_version or "[dim]not detected[/]")
    table.add_row("Rust", info.rust_toolchain or "[dim]not detected[/]")
    table.add_row("Frameworks", ", ".join(info.frameworks) or "[dim]none[/]")
    table.add_row("Scripts", ", ".join(info.scripts[:10]) or "[dim]none[/]")
    table.add_row("Dependencies", str(info.dependencies) or "0")
    table.add_row("Dev Dependencies", str(info.dev_dependencies) or "0")

    console.print(table)


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------


@app.command()
def config(
    action: Annotated[
        str,
        typer.Argument(help="Action: show, set, list-profiles, switch-profile"),
    ] = "show",
    key: Annotated[
        Optional[str],
        typer.Argument(help="Configuration key (for 'set' action)"),
    ] = None,
    value: Annotated[
        Optional[str],
        typer.Argument(help="Configuration value (for 'set' action)"),
    ] = None,
) -> None:
    """Manage configuration and profiles."""
    from config import config_manager

    if action == "show":
        cfg = config_manager.config
        table = Table(title="Current Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Active Profile", cfg.active_profile or "default")
        table.add_row("Brave Path", cfg.brave_executable_path or "[dim]not set[/]")
        table.add_row("VS Code Path", cfg.vscode_executable_path)
        table.add_row("Project Directory", cfg.default_project_directory or "[dim]not set[/]")
        table.add_row("GitHub URL", cfg.github_repository_url or "[dim]not set[/]")
        table.add_row("Render URL", cfg.render_dashboard_url or "[dim]not set[/]")
        table.add_row("Vercel URL", cfg.vercel_dashboard_url or "[dim]not set[/]")
        table.add_row("Freebuff Command", cfg.freebuff_command or "[dim]not set[/]")
        console.print(table)

    elif action == "set":
        if not key or value is None:
            console.print("[red]Usage:[/] workflow config set <key> <value>")
            raise typer.Exit(code=1)
        config_manager.set(key, value)
        console.print(f"[green]✓[/] Set [cyan]{key}[/] = [yellow]{value}[/]")

    elif action == "list-profiles":
        profiles = config_manager.list_profiles()
        table = Table(title="Available Profiles")
        table.add_column("Profile", style="cyan")
        table.add_column("Active", style="green")
        for profile in profiles:
            is_active = profile == config_manager.config.active_profile
            table.add_row(profile, "[green]✓[/]" if is_active else "")
        console.print(table)

    elif action == "switch-profile":
        if not key:
            console.print("[red]Usage:[/] workflow config switch-profile <profile_name>")
            raise typer.Exit(code=1)
        if config_manager.switch_profile(key):
            console.print(f"[green]✓[/] Switched to profile '[cyan]{key}[/]'")
        else:
            console.print(f"[red]Error:[/] Profile '[yellow]{key}[/]' not found.")
            raise typer.Exit(code=1)

    else:
        console.print(f"[red]Unknown action: {action}. Use: show, set, list-profiles, switch-profile[/]")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# plugins
# ---------------------------------------------------------------------------


@app.command()
def plugins() -> None:
    """List all registered plugins."""
    from workflow_orchestrator.plugins.registry import default_registry

    default_registry.discover()
    plugin_list = default_registry.list_plugins()

    if not plugin_list:
        console.print("[yellow]No plugins registered.[/]")
        return

    table = Table(title=f"Registered Plugins ({len(plugin_list)})")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Version", justify="right")

    for p in plugin_list:
        table.add_row(p["name"], p["description"][:60], p["version"])

    console.print(table)


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------


@app.command()
def reports(
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Number of recent reports to show"),
    ] = 10,
    stats: Annotated[
        bool,
        typer.Option("--stats", "-s", help="Show summary statistics"),
    ] = False,
) -> None:
    """View execution reports and statistics."""
    if stats:
        s = get_statistics()
        table = Table(title="Execution Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Runs", str(s["total_runs"]))
        table.add_row("Successful", str(s["successful_runs"]))
        table.add_row("Failed", str(s["failed_runs"]))
        table.add_row("Success Rate", f"{s['success_rate']}%")
        table.add_row("Total Duration", f"{s['total_duration']}s")
        table.add_row("Average Duration", f"{s['average_duration']}s")
        table.add_row("Most Run", s["most_run_workflow"] or "[dim]n/a[/]")
        console.print(table)

    reports_list = list_reports(limit=limit)
    if not reports_list:
        console.print("[yellow]No execution reports found.[/]")
        return

    table = Table(title=f"Recent Reports (last {limit})")
    table.add_column("Workflow", style="cyan")
    table.add_column("Timestamp", style="white")
    table.add_column("Duration", justify="right")
    table.add_column("Steps", justify="right")
    table.add_column("Status")

    for r in reports_list:
        status = "[green]✓ Success[/]" if r["success"] else f"[red]✗ Failed[/]"
        if r["error"]:
            status += f"\n[dim]{r['error'][:40]}[/]"
        table.add_row(
            r["workflow_name"],
            r["timestamp"][:19] if r["timestamp"] else "?",
            f"{r['duration']:.1f}s",
            f"{r['successful_steps']}/{r['total_steps']}",
            status,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _display_report(report, report_path: Path) -> None:
    """Display an execution report in the console."""
    from workflow_orchestrator.models import StepStatus
    from rich.progress import Progress, SpinnerColumn, TextColumn

    # Summary
    status_icon = "[green]✓[/]" if report.success else "[red]✗[/]"
    status_text = "Success" if report.success else "Failed"

    summary = Table(title=f"Workflow: {report.workflow_name}", show_header=False)
    summary.add_column("Property", style="cyan")
    summary.add_column("Value", style="green")
    summary.add_row("Status", f"{status_icon} {status_text}")
    summary.add_row("Duration", f"{report.duration:.2f}s")
    summary.add_row("Steps", f"{report.successful_steps}/{report.total_steps}")
    summary.add_row("Profile", report.profile)
    summary.add_row("Report", str(report_path))
    if report.error:
        summary.add_row("Error", f"[red]{report.error}[/]")

    console.print(summary)
    console.print()

    # Step details
    if report.steps:
        steps_table = Table(title="Step Details")
        steps_table.add_column("#", justify="right", style="dim")
        steps_table.add_column("Step", style="cyan")
        steps_table.add_column("Plugin", style="blue")
        steps_table.add_column("Duration", justify="right")
        steps_table.add_column("Status")
        steps_table.add_column("Message")

        for i, step in enumerate(report.steps, 1):
            if step.status == StepStatus.SUCCESS:
                status_display = "[green]✓[/]"
            elif step.status == StepStatus.FAILURE:
                status_display = "[red]✗[/]"
            elif step.status == StepStatus.SKIPPED:
                status_display = "[yellow]—[/]"
            else:
                status_display = "[dim]?[/]"

            steps_table.add_row(
                str(i),
                step.step_name[:40],
                step.plugin,
                f"{step.duration:.2f}s",
                status_display,
                step.message[:60] or "",
            )

        console.print(steps_table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def entry_point() -> None:
    """Console script entry point for ``workflow`` command."""
    app()


if __name__ == "__main__":
    entry_point()
