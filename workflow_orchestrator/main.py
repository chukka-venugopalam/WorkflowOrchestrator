"""Main entry point for the Workflow Orchestrator.

This is the **Rich interactive CLI** menu (backward-compatible
with v1 usage via ``python main.py``).  For the Typer-based CLI,
use the ``workflow`` command instead.

Usage:
    python main.py          # Rich interactive menu
    workflow run ...        # Typer CLI (see cli.py)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich import print as rprint
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import config_manager
from modules.logger import setup_logger, logger
from modules.terminal import run_command
from modules.clipboard import copy_to_clipboard
from modules.browser import (
    open_url,
    open_github,
    open_render,
    open_render_logs,
    open_vercel,
)
from modules.vscode import open_vscode
from modules.github import auto_commit_and_push, git_status
from modules.render import open_dashboard as render_open_dashboard
from modules.render import open_logs as render_open_logs
from modules.vercel import open_dashboard as vercel_open_dashboard
from modules.vercel import open_deployment as vercel_open_deployment
from modules.prompts import load_template, format_prompt

from workflow_orchestrator.engine import WorkflowEngine
from workflow_orchestrator.plugins.registry import default_registry
from workflow_orchestrator.reports import list_reports, get_statistics, save_report
from workflow_orchestrator.scanner import ProjectScanner

HISTORY_FILE = PROJECT_ROOT / "data" / "history.json"
WORKFLOWS_DIR = PROJECT_ROOT / "workflows"

console = Console()


# ---------------------------------------------------------------------------
# History helpers (preserved from v1)
# ---------------------------------------------------------------------------


def load_history() -> list[dict[str, Any]]:
    """Load the execution history from the JSON file."""
    if not HISTORY_FILE.exists():
        return []

    try:
        data = HISTORY_FILE.read_text(encoding="utf-8")
        entries: list[dict[str, Any]] = json.loads(data)
        return entries
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load history: %s", exc)
        return []


def save_history(entry: dict[str, Any]) -> None:
    """Append an entry to the execution history."""
    history = load_history()
    history.insert(0, entry)

    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to save history: %s", exc)


def record_action(action: str, status: str, details: str = "") -> None:
    """Record an action in the history log."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "status": status,
        "details": details,
    }
    save_history(entry)


# ---------------------------------------------------------------------------
# Menu display (Rich)
# ---------------------------------------------------------------------------


