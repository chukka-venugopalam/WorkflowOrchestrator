"""Dashboards — Startup Dashboard and Project Execution Dashboard.

Renders rich terminal UI views summarizing system boot state, active providers,
connected MCP servers, project progress, graph execution, and current phase.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich import box

logger = logging.getLogger(__name__)
console = Console()


class StartupDashboard:
    """Renders the Startup Dashboard after application boot."""

    @staticmethod
    def render_boot_summary(boot_results: List[Any]) -> None:
        """Render the 14-step boot sequence summary table."""
        table = Table(title="Workflow Orchestrator — Boot Sequence", box=box.ROUNDED, header_style="bold cyan")
        table.add_column("Step", justify="right", style="bold yellow")
        table.add_column("Component", style="white")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim white")

        for res in boot_results:
            status_text = "[bold green]✓ PASSED[/]" if res.success else "[bold red]✗ FAILED[/]"
            table.add_row(str(res.step_number), res.name, status_text, res.details)

        console.print(Panel(table, border_style="cyan", expand=False))

    @staticmethod
    def render_main_dashboard(
        providers: List[Any],
        mcp_count: int,
        active_projects: int,
        completed_projects: int,
    ) -> None:
        """Render the primary system dashboard header."""
        header = Text("Workflow Orchestrator v3.0 — AI Operating System", style="bold magenta center")
        console.print(Panel(header, border_style="magenta"))

        # Providers status table
        prov_table = Table(title="Providers", box=box.SIMPLE_HEAD, header_style="bold blue")
        prov_table.add_column("Provider")
        prov_table.add_column("Status")

        for p in providers:
            status = "[green]✓ Active[/]" if getattr(p, "enabled", True) else "[dim]Disabled[/]"
            name = getattr(p, "name", str(p))
            prov_table.add_row(name, status)

        # Overview panel
        info_text = f"[bold green]MCP Servers:[/] {mcp_count} Connected\n"
        info_text += f"[bold cyan]Active Projects:[/] {active_projects}\n"
        info_text += f"[bold yellow]Completed Projects:[/] {completed_projects}\n"

        console.print(Columns([Panel(prov_table, border_style="blue"), Panel(info_text, title="System Summary", border_style="green")]))


class ProjectDashboard:
    """Renders real-time Project Dashboard during execution."""

    @staticmethod
    def render_project_status(
        project_name: str,
        current_phase: str,
        provider: str,
        agent: str,
        progress_pct: float,
        artifacts_count: int,
        contract_version: str,
        current_task: str,
        next_task: str,
        elapsed_seconds: float,
    ) -> None:
        """Render a complete live project status dashboard."""
        table = Table(title=f"Project Dashboard — {project_name}", box=box.HEAVY, header_style="bold green")
        table.add_column("Property", style="bold cyan")
        table.add_column("Value", style="white")

        table.add_row("Current Phase", current_phase.upper())
        table.add_row("Selected Provider", provider)
        table.add_row("Selected Agent", agent)
        table.add_row("Progress", f"{progress_pct:.1f}%")
        table.add_row("Artifacts Generated", str(artifacts_count))
        table.add_row("Contract Version", contract_version)
        table.add_row("Current Task", current_task)
        table.add_row("Next Task", next_task)
        table.add_row("Elapsed Time", f"{elapsed_seconds:.1f}s")

        console.print(Panel(table, border_style="green", expand=False))
