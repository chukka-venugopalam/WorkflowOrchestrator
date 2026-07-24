"""Main entry point for the Workflow Orchestrator AI Operating System.

Boots the Orchestrator, executes the 14-step boot sequence, performs health checks,
displays the startup dashboard, and runs the interactive OS CLI menu.

Usage:
    python main.py          # Interactive AI Operating System CLI
    workflow doctor         # Diagnostics CLI command
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
from rich import box

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from workflow_orchestrator.orchestrator.orchestrator import Orchestrator
from workflow_orchestrator.orchestrator.first_run import SetupConfiguration

console = Console()


def render_os_header(orchestrator: Orchestrator) -> None:
    """Render the top dashboard banner with status of providers, MCP, and projects."""
    providers = orchestrator.provider_manager.discover_and_load()
    mcp_servers = orchestrator.mcp_manager.discover_and_list()
    sessions = orchestrator.project_flow.session_mgr.list_sessions()
    
    active_sessions = len([s for s in sessions if s.state in ("active", "created")])
    completed_sessions = len([s for s in sessions if s.state == "completed"])

    console.print()
    console.print(Panel("[bold magenta]═══ Workflow Orchestrator — AI Operating System ═══[/]", box=box.DOUBLE))

    prov_lines = []
    for p in providers:
        if p.enabled and (p.api_key_configured or p.status == "available"):
            prov_lines.append(f"[green]{p.name} ✓[/]")
        else:
            prov_lines.append(f"[dim]{p.name} (off)[/]")

    mcp_text = f"[bold cyan]MCP Servers:[/] {len([m for m in mcp_servers if m.enabled])} Connected"
    proj_text = f"[bold yellow]Projects:[/] {active_sessions} Active | {completed_sessions} Completed"

    header_table = Table(show_header=False, box=box.ROUNDED, border_style="cyan", expand=True)
    header_table.add_column("Section", style="bold white")
    header_table.add_column("Details")

    header_table.add_row("Providers", "  ".join(prov_lines[:6]))
    header_table.add_row("MCP Servers", mcp_text)
    header_table.add_row("Projects", proj_text)

    console.print(header_table)
    console.print()


def display_menu() -> None:
    """Display the 14-option AI Operating System Menu."""
    menu_items = [
        ("1", "Create Project"),
        ("2", "Continue Project"),
        ("3", "Projects"),
        ("4", "Providers"),
        ("5", "Agents"),
        ("6", "Knowledge"),
        ("7", "Contracts"),
        ("8", "Workflows"),
        ("9", "Sessions"),
        ("10", "Deployments"),
        ("11", "Settings"),
        ("12", "Diagnostics (workflow doctor)"),
        ("13", "Logs"),
        ("14", "Exit"),
    ]

    table = Table(show_header=False, border_style="dim", box=box.SIMPLE)
    table.add_column("Key", style="bold cyan", width=6)
    table.add_column("Action", style="bold white")

    for key, action in menu_items:
        table.add_row(key, action)

    console.print(table)
    console.print()


def handle_create_project(orchestrator: Orchestrator) -> None:
    """Option 1: Single-prompt automated project creation."""
    console.print("\n[bold cyan]═══ Create Project ═══[/]")
    idea = Prompt.ask("\n[bold yellow]Describe your project[/]")
    if not idea.strip():
        console.print("[yellow]Project description cannot be empty.[/]")
        return

    name = Prompt.ask("[bold yellow]Project name (optional, press Enter to auto-generate)[/]", default="")
    name_val = name.strip() if name.strip() else None

    console.print("\n[bold green]Launching AI Operating System Project Pipeline...[/]\n")
    rec = orchestrator.create_project(idea=idea, project_name=name_val)

    if rec.status == "completed":
        console.print(f"\n[bold green]✓ Project '{rec.project_name}' created and built successfully in {rec.duration_seconds:.1f}s![/]")
    else:
        console.print(f"\n[bold red]✗ Project build failed:[/] {rec.error}")


def handle_continue_project(orchestrator: Orchestrator) -> None:
    """Option 2: Resume an existing project."""
    sessions = orchestrator.project_flow.session_mgr.list_sessions()
    if not sessions:
        console.print("\n[yellow]No existing project sessions found to continue.[/]")
        return

    console.print("\n[bold cyan]Select Project to Resume:[/]")
    for idx, s in enumerate(sessions, 1):
        console.print(f"  [cyan]{idx}.[/] {s.session_id} (Project: {s.project_id or 'default'}, State: {s.state})")

    choice = Prompt.ask("Enter selection number", default="1")
    try:
        sel = int(choice) - 1
        if 0 <= sel < len(sessions):
            target = sessions[sel]
            orchestrator.project_flow.session_mgr.resume_session(target.session_id)
            console.print(f"[bold green]Resumed session {target.session_id}.[/]")
    except ValueError:
        console.print("[red]Invalid selection.[/]")


def handle_list_projects(orchestrator: Orchestrator) -> None:
    """Option 3: List all projects."""
    sessions = orchestrator.project_flow.session_mgr.list_sessions()
    table = Table(title="All Projects & Sessions", box=box.ROUNDED)
    table.add_column("Session ID", style="cyan")
    table.add_column("Project", style="white")
    table.add_column("State", style="green")
    table.add_column("Tasks", justify="right")

    for s in sessions:
        table.add_row(s.session_id, s.project_id or "default", s.state, str(len(s.tasks)))

    console.print(table)


def handle_providers(orchestrator: Orchestrator) -> None:
    """Option 4: Manage Providers."""
    providers = orchestrator.provider_manager.discover_and_load()
    table = Table(title="AI Providers", box=box.ROUNDED)
    table.add_column("Provider", style="bold cyan")
    table.add_column("Status", style="white")
    table.add_column("API Key", style="yellow")
    table.add_column("Transport", style="dim white")

    for p in providers:
        key_status = "Configured ✓" if p.api_key_configured else "Missing"
        table.add_row(p.name, p.status.upper(), key_status, p.preferred_transport)

    console.print(table)

    if Confirm.ask("\nConfigure an API key for a provider?", default=False):
        pid = Prompt.ask("Enter provider ID (e.g. claude, chatgpt, gemini)")
        key = Prompt.ask(f"Enter API Key for {pid}")
        if pid and key:
            orchestrator.provider_manager.configure_provider(pid, api_key=key)
            console.print(f"[bold green]Saved API key for {pid}.[/]")


def handle_agents(orchestrator: Orchestrator) -> None:
    """Option 5: List & Manage Agents."""
    agents = orchestrator.agent_manager.discover_agents()
    table = Table(title="Discovered AI Agents", box=box.ROUNDED)
    table.add_column("Agent ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Status", style="green")
    table.add_column("Version", style="dim white")

    for a in agents:
        table.add_row(a.agent_id, a.name, a.status.upper(), a.version)

    console.print(table)


def handle_knowledge(orchestrator: Orchestrator) -> None:
    """Option 6: Inspect Knowledge Base."""
    kb = orchestrator.project_flow.knowledge_base
    console.print(f"\n[bold cyan]Knowledge Base Store Count:[/] {kb.store.count} entry/entries")
    entries = kb.store.list_all()
    for e in entries[:10]:
        console.print(f"  • [{e.category}] {e.title}")


def handle_contracts(orchestrator: Orchestrator) -> None:
    """Option 7: Inspect Contracts."""
    cm = orchestrator.project_flow.contract_mgr
    console.print(f"\n[bold cyan]Project Contract Manager initialized.[/]")
    console.print(f"Active contract count: {len(cm.history.history)}")


def handle_workflows(orchestrator: Orchestrator) -> None:
    """Option 8: List Workflows."""
    wl = orchestrator.kernel.get_service("workflow_loader") if orchestrator.kernel.registry.has_service("workflow_loader") else None
    if wl:
        console.print(f"\n[bold cyan]Workflow Loader Formats:[/] {', '.join(wl.supported_formats)}")
    console.print("Built-in Workflows: build, test, verify, deploy, master")


def handle_sessions(orchestrator: Orchestrator) -> None:
    """Option 9: Manage Sessions."""
    sm = orchestrator.project_flow.session_mgr
    console.print(f"\n[bold cyan]Active Sessions:[/] {sm.count}")


def handle_deployments(orchestrator: Orchestrator) -> None:
    """Option 10: View Deployments."""
    console.print("\n[bold cyan]Deployment Targets:[/] Vercel, Render, Local Docker")


def handle_settings(orchestrator: Orchestrator) -> None:
    """Option 11: Application Settings."""
    cm = orchestrator.kernel.get_service("config_manager") if orchestrator.kernel.registry.has_service("config_manager") else None
    if cm:
        console.print(f"\n[bold cyan]Active Configuration Profile:[/] {cm.active_profile}")


def handle_diagnostics(orchestrator: Orchestrator) -> None:
    """Option 12: Run Diagnostics (workflow doctor)."""
    console.print("\n[bold cyan]Running System Diagnostics (workflow doctor)...[/]\n")
    rep = orchestrator.run_doctor()

    table = Table(title="Workflow Doctor Diagnostics Report", box=box.ROUNDED)
    table.add_column("Category", style="cyan")
    table.add_column("Check", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Message", style="dim white")

    for item in rep.items:
        st = f"[green]{item.status}[/]" if item.status == "OK" else (f"[yellow]{item.status}[/]" if item.status == "WARNING" else f"[red]{item.status}[/]")
        table.add_row(item.category, item.name, st, item.message)

    console.print(table)
    console.print(f"\n[bold]Summary:[/] Passed: [green]{rep.passed_count}[/], Warnings: [yellow]{rep.warning_count}[/], Failed: [red]{rep.failed_count}[/]\n")


def handle_logs(orchestrator: Orchestrator) -> None:
    """Option 13: View Logs."""
    console.print("\n[bold cyan]System Logs Directory:[/] workflow_orchestrator/logs")


def main() -> None:
    """Main application loop."""
    console.print("\n[bold cyan]Booting Workflow Orchestrator AI Operating System...[/]\n")
    orchestrator = Orchestrator.get_instance()
    boot_report = orchestrator.boot(show_dashboard=True)

    if not boot_report.success:
        console.print("[bold red]Boot Sequence encountered errors. Check diagnostics below.[/]")

    while True:
        try:
            render_os_header(orchestrator)
            display_menu()
            choice = Prompt.ask("[bold yellow]Select choice (1-14)[/]", default="12")

            if choice == "1":
                handle_create_project(orchestrator)
            elif choice == "2":
                handle_continue_project(orchestrator)
            elif choice == "3":
                handle_list_projects(orchestrator)
            elif choice == "4":
                handle_providers(orchestrator)
            elif choice == "5":
                handle_agents(orchestrator)
            elif choice == "6":
                handle_knowledge(orchestrator)
            elif choice == "7":
                handle_contracts(orchestrator)
            elif choice == "8":
                handle_workflows(orchestrator)
            elif choice == "9":
                handle_sessions(orchestrator)
            elif choice == "10":
                handle_deployments(orchestrator)
            elif choice == "11":
                handle_settings(orchestrator)
            elif choice == "12":
                handle_diagnostics(orchestrator)
            elif choice == "13":
                handle_logs(orchestrator)
            elif choice == "14":
                console.print("\n[bold green]Goodbye![/]\n")
                sys.exit(0)
            else:
                console.print("[yellow]Invalid option. Please select 1-14.[/]")

            Prompt.ask("\n[dim]Press Enter to return to main menu...[/]")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold green]Goodbye![/]\n")
            sys.exit(0)


if __name__ == "__main__":
    main()