def display_menu() -> None:
    """Print the Rich main CLI menu."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Workflow Orchestrator v2[/]",
        subtitle="Automation Framework",
    ))
    console.print()

    menu_items = [
        ("1", "Copy Prompt to Clipboard"),
        ("2", "Open Freebuff"),
        ("3", "Open VS Code"),
        ("4", "Git Push"),
        ("5", "Open GitHub"),
        ("6", "Open Render Dashboard"),
        ("7", "Open Render Logs"),
        ("8", "Open Vercel Dashboard"),
        ("9", "Open Website / Deployment URL"),
        ("10", "Run Custom Terminal Command"),
        ("11", "Configuration"),
        ("12", "Run Full Workflow"),
        ("13", "View History"),
        ("14", "Run YAML Workflow"),
        ("15", "Scan Project"),
        ("16", "View Reports"),
        ("17", "List Plugins"),
        ("18", "Exit"),
    ]

    table = Table(show_header=False, border_style="dim", box=None)
    table.add_column("Key", style="cyan", width=4)
    table.add_column("Action", style="white")

    for key, action in menu_items:
        table.add_row(key, action)

    console.print(table)
    console.print()


# ---------------------------------------------------------------------------
# Existing action handlers (preserved and enhanced with Rich)
# ---------------------------------------------------------------------------

def action_copy_prompt() -> None:
    """Prompt user for ChatGPT-generated text and copy it to clipboard."""
    console.rule("[bold cyan]Copy Prompt to Clipboard[/]")
    console.print("Paste the prompt generated by ChatGPT (Ctrl+Z then Enter to finish):")
    console.print()

    lines: list[str] = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    prompt_text = "\n".join(lines).strip()

    if not prompt_text:
        logger.warning("No prompt text entered.")
        console.print("[yellow]⚠  No text entered. Cancelled.[/]")
        return

    if copy_to_clipboard(prompt_text):
        console.print(f"[green]✓[/] Prompt copied to clipboard. ({len(prompt_text)} chars)")
        record_action("Copy prompt", "success", f"{len(prompt_text)} chars")
    else:
        console.print("[red]✗ Failed to copy to clipboard.[/]")
        record_action("Copy prompt", "failure")


def action_open_freebuff() -> None:
    """Launch Freebuff using the configured command."""
    console.rule("[bold cyan]Open Freebuff[/]")

    freebuff_cmd = config_manager.config.freebuff_command
    if not freebuff_cmd:
        logger.warning("Freebuff command is not configured.")
        console.print("[yellow]⚠  Freebuff command is not configured.[/]")
        console.print("   Set it in Configuration (option 11) or data/config.json.")
        record_action("Open Freebuff", "failure", "command not configured")
        return

    try:
        from modules.terminal import run_command_async
        run_command_async(freebuff_cmd)
        console.print(f"[green]✓[/] Freebuff launched: [cyan]{freebuff_cmd}[/]")
        logger.info("Freebuff launched: %s", freebuff_cmd)
        record_action("Open Freebuff", "success", freebuff_cmd)
    except Exception as exc:
        logger.error("Failed to launch Freebuff: %s", exc)
        console.print(f"[red]✗ Failed to launch Freebuff: {exc}[/]")
        record_action("Open Freebuff", "failure", str(exc))


def action_open_vscode() -> None:
    """Open VS Code with the configured project directory."""
    console.rule("[bold cyan]Open VS Code[/]")

    project_dir = config_manager.config.default_project_directory
    if not project_dir:
        logger.warning("Default project directory is not configured.")
        console.print("[yellow]⚠  Default project directory is not configured.[/]")
        console.print("   Set it in Configuration (option 11) or data/config.json.")

        custom = Prompt.ask("Enter project path", default="")
        if custom:
            project_dir = custom
        else:
            record_action("Open VS Code", "cancelled")
            return

    path = Path(project_dir).expanduser().resolve()
    if open_vscode(path):
        console.print(f"[green]✓[/] VS Code opened with project: [cyan]{path}[/]")
        record_action("Open VS Code", "success", str(path))
    else:
        console.print("[red]✗ Failed to open VS Code.[/]")
        record_action("Open VS Code", "failure", str(path))


def action_git_push() -> None:
    """Run git commit and push with optional custom message."""
    console.rule("[bold cyan]Git Push[/]")

    state = git_status()
    if state is None:
        console.print("[red]✗ Not a Git repository or project directory not configured.[/]")
        record_action("Git push", "failure", "not a Git repo or not configured")
        return

    console.print(f"   Branch: [cyan]{state.branch}[/]")
    console.print(f"   Changes: {len(state.untracked_files)} untracked, "
                  f"{len(state.modified_files)} modified, {len(state.staged_files)} staged")
    console.print(f"   Ahead: {state.ahead}, Behind: {state.behind}")

    if not state.has_changes and state.ahead == 0:
        console.print("\n[green]✓ No changes to push.[/]")
        return

    message = Prompt.ask("Commit message", default="")
    console.print()

    if auto_commit_and_push(message or None):
        console.print("[green]✓ Changes committed and pushed successfully.[/]")
        record_action("Git push", "success", state.branch)
    else:
        console.print("[red]✗ Git push failed. Check logs for details.[/]")
        record_action("Git push", "failure", state.branch)


def action_open_github() -> None:
    """Open the configured GitHub repository in browser."""
    console.rule("[bold cyan]Open GitHub[/]")
    if open_github():
        console.print("[green]✓ GitHub repository opened in browser.[/]")
        record_action("Open GitHub", "success")
    else:
        console.print("[red]✗ Failed to open GitHub. Is the URL configured?[/]")
        record_action("Open GitHub", "failure")


def action_open_render() -> None:
    """Open the Render dashboard in browser."""
    console.rule("[bold cyan]Open Render Dashboard[/]")
    if render_open_dashboard() or open_render():
        console.print("[green]✓ Render dashboard opened in browser.[/]")
        record_action("Open Render", "success")
    else:
        console.print("[red]✗ Failed to open Render. Is the URL configured?[/]")
        record_action("Open Render", "failure")


def action_open_render_logs() -> None:
    """Open the Render logs page in browser."""
    console.rule("[bold cyan]Open Render Logs[/]")
    if render_open_logs() or open_render_logs():
        console.print("[green]✓ Render logs opened in browser.[/]")
        record_action("Open Render Logs", "success")
    else:
        console.print("[red]✗ Failed to open Render logs. Is the URL configured?[/]")
        record_action("Open Render Logs", "failure")


def action_open_vercel() -> None:
    """Open the Vercel dashboard in browser."""
    console.rule("[bold cyan]Open Vercel Dashboard[/]")
    if vercel_open_dashboard() or open_vercel():
        console.print("[green]✓ Vercel dashboard opened in browser.[/]")
        record_action("Open Vercel", "success")
    else:
        console.print("[red]✗ Failed to open Vercel. Is the URL configured?[/]")
        record_action("Open Vercel", "failure")


def action_open_website() -> None:
    """Open a deployment URL in browser."""
    console.rule("[bold cyan]Open Website / Deployment URL[/]")
    url = Prompt.ask("Enter the website URL")

    if not url:
        console.print("[yellow]⚠  No URL entered. Cancelled.[/]")
        record_action("Open Website", "cancelled")
        return

    if open_url(url) or vercel_open_deployment(url):
        console.print(f"[green]✓[/] Opened: [cyan]{url}[/]")
        record_action("Open Website", "success", url)
    else:
        console.print("[red]✗ Failed to open URL.[/]")
        record_action("Open Website", "failure", url)


def action_run_command() -> None:
    """Prompt for and execute a custom terminal command."""
    console.rule("[bold cyan]Run Custom Terminal Command[/]")
    command = Prompt.ask("$ ")

    if not command:
        console.print("[yellow]⚠  No command entered. Cancelled.[/]")
        return

    console.print()
    with console.status("[cyan]Running command...[/]"):
        result = run_command(command)

    console.print("─" * 45)
    if result.stdout:
        console.print(result.stdout)
    if result.stderr:
        console.print(f"[red]{result.stderr}[/]")
    console.print("─" * 45)

    status_color = "green" if result.success else "red"
    console.print(f"Exit code: [{status_color}]{result.exit_code}[/]")

    record_action("Custom command", "success" if result.success else "failure", command)


def action_configuration() -> None:
    """Open the interactive configuration menu."""
    console.rule("[bold cyan]Configuration[/]")
    console.print("1. View current configuration")
    console.print("2. Edit configuration interactively")
    console.print("3. Reset to defaults")
    console.print("4. List profiles")
    console.print("5. Switch profile")
    console.print()

    choice = Prompt.ask("Select option", default="1")

    if choice == "1":
        cfg = config_manager.config
        table = Table(title="Current Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Active Profile", cfg.active_profile or "default")
        table.add_row("Brave Path", cfg.brave_executable_path or "(not set)")
        table.add_row("VS Code Path", cfg.vscode_executable_path)
        table.add_row("Project Dir", cfg.default_project_directory or "(not set)")
        table.add_row("GitHub URL", cfg.github_repository_url or "(not set)")
        table.add_row("Render URL", cfg.render_dashboard_url or "(not set)")
        table.add_row("Vercel URL", cfg.vercel_dashboard_url or "(not set)")
        table.add_row("Freebuff Cmd", cfg.freebuff_command or "(not set)")
        if cfg.custom:
            for k, v in cfg.custom.items():
                table.add_row(f"[dim]{k}[/]", str(v))
        console.print(table)
        console.print()

    elif choice == "2":
        config_manager.configure_interactive()
        record_action("Configure", "success")

    elif choice == "3":
        if Confirm.ask("Reset all configuration to defaults?"):
            from config import AppConfig
            config_manager._config = AppConfig()
            config_manager.save()
            console.print("[green]✓ Configuration reset to defaults.[/]")
            record_action("Reset config", "success")

    elif choice == "4":
        profiles = config_manager.list_profiles()
        table = Table(title="Available Profiles")
        table.add_column("Profile", style="cyan")
        table.add_column("Active", style="green")
        for profile in profiles:
            is_active = profile == config_manager.config.active_profile
            table.add_row(profile, "[green]✓[/]" if is_active else "")
        console.print(table)

    elif choice == "5":
        profile = Prompt.ask("Profile name")
        if config_manager.switch_profile(profile):
            console.print(f"[green]✓[/] Switched to profile '[cyan]{profile}[/]'")
            record_action("Switch profile", "success", profile)
        else:
            console.print(f"[red]✗ Profile '{profile}' not found.[/]")

    else:
        console.print("[red]Invalid option.[/]")


def action_view_history() -> None:
    """Display the execution history."""
    console.rule("[bold cyan]Execution History[/]")

    history = load_history()
    if not history:
        console.print("[yellow]No history recorded yet.[/]")
        return

    table = Table(title="Execution History (last 20)")
    table.add_column("#", justify="right", style="dim")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Action", style="white")
    table.add_column("Status")

    for i, entry in enumerate(history[:20], 1):
        ts = entry.get("timestamp", "?")[:19]
        action = entry.get("action", "?")[:30]
        status = entry.get("status", "?")

        if status == "success":
            status_display = "[green]success[/]"
        elif status == "failure":
            status_display = "[red]failure[/]"
        else:
            status_display = f"[yellow]{status}[/]"

        table.add_row(str(i), ts, action, status_display)

    console.print(table)
    if len(history) > 20:
        console.print(f"\n[dim]... and {len(history) - 20} more entries.[/]")
    console.print()


def action_run_yaml_workflow() -> None:
    """Run a YAML workflow file."""
    console.rule("[bold cyan]Run YAML Workflow[/]")

    # Show available workflows
    if WORKFLOWS_DIR.exists():
        yaml_files = sorted(WORKFLOWS_DIR.glob("*.yaml"))
        if yaml_files:
            console.print("Available workflows:")
            for i, f in enumerate(yaml_files, 1):
                console.print(f"  {i}. {f.name}")
            console.print()

    path_str = Prompt.ask("Path to workflow YAML file", default="")
    if not path_str:
        console.print("[yellow]Cancelled.[/]")
        return

    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        # Try relative to workflows directory
        alt_path = WORKFLOWS_DIR / path_str
        if alt_path.exists():
            path = alt_path
        else:
            console.print(f"[red]Workflow file not found: {path}[/]")
            return

    try:
        from workflow_orchestrator.models import WorkflowDefinition

        default_registry.discover()
        workflow = WorkflowDefinition.from_yaml(path)
        engine = WorkflowEngine()

        console.print(f"Running workflow: [cyan]{workflow.name}[/] ({len(workflow.steps)} steps)")
        console.print()

        report = engine.execute(workflow)
        report_path = save_report(report)

        # Display results
        if report.success:
            console.print(f"[green]✓[/] Workflow completed successfully!")
        else:
            console.print(f"[red]✗[/] Workflow failed: {report.error}")

        console.print(f"   Duration: {report.duration:.2f}s")
        console.print(f"   Steps: {report.successful_steps}/{report.total_steps}")
        console.print(f"   Report: {report_path}")

        # Show step details
        if report.steps:
            console.print()
            step_table = Table(title="Steps")
            step_table.add_column("#", justify="right", style="dim")
            step_table.add_column("Step", style="cyan")
            step_table.add_column("Plugin", style="blue")
            step_table.add_column("Duration", justify="right")
            step_table.add_column("Status")

            for i, step in enumerate(report.steps, 1):
                from workflow_orchestrator.models import StepStatus
                if step.status == StepStatus.SUCCESS:
                    s = "[green]✓[/]"
                elif step.status == StepStatus.FAILURE:
                    s = "[red]✗[/]"
                else:
                    s = f"[yellow]{step.status.value}[/]"
                step_table.add_row(str(i), step.step_name[:35], step.plugin, f"{step.duration:.2f}s", s)

            console.print(step_table)

        record_action("YAML workflow", "success" if report.success else "failure", path.name)

    except Exception as exc:
        logger.exception("Failed to run workflow: %s", exc)
        console.print(f"[red]Error running workflow: {exc}[/]")
        record_action("YAML workflow", "failure", str(exc))


def action_scan_project() -> None:
    """Scan a project directory."""
    console.rule("[bold cyan]Project Scanner[/]")

    path_str = Prompt.ask("Project path", default=".")
    project_path = Path(path_str).expanduser().resolve()

    if not project_path.exists():
        console.print(f"[red]Path not found: {project_path}[/]")
        return

    with console.status("[cyan]Scanning project...[/]"):
        scanner = ProjectScanner()
        info = scanner.scan(project_path)

    table = Table(title=f"Project: {info.name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Root", str(info.root))
    table.add_row("Languages", ", ".join(info.languages) or "[dim]none[/]")
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

    console.print(table)
    record_action("Project scan", "success", str(project_path))


def action_view_reports() -> None:
    """View execution reports and statistics."""
    console.rule("[bold cyan]Execution Reports[/]")

    # Show statistics
    s = get_statistics()
    stat_table = Table(title="Statistics")
    stat_table.add_column("Metric", style="cyan")
    stat_table.add_column("Value", style="green")
    stat_table.add_row("Total Runs", str(s["total_runs"]))
    stat_table.add_row("Success Rate", f"{s['success_rate']}%")
    stat_table.add_row("Avg Duration", f"{s['average_duration']}s")
    console.print(stat_table)
    console.print()

    # Show recent reports
    reports = list_reports(limit=10)
    if not reports:
        console.print("[yellow]No reports yet.[/]")
        return

    report_table = Table(title="Recent Reports")
    report_table.add_column("Workflow", style="cyan")
    report_table.add_column("Time", style="white")
    report_table.add_column("Duration", justify="right")
    report_table.add_column("Steps", justify="right")
    report_table.add_column("Status")

    for r in reports:
        status = "[green]Success[/]" if r["success"] else "[red]Failed[/]"
        report_table.add_row(
            r["workflow_name"],
            r["timestamp"][:19] if r["timestamp"] else "?",
            f"{r['duration']:.1f}s",
            f"{r['successful_steps']}/{r['total_steps']}",
            status,
        )

    console.print(report_table)


def action_list_plugins() -> None:
    """List all registered plugins."""
    console.rule("[bold cyan]Registered Plugins[/]")

    default_registry.discover()
    plugin_list = default_registry.list_plugins()

    if not plugin_list:
        console.print("[yellow]No plugins registered.[/]")
        return

    table = Table(title=f"Plugins ({len(plugin_list)})")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Version", justify="right")

    for p in plugin_list:
        table.add_row(p["name"], p["description"][:60], p["version"])

    console.print(table)


# ---------------------------------------------------------------------------
# Full workflow (preserved and enhanced with Rich)
# ---------------------------------------------------------------------------


def run_full_workflow() -> None:
    """Execute the complete AI-assisted coding workflow."""
    console.rule("[bold cyan]Full Workflow Execution[/]")
    record_action("Workflow started", "success")

    # Step 1: Task description
    console.print("[bold]Step 1/10:[/] Describe the task")
    task = Prompt.ask("What task are you working on?")
    console.print()

    # Step 2: ChatGPT prompt
    console.print("[bold]Step 2/10:[/] Paste the ChatGPT-generated prompt")
    console.print("(Ctrl+Z then Enter to finish)")
    console.print()

    lines: list[str] = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    prompt_text = "\n".join(lines).strip()
    if prompt_text:
        copy_to_clipboard(prompt_text)
        console.print("[green]✓ Prompt copied to clipboard.[/]")
    else:
        console.print("[yellow]⚠ No prompt text entered. Skipping clipboard copy.[/]")
    console.print()

    # Step 3: Launch Freebuff
    console.print("[bold]Step 3/10:[/] Launching Freebuff...")
    freebuff_cmd = config_manager.config.freebuff_command
    if freebuff_cmd:
        try:
            from modules.terminal import run_command_async
            run_command_async(freebuff_cmd)
            console.print("[green]✓ Freebuff launched.[/]")
        except Exception as exc:
            console.print(f"[yellow]⚠ Could not launch Freebuff: {exc}[/]")
    else:
        console.print("[yellow]⚠ Freebuff command not configured. Skipping.[/]")
    console.print()

    # Step 4: Wait for Freebuff completion
    console.print("[bold]Step 4/10:[/] Waiting for Freebuff to complete")
    Prompt.ask("Press Enter after Freebuff has finished generating/modifying code", default="")
    console.print("[green]✓ Confirmed.[/]")
    console.print()

    # Step 5: Open VS Code
    console.print("[bold]Step 5/10:[/] Opening VS Code...")
    project_dir = config_manager.config.default_project_directory
    if project_dir:
        path = Path(project_dir).expanduser().resolve()
        if open_vscode(path):
            console.print(f"[green]✓ VS Code opened with project: [cyan]{path}[/]")
        else:
            console.print("[yellow]⚠ Could not open VS Code.[/]")
    else:
        console.print("[yellow]⚠ Project directory not configured.[/]")
    console.print()

    # Step 6: Git push
    console.print("[bold]Step 6/10:[/] Checking Git status and pushing changes...")
    state = git_status()
    if state:
        console.print(f"   Branch: [cyan]{state.branch}[/]")
        if state.has_changes:
            commit_msg = f"Workflow: {task[:50]}" if task else ""
            if auto_commit_and_push(commit_msg):
                console.print("[green]✓ Changes committed and pushed.[/]")
            else:
                console.print("[red]✗ Git push failed. See logs.[/]")
        elif state.ahead > 0:
            auto_commit_and_push()
            console.print("[green]✓ Pushed pending commits.[/]")
        else:
            console.print("[green]✓ No new changes to push.[/]")
    else:
        console.print("[yellow]⚠ Git status unavailable.[/]")
    console.print()

    # Step 7: Open GitHub
    console.print("[bold]Step 7/10:[/] Opening GitHub...")
    if open_github():
        console.print("[green]✓ GitHub repository opened.[/]")
    else:
        console.print("[yellow]⚠ GitHub URL not configured.[/]")
    console.print()

    # Step 8: Open deployment platform
    console.print("[bold]Step 8/10:[/] Opening deployment platform...")
    platform = Prompt.ask("Deployment platform (render/vercel, or press Enter to skip)", default="")

    if platform == "render":
        if render_open_dashboard() or open_render():
            console.print("[green]✓ Render dashboard opened.[/]")
        else:
            console.print("[yellow]⚠ Render URL not configured.[/]")
    elif platform == "vercel":
        if vercel_open_dashboard() or open_vercel():
            console.print("[green]✓ Vercel dashboard opened.[/]")
        else:
            console.print("[yellow]⚠ Vercel URL not configured.[/]")
    else:
        console.print("Skipped.")
    console.print()

    # Step 9: Open deployed website
    console.print("[bold]Step 9/10:[/] Opening the deployed website...")
    deploy_url = Prompt.ask("Deployment URL (or press Enter to skip)", default="")
    if deploy_url:
        if open_url(deploy_url):
            console.print(f"[green]✓ Opened: [cyan]{deploy_url}[/]")
        else:
            console.print("[yellow]⚠ Could not open URL.[/]")
    else:
        console.print("Skipped.")
    console.print()

    # Step 10: Report
    console.rule("[bold cyan]Workflow Complete[/]")
    console.print(f"   Task: {task or '(not specified)'}")
    console.print("   Status: [green]✓ All steps executed[/]")
    console.print()
    record_action("Workflow completed", "success", task)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Main entry point. Displays the Rich menu and dispatches user choices."""
    # Ensure logs directory exists
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Initialize logger
    setup_logger("workflow_orchestrator", log_to_file=True, log_to_console=True)

    # Discover plugins
    default_registry.discover()

    logger.info("Workflow Orchestrator v2 started.")

    console.print()
    console.print(Panel.fit(
        "[bold cyan]Welcome to the Workflow Orchestrator v2[/]",
        subtitle="Type a menu number or press Enter to show the menu",
    ))

    while True:
        display_menu()
        choice = Prompt.ask("Select option", default="")

        if choice == "1":
            action_copy_prompt()
        elif choice == "2":
            action_open_freebuff()
        elif choice == "3":
            action_open_vscode()
        elif choice == "4":
            action_git_push()
        elif choice == "5":
            action_open_github()
        elif choice == "6":
            action_open_render()
        elif choice == "7":
            action_open_render_logs()
        elif choice == "8":
            action_open_vercel()
        elif choice == "9":
            action_open_website()
        elif choice == "10":
            action_run_command()
        elif choice == "11":
            action_configuration()
        elif choice == "12":
            run_full_workflow()
        elif choice == "13":
            action_view_history()
        elif choice == "14":
            action_run_yaml_workflow()
        elif choice == "15":
            action_scan_project()
        elif choice == "16":
            action_view_reports()
        elif choice == "17":
            action_list_plugins()
        elif choice == "18":
            console.print("\n[bold]Goodbye![/]")
            logger.info("Workflow Orchestrator exited.")
            break
        else:
            console.print("\n[red]Invalid option. Please enter a number between 1 and 18.[/]")

        console.print("\n" + "─" * 50)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Exited by user.[/]")
        logger.info("Workflow Orchestrator interrupted by user.")
        sys.exit(0)
    except Exception as exc:
        logger.exception("Unhandled exception: %s", exc)
        console.print(f"\n[red]An unexpected error occurred: {exc}[/]")
        sys.exit(1)
