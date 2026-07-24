"""Typer-based CLI for the Workflow Orchestrator.

Provides the ``workflow`` command with subcommands:
    - ``workflow run`` — Execute a YAML workflow.
    - ``workflow list`` — List available workflows.
    - ``workflow schedule`` — Schedule a workflow.
    - ``workflow scan`` — Scan a project directory.
    - ``workflow config`` — Manage configuration profiles.
    - ``workflow plugins`` — List registered plugins.
    - ``workflow reports`` — View execution reports.
    - ``workflow setup`` — Interactive setup wizard.
    - ``workflow doctor`` — Run complete system diagnostics.
    - ``workflow login`` — Authenticate with a provider.
    - ``workflow providers`` — List providers with health.
    - ``workflow agents`` — List installed agents.
    - ``workflow environment`` — Print detected environment.
    - ``workflow update`` — Check for updates.
    - ``workflow provider`` — Manage AI provider configurations.
    - ``workflow gui`` — Launch the interactive Rich menu (backward compat).

Usage:
    ```bash
    workflow run workflows/morning.yaml
    workflow doctor
    workflow login claude
    workflow providers
    workflow environment
    workflow update
    ```
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.columns import Columns
from rich.layout import Layout
from rich import box

from workflow_orchestrator.engine import WorkflowEngine
from workflow_orchestrator.reports import list_reports, get_statistics, save_report
from workflow_orchestrator.scanner import ProjectScanner

# Ensure project root is importable
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

app = typer.Typer(
    name="workflow",
    help="Workflow Orchestrator v3 — A deterministic, provider-agnostic workflow operating system.",
    add_completion=False,
)

console = Console()

# ---------------------------------------------------------------------------
# Kernel helper
# ---------------------------------------------------------------------------


def _get_kernel() -> Any:
    """Get a bootstrapped kernel instance.

    Returns:
        A bootstrapped Kernel instance.
    """
    from workflow_orchestrator.core.kernel import Kernel
    kernel = Kernel.create_default()
    kernel.boot(register_defaults=True, discover_plugins=False, setup_signal_handlers=False)
    return kernel


# ---------------------------------------------------------------------------
# doctor — complete diagnostics
# ---------------------------------------------------------------------------


@app.command()
def doctor() -> None:
    """Run complete system diagnostics.

    Checks providers, transports, agents, authentication,
    workspace, CLI tools, environment, dependencies, and overall health.
    """
    from workflow_orchestrator.orchestrator.orchestrator import Orchestrator
    console.print("[bold cyan]═══ Workflow Orchestrator Diagnostics ═══[/]\n")

    orch = Orchestrator.get_instance()
    rep = orch.run_doctor()

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
    console.print(f"  Python: [cyan]{env_info.get('python_version', 'Unknown')}[/]")
    console.print(f"  Architecture: [cyan]{env_info.get('architecture', 'Unknown')}[/]")
    if env_info.get("has_gpu"):
        console.print(f"  GPU: [green]✓[/] {env_info.get('gpu_info', 'Available')}")

    # --- Workspace ---
    console.print("\n[bold]─ Workspace ─[/]")
    workspace_info = workspace_detector.detect()
    if workspace_info.get("name"):
        console.print(f"  Project: [cyan]{workspace_info.get('name')}[/]")
        console.print(f"  Type: [cyan]{workspace_info.get('project_type', 'Unknown')}[/]")
        if workspace_info.get("frameworks"):
            console.print(f"  Frameworks: [cyan]{', '.join(workspace_info['frameworks'])}[/]")
    else:
        console.print("  [yellow]Not in a recognized project[/]")

    # --- Version Compatibility ---
    console.print("\n[bold]─ Version Compatibility ─[/]")
    incompatible = version_manager.get_incompatible_components()
    if incompatible:
        for c in incompatible:
            console.print(f"  [red]✗[/] {c.component_id}: installed {c.installed_version}, min {c.min_version}")
            all_healthy = False
    else:
        console.print("  [green]All versions compatible[/]")

    # --- Environment Health ---
    console.print("\n[bold]─ System Health ─[/]")
    env_health = health_monitor.check_environment()
    for check in env_health.checks:
        if check.is_healthy:
            console.print(f"  [green]✓[/] {check.component_id}")
        else:
            console.print(f"  [red]✗[/] {check.component_id}: {check.error}")
            all_healthy = False

    # Summary
    console.print()
    if all_healthy:
        console.print("[bold green]═══ Everything Ready ═══[/]")
    else:
        console.print("[bold yellow]═══ Some Issues Found ═══[/]")
        console.print("Run [green]workflow setup[/] to configure missing components.")


# ---------------------------------------------------------------------------
# login — authenticate with a provider
# ---------------------------------------------------------------------------


@app.command()
def login(
    provider_id: Annotated[
        str,
        typer.Argument(help="Provider ID (claude, chatgpt, gemini, github, cursor)"),
    ],
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", "-k", help="API key (for API-key-based providers)"),
    ] = None,
) -> None:
    """Log in to an AI provider or service.

    Supports API key entry, OAuth flow, and browser-based login.
    """
    console.print(f"[bold cyan]═══ Login: {provider_id} ═══[/]\n")

    kernel = _get_kernel()
    credential_manager = kernel.get_service("credential_manager")

    provider_map = {
        "claude": {"type": "provider", "env_var": "ANTHROPIC_API_KEY"},
        "chatgpt": {"type": "provider", "env_var": "OPENAI_API_KEY"},
        "gpt": {"type": "provider", "env_var": "OPENAI_API_KEY"},
        "gemini": {"type": "provider", "env_var": "GEMINI_API_KEY"},
        "github": {"type": "service", "env_var": "GITHUB_TOKEN"},
        "cursor": {"type": "agent", "env_var": ""},
    }

    info = provider_map.get(provider_id.lower())
    if not info:
        console.print(f"[red]Unknown provider: {provider_id}[/]")
        console.print(f"Supported: {', '.join(provider_map.keys())}")
        raise typer.Exit(code=1)

    if info["type"] == "agent":
        console.print(f"[yellow]Cursor uses CLI session login.[/]")
        console.print("Open Cursor and sign in, then the orchestrator will detect it.")
        console.print("[green]✓[/] Login instructions displayed.")
        return

    env_var = info["env_var"]

    if api_key:
        # Validate the key format
        if len(api_key) < 10:
            console.print("[red]Invalid API key format. Keys are typically 20+ characters.[/]")
            raise typer.Exit(code=1)

        credential_manager.store(provider_id, api_key)
        console.print(f"[green]✓[/] API key stored securely for [cyan]{provider_id}[/]")
        console.print(f"   Set environment variable [yellow]{env_var}[/] to use it.")
    else:
        console.print(f"Enter your [cyan]{provider_id}[/] API key:")
        console.print(f"(This will be stored in {credential_manager.store_path})\n")

        try:
            key = input("API Key: ").strip()
            if key:
                credential_manager.store(provider_id, key)
                console.print(f"\n[green]✓[/] API key stored securely for [cyan]{provider_id}[/]")
            else:
                console.print("\n[yellow]No key entered. Login cancelled.[/]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Login cancelled.[/]")


# ---------------------------------------------------------------------------
# providers — list providers with health
# ---------------------------------------------------------------------------


@app.command()
def providers() -> None:
    """List all providers with health, capabilities, and status."""
    kernel = _get_kernel()
    provider_detector = kernel.get_service("provider_detector")
    health_monitor = kernel.get_service("health_monitor")

    table = Table(title="Providers", box=box.ROUNDED)
    table.add_column("Provider", style="cyan")
    table.add_column("Transport", style="blue")
    table.add_column("Capabilities", style="green")
    table.add_column("Health", style="yellow")
    table.add_column("Status")

    detected = provider_detector.detect_all()
    if not detected:
        console.print("[yellow]No providers detected. Run 'workflow setup' to configure providers.[/]")
        return

    for p in detected:
        provider_id = p.provider_id
        name = p.name or provider_id
        transport = p.transport or "unknown"

        # Check health
        health_check = health_monitor.get_last_check(provider_id)
        if health_check:
            health_icon = "[green]✓ Healthy[/]" if health_check.is_healthy else f"[red]✗ {health_check.status.value}[/]"
        else:
            health_icon = "[yellow]? Unknown[/]"

        table.add_row(
            name,
            transport,
            "[dim]auto-detected[/]",
            health_icon,
            "[green]Available[/]" if p.available else "[yellow]Detected[/]",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# agents — list installed agents
# ---------------------------------------------------------------------------


@app.command()
def agents() -> None:
    """List installed and detected coding agents."""
    kernel = _get_kernel()
    agent_detector = kernel.get_service("agent_detector")

    table = Table(title="Coding Agents", box=box.ROUNDED)
    table.add_column("Agent", style="cyan")
    table.add_column("Type", style="blue")
    table.add_column("Transport", style="green")
    table.add_column("Status")

    detected = agent_detector.detect_all()
    if not detected:
        console.print("[yellow]No coding agents detected.[/]")
        return

    for agent in detected:
        agent_id = agent.agent_id
        agent_name = agent.name or agent_id
        transport = agent.transport or "cli"
        agent_type = agent.agent_type or "generic"

        table.add_row(agent_name, agent_type, transport, "[green]✓ Available[/]")

    console.print(table)


# ---------------------------------------------------------------------------
# environment — print detected environment
# ---------------------------------------------------------------------------


@app.command()
def environment() -> None:
    """Print the detected runtime environment."""
    kernel = _get_kernel()
    environment_detector = kernel.get_service("environment_detector")
    workspace_detector = kernel.get_service("workspace_detector")
    tool_detector = kernel.get_service("tool_detector")
    dependency_detector = kernel.get_service("dependency_detector")

    env = environment_detector.detect()

    console.print("[bold cyan]═══ Environment ═══[/]\n")

    # System
    console.print("[bold]System[/]")
    sys_table = Table(show_header=False, box=box.SIMPLE)
    sys_table.add_column("Key", style="cyan")
    sys_table.add_column("Value", style="green")
    sys_table.add_row("OS", env.get("os", "Unknown"))
    sys_table.add_row("Platform", env.get("platform", "Unknown"))
    sys_table.add_row("Architecture", env.get("architecture", "Unknown"))
    sys_table.add_row("CPU Cores", str(env.get("cpu_count", "Unknown")))
    sys_table.add_row("RAM (GB)", str(env.get("ram_gb", "Unknown")))
    sys_table.add_row("Hostname", env.get("hostname", "Unknown"))
    if env.get("has_gpu"):
        sys_table.add_row("GPU", env.get("gpu_info", "Available"))
    console.print(sys_table)

    # Languages
    console.print("\n[bold]Languages & Runtimes[/]")
    lang_table = Table(show_header=False, box=box.SIMPLE)
    lang_table.add_column("Runtime", style="cyan")
    lang_table.add_column("Version", style="green")
    lang_table.add_row("Python", env.get("python_version", "Not detected"))
    lang_table.add_row("Node.js", env.get("node_version", "Not detected"))
    lang_table.add_row("Java", env.get("java_version", "Not detected"))
    lang_table.add_row("Go", env.get("go_version", "Not detected"))
    lang_table.add_row("Rust", env.get("rust_version", "Not detected"))
    lang_table.add_row(".NET", env.get("dotnet_version", "Not detected"))
    console.print(lang_table)

    # Tools
    console.print("\n[bold]Tools[/]")
    tools = tool_detector.detect_all()
    tool_table = Table(show_header=False, box=box.SIMPLE)
    tool_table.add_column("Tool", style="cyan")
    tool_table.add_column("Status", style="green")
    for tool in tools:
        status = "[green]✓[/]" if tool.available else "[red]✗[/]"
        tool_table.add_row(tool.name or "Unknown", status)
    console.print(tool_table)

    # Workspace
    console.print("\n[bold]Workspace[/]")
    workspace = workspace_detector.detect()
    ws_table = Table(show_header=False, box=box.SIMPLE)
    ws_table.add_column("Property", style="cyan")
    ws_table.add_column("Value", style="green")
    ws_table.add_row("Name", workspace.get("name", "Not detected"))
    ws_table.add_row("Type", workspace.get("project_type", "Unknown"))
    ws_table.add_row("Root", str(workspace.get("root", ".")))
    if workspace.get("frameworks"):
        ws_table.add_row("Frameworks", ", ".join(workspace["frameworks"]))
    if workspace.get("languages"):
        ws_table.add_row("Languages", ", ".join(workspace["languages"]))
    console.print(ws_table)

    # Dependencies
    console.print("\n[bold]Dependencies[/]")
    deps = dependency_detector.detect_all()
    if deps:
        dep_table = Table(show_header=False, box=box.SIMPLE)
        dep_table.add_column("Category", style="cyan")
        dep_table.add_column("Details", style="green")
        for dep in deps:
            dep_table.add_row(dep.get("category", "Unknown"), dep.get("details", ""))
        console.print(dep_table)
    else:
        console.print("  [dim]No dependencies detected[/]")


# ---------------------------------------------------------------------------
# update — check for updates
# ---------------------------------------------------------------------------


@app.command()
def update(
    check_all: Annotated[
        bool,
        typer.Option("--all", "-a", help="Check all components"),
    ] = False,
) -> None:
    """Check for updates to providers, agents, and the CLI."""
    console.print("[bold cyan]═══ Update Check ═══[/]\n")

    kernel = _get_kernel()
    update_manager = kernel.get_service("update_manager")
    version_manager = kernel.get_service("version_manager")

    with console.status("[bold cyan]Checking for updates...[/]"):
        update_report = update_manager.check_for_updates()

    if update_report.updates:
        table = Table(title=f"Updates Available ({len(update_report.updates)})")
        table.add_column("Component", style="cyan")
        table.add_column("Current", style="yellow")
        table.add_column("Latest", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Severity")

        for update_info in update_report.updates:
            severity_style = {
                "critical": "[red]Critical[/]",
                "high": "[bold]High[/]",
                "medium": "[yellow]Medium[/]",
                "low": "[dim]Low[/]",
                "optional": "[dim]Optional[/]",
            }.get(update_info.severity.value, "[dim]Unknown[/]")

            table.add_row(
                update_info.component_id,
                update_info.current_version,
                update_info.target_version,
                update_info.update_type.value,
                severity_style,
            )

        console.print(table)

        if update_report.critical_count:
            console.print(f"\n[red]⚠ {update_report.critical_count} critical update(s) available![/]")
    else:
        console.print("[green]✓[/] All components are up to date.")

    # Show version tracking
    versions = version_manager.list_versions()
    if versions:
        console.print()
        ver_table = Table(title="Tracked Versions")
        ver_table.add_column("Component", style="cyan")
        ver_table.add_column("Version", style="green")
        ver_table.add_column("Compatible")
        for v in versions:
            compat = "[green]✓[/]" if v.compatible else "[red]✗[/]"
            ver_table.add_row(v.component_id, v.installed_version, compat)
        console.print(ver_table)


# ---------------------------------------------------------------------------
# provider subcommand group
# ---------------------------------------------------------------------------


@app.group()
def provider() -> None:
    """Manage AI provider configurations."""
    pass


@provider.command("add")
def provider_add(
    provider_id: Annotated[
        str,
        typer.Argument(help="Provider ID (e.g., claude, chatgpt, gemini)"),
    ],
    api_key: Annotated[
        Optional[str],
        typer.Option("--api-key", "-k", help="API key for the provider"),
    ] = None,
    transport: Annotated[
        str,
        typer.Option("--transport", "-t", help="Transport type (rest_api, cli, browser)"),
    ] = "rest_api",
) -> None:
    """Register and configure an AI provider."""
    # Map short names to full provider IDs
    provider_map = {
        "claude": "anthropic.claude",
        "chatgpt": "openai.chatgpt",
        "gpt": "openai.chatgpt",
        "gemini": "google.gemini",
    }

    full_id = provider_map.get(provider_id.lower(), provider_id)

    # Get or create kernel
    kernel = _get_kernel()
    provider_registry = kernel.get_service("provider_registry")

    # Check if already registered
    existing = provider_registry.lookup(full_id)
    if existing:
        console.print(f"[yellow]Provider '{full_id}' is already registered. Using existing configuration.[/]")
    else:
        # Create the provider
        import importlib
        provider_class_map = {
            "anthropic.claude": "workflow_orchestrator.providers.implementations.ClaudeProvider",
            "openai.chatgpt": "workflow_orchestrator.providers.implementations.ChatGPTProvider",
            "google.gemini": "workflow_orchestrator.providers.implementations.GeminiProvider",
        }

        class_path = provider_class_map.get(full_id)
        if not class_path:
            console.print(f"[red]Unknown provider: {provider_id}[/]")
            console.print(f"Supported: {', '.join(provider_map.keys())}")
            raise typer.Exit(code=1)

        module_path, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        provider_cls = getattr(module, class_name)

        provider_instance = provider_cls()
        provider_registry.register(provider_instance)
        console.print(f"[green]✓[/] Registered provider: [cyan]{full_id}[/]")

    # Set API key if provided
    env_var_map = {
        "anthropic.claude": "ANTHROPIC_API_KEY",
        "openai.chatgpt": "OPENAI_API_KEY",
        "google.gemini": "GEMINI_API_KEY",
    }
    if api_key:
        env_var = env_var_map.get(full_id, f"{full_id.upper().replace('.', '_')}_API_KEY")
        console.print(f"[green]✓[/] API key set via environment variable: [cyan]{env_var}[/]")

    # Save provider config to project memory
    from workflow_orchestrator.runtime import ProjectMemory
    memory = ProjectMemory(Path.cwd())
    memory.initialize()
    providers = memory.load_providers()
    providers.append({
        "id": full_id,
        "transport": transport,
        "enabled": True,
        "api_key_env": env_var_map.get(full_id, ""),
    })
    memory.save_providers(providers)

    console.print(f"[green]✓[/] Provider configuration saved for: [cyan]{full_id}[/]")

    # Display available providers
    _display_provider_status(kernel)


@provider.command("list")
def provider_list() -> None:
    """List all registered providers with their status."""
    kernel = _get_kernel()
    _display_provider_status(kernel)


@provider.command("remove")
def provider_remove(
    provider_id: Annotated[
        str,
        typer.Argument(help="Provider ID to remove"),
    ],
) -> None:
    """Remove a registered provider."""
    kernel = _get_kernel()
    provider_registry = kernel.get_service("provider_registry")

    # Map short names
    provider_map = {
        "claude": "anthropic.claude",
        "chatgpt": "openai.chatgpt",
        "gpt": "openai.chatgpt",
        "gemini": "google.gemini",
    }
    full_id = provider_map.get(provider_id.lower(), provider_id)

    if provider_registry.unregister(full_id):
        console.print(f"[green]✓[/] Removed provider: [cyan]{full_id}[/]")

        # Update project memory
        from workflow_orchestrator.runtime import ProjectMemory
        memory = ProjectMemory(Path.cwd())
        if memory.exists():
            providers = [p for p in memory.load_providers() if p.get("id") != full_id]
            memory.save_providers(providers)
    else:
        console.print(f"[red]Provider '{full_id}' not found.[/]")
        raise typer.Exit(code=1)


def _display_provider_status(kernel: Any) -> None:
    """Display provider status table.

    Args:
        kernel: The kernel instance with registered services.
    """
    provider_registry = kernel.get_service("provider_registry")

    table = Table(title=f"Registered Providers ({provider_registry.count})")
    table.add_column("Provider ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Capabilities", justify="right")
    table.add_column("Status", style="yellow")

    for p in provider_registry.list_providers():
        manifest = p.manifest()
        status = "[green]Available[/]" if hasattr(p, "status") else "[yellow]Registered[/]"
        table.add_row(
            manifest.id,
            manifest.name,
            str(len(manifest.capabilities)),
            status,
        )

    console.print(table)


# ---------------------------------------------------------------------------
# setup — interactive wizard
# ---------------------------------------------------------------------------


@app.command()
def setup() -> None:
    """Interactive setup wizard for the Workflow Orchestrator.

    Guides the user through:
    1. Configuration setup
    2. Automatic discovery
    3. Provider registration
    4. Profile configuration
    5. Project memory initialization
    """
    console.print("[bold cyan]═══ Workflow Orchestrator Setup ═══[/]\n")

    # Step 1: Configuration
    console.print("[bold]Step 1: Configuration[/]\n")
    from workflow_orchestrator.config.config_manager import config_manager

    config_manager.configure_interactive()

    # Step 2: Automatic Discovery
    console.print("[bold]Step 2: Automatic Discovery[/]\n")
    kernel = _get_kernel()

    with console.status("[bold cyan]Detecting environment...[/]"):
        environment_detector = kernel.get_service("environment_detector")
        workspace_detector = kernel.get_service("workspace_detector")
        cli_manager = kernel.get_service("cli_manager")
        browser_manager = kernel.get_service("browser_manager")
        provider_detector = kernel.get_service("provider_detector")
        agent_detector = kernel.get_service("agent_detector")

        env = environment_detector.detect()
        workspace = workspace_detector.detect()
        tools = cli_manager.detect_all()
        browsers = browser_manager.detect_all()
        detected_providers = provider_detector.detect_all()
        detected_agents = agent_detector.detect_all()

    # Display discovery results
    console.print(f"  OS: [cyan]{env.get('os', 'Unknown')}[/]")
    console.print(f"  Python: [cyan]{env.get('python_version', 'Not found')}[/]")
    console.print(f"  Node.js: [cyan]{env.get('node_version', 'Not found')}[/]")

    if workspace.get("name"):
        console.print(f"  Workspace: [cyan]{workspace.get('name')}[/] ({workspace.get('project_type', 'unknown')})")

    available_tools = [t.name for t in tools if t.available]
    if available_tools:
        console.print(f"  Tools: [cyan]{', '.join(available_tools)}[/]")

    available_browsers = [b.name for b in browsers]
    if available_browsers:
        console.print(f"  Browsers: [cyan]{', '.join(available_browsers)}[/]")

    if detected_providers:
        provider_names = [p.name or p.provider_id for p in detected_providers]
        console.print(f"  Providers detected: [cyan]{', '.join(provider_names)}[/]")

    if detected_agents:
        agent_names = [a.name or a.agent_id for a in detected_agents]
        console.print(f"  Agents detected: [cyan]{', '.join(agent_names)}[/]")

    console.print()

    # Step 3: Project memory
    console.print("[bold]Step 3: Project Memory[/]\n")
    from workflow_orchestrator.runtime import ProjectMemory
    memory = ProjectMemory(Path.cwd())
    memory.initialize()
    console.print(f"[green]✓[/] Project memory initialized at [cyan].state/[/]\n")

    # Step 4: Provider registration
    console.print("[bold]Step 4: Provider Registration[/]\n")
    console.print("Register AI providers for the orchestrator to use.")
    console.print("Available: claude, chatgpt, gemini")
    console.print("You can skip this step and register providers later with 'workflow provider add'.\n")

    providers_to_register = ["claude", "chatgpt", "gemini"]
    for pid in providers_to_register:
        try:
            ans = input(f"Register {pid}? (y/N): ").strip().lower()
            if ans == "y":
                provider_registry = kernel.get_service("provider_registry")
                provider_map = {
                    "claude": ("anthropic.claude", "workflow_orchestrator.providers.implementations.ClaudeProvider"),
                    "chatgpt": ("openai.chatgpt", "workflow_orchestrator.providers.implementations.ChatGPTProvider"),
                    "gemini": ("google.gemini", "workflow_orchestrator.providers.implementations.GeminiProvider"),
                }

                full_id, class_path = provider_map[pid]
                module_path, class_name = class_path.rsplit(".", 1)
                import importlib
                module = importlib.import_module(module_path)
                provider_cls = getattr(module, class_name)

                provider_registry.register(provider_cls())
                console.print(f"  [green]✓ Registered {full_id}[/]")

                # Save to project memory
                providers = memory.load_providers()
                providers.append({"id": full_id, "enabled": True})
                memory.save_providers(providers)

                # Also save credential info
                credential_manager = kernel.get_service("credential_manager")
                ans_key = input(f"  Enter API key for {pid} (or press Enter to skip): ").strip()
                if ans_key:
                    credential_manager.store(pid, ans_key)
                    console.print(f"  [green]✓ API key stored[/]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Setup interrupted.[/]")
            break

    # Summary
    console.print("\n[bold cyan]═══ Setup Complete ═══[/]")
    console.print()
    console.print("Next steps:")
    console.print("  1. [green]workflow doctor[/] — Run complete diagnostics")
    console.print("  2. [green]workflow providers[/] — View registered providers")
    console.print("  3. [green]workflow agents[/] — View detected agents")
    console.print("  4. [green]workflow environment[/] — View your runtime environment")
    console.print("  5. [green]workflow run examples/build_web_app.yaml[/] — Run a workflow\n")


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


def _display_report(report: Any, report_path: Path) -> None:
    """Display an execution report in the console.

    Args:
        report: The execution report object.
        report_path: Path to the saved report file.
    """
    from workflow_orchestrator.models import StepStatus

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
