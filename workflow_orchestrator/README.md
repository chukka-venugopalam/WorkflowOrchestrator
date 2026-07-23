# Workflow Orchestrator v2

A **reusable workflow automation framework** that lets you define, schedule, and execute automation workflows using YAML files and a plugin system.

## Features

### Core
- 🔧 **Workflow Engine** — Execute automation workflows step by step with error recovery
- 📜 **YAML Workflows** — Define workflows as simple YAML files
- 🧩 **Plugin System** — Extensible plugin architecture; add plugins without modifying the engine
- ⏰ **Scheduler** — Run workflows on a schedule (once, daily, weekly, startup, or cron)
- 📊 **Execution Reports** — JSON reports with timing, step details, and success/failure
- 🔍 **Project Scanner** — Auto-detect project languages, frameworks, and tools
- 🎨 **Rich CLI** — Beautiful colored output, progress bars, and tables (Rich + Typer)
- ⚙️ **Configuration Profiles** — Switch between home, work, laptop profiles (YAML-based)
- 🛡️ **Error Recovery** — Retry, continue, or stop on step failure

### Automation Actions (Plugins)

| Plugin      | Description                                      |
|-------------|--------------------------------------------------|
| `terminal`  | Run shell commands and capture output            |
| `browser`   | Open URLs in browser (GitHub, Render, Vercel)    |
| `vscode`    | Open VS Code with projects or files              |
| `git`       | Git status, add, commit, push                    |
| `clipboard` | Copy to / read from system clipboard             |
| `wait`      | Pause execution for N seconds                    |
| `open_app`  | Launch any desktop application                   |

## Installation

### Prerequisites
- Python 3.12 or higher
- pip (Python package manager)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/workflow_orchestrator.git
cd workflow_orchestrator

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package (for the `workflow` CLI command)
pip install -e .
```

## Usage

### Interactive Menu (Backward Compatible)

```bash
python main.py
```

This launches the Rich interactive menu with options for all automation actions.

### `workflow` CLI Command

```bash
# Run a YAML workflow
workflow run workflows/example.yaml

# List available workflows
workflow list

# Scan a project directory
workflow scan .

# View configuration
workflow config show

# Switch configuration profile
workflow config switch-profile home

# List profiles
workflow config list-profiles

# List registered plugins
workflow plugins

# View execution reports
workflow reports

# View execution statistics
workflow reports --stats

# Schedule a workflow
workflow schedule workflows/daily.yaml --type daily --time 09:00

# Run with a specific profile
workflow run workflows/example.yaml --profile home
```

## YAML Workflow Format

### Basic Example

```yaml
name: Morning Setup
description: Open development tools at the start of the day

steps:
  - open_app:
      app: code
      args: .

  - open_url:
      url: https://github.com

  - terminal:
      command: git status

  - wait:
      seconds: 3
```

### Full Format

```yaml
name: Git Sync
description: Sync changes with remote repository
tags: [git, daily]

steps:
  - name: Check Git Status
    plugin: git
    config:
      action: status

  - name: Stage Changes
    plugin: terminal
    config:
      command: git add -A
    on_failure: continue
    retry:
      max_retries: 2
      delay: 1.0
      backoff: 2.0

  - name: Commit
    plugin: terminal
    config:
      command: git commit -m "Auto-commit"
    on_failure: continue

  - name: Push
    plugin: git
    config:
      action: push
    on_failure: continue
```

### Step Configuration Reference

Each step supports:

| Field        | Description                                        | Default    |
|-------------|----------------------------------------------------|------------|
| `name`      | Human-readable step name (auto-generated if empty) | auto       |
| `plugin`    | Plugin identifier (long form only)                 | —          |
| `config`    | Plugin-specific configuration dictionary           | `{}`       |
| `on_failure`| Action on failure: `stop`, `continue`, `retry`     | `stop`     |
| `retry`     | Retry configuration (see below)                    | `max_retries: 0` |

Retry configuration:

| Field        | Description                                         | Default |
|-------------|-----------------------------------------------------|---------|
| `max_retries`| Maximum retry attempts (0 = no retry)               | `0`     |
| `delay`     | Seconds between retries                             | `1.0`   |
| `backoff`   | Exponential backoff multiplier                       | `1.0`   |

### Plugin Configurations

#### `terminal`
```yaml
- terminal:
    command: git status
    timeout: 30          # optional, default: 60
    cwd: /path/to/dir    # optional working directory
```

#### `browser`
```yaml
- browser:
    action: open_url     # open_url, open_github, open_render, open_vercel
    url: https://example.com
```

#### `git`
```yaml
- git:
    action: auto_commit_push  # status, add, commit, push, auto_commit_push
    message: "My commit message"
```

#### `vscode`
```yaml
- vscode:
    action: open_project   # open_project, open_file
    project: /path/to/project
p```

#### `wait`
```yaml
- wait:
    seconds: 5
    message: "Pausing..."
```

#### `clipboard`
```yaml
- clipboard:
    action: copy   # copy or paste
    text: "Some text to copy"
```

#### `open_app`
```yaml
- open_app:
    app: code
    args: .
    wait: false
```

## Configuration Profiles

Profiles are stored as YAML files in the `profiles/` directory.

```yaml
# profiles/home.yaml
name: home
description: Home development environment

brave_executable_path: ""
vscode_executable_path: "code"
default_project_directory: "~/projects"
github_repository_url: "https://github.com/yourusername/your-project"
render_dashboard_url: ""
vercel_dashboard_url: ""
freebuff_command: ""
```

Switch between profiles:
```bash
workflow config switch-profile home
```

## Plugin Development

Create a new plugin by subclassing `Plugin`:

```python
from workflow_orchestrator.models import StepResult
from workflow_orchestrator.plugins.base import Plugin, PluginMetadata
from workflow_orchestrator.plugins.registry import default_registry

class MyPlugin(Plugin):
    metadata = PluginMetadata(
        name="my_plugin",
        description="Does something useful",
        version="1.0.0",
    )

    def execute(self, step_config, context):
        # Your action logic here
        return self._success("Step Name", "Completed successfully!")

# Auto-register on import
default_registry.register(MyPlugin())
```

Save it as `plugins/my_plugin.py` — it will be auto-discovered.

## Project Structure

```
workflow_orchestrator/
├── main.py                  # Rich interactive menu (python main.py)
├── cli.py                   # Typer CLI (workflow command)
├── engine.py                # Workflow engine
├── config.py                # Configuration management (JSON + YAML profiles)
├── models.py                # Shared dataclasses
├── scanner.py               # Project scanner
├── scheduler.py             # APScheduler workflow scheduler
├── reports.py               # Execution report management
├── pyproject.toml           # Package config with console_scripts
├── requirements.txt         # Python dependencies
├── README.md                # This file
│
├── modules/                 # Core automation modules (v1 preserved)
│   ├── __init__.py
│   ├── browser.py
│   ├── clipboard.py
│   ├── terminal.py
│   ├── vscode.py
│   ├── github.py
│   ├── render.py
│   ├── vercel.py
│   ├── prompts.py
│   ├── logger.py
│   └── utils.py
│
├── plugins/                 # Plugin system (NEW in v2)
│   ├── __init__.py
│   ├── base.py              # Abstract base Plugin class
│   ├── registry.py          # Plugin registry
│   ├── browser_plugin.py    # Wraps modules/browser.py
│   ├── terminal_plugin.py   # Wraps modules/terminal.py
│   ├── vscode_plugin.py     # Wraps modules/vscode.py
│   ├── git_plugin.py        # Wraps modules/github.py
│   ├── clipboard_plugin.py  # Wraps modules/clipboard.py
│   ├── wait_plugin.py       # Simple delay step
│   └── open_app_plugin.py   # Generic app launcher
│
├── profiles/                # YAML configuration profiles (NEW)
│   ├── default.yaml
│   └── home.yaml
│
├── workflows/               # YAML workflow definitions (NEW)
│   ├── example.yaml
│   ├── morning_setup.yaml
│   └── git_sync.yaml
│
├── data/
│   ├── config.json          # Base configuration
│   └── history.json         # Execution history
│
├── reports/                 # Execution reports (JSON, auto-generated)
├── logs/                    # Log files (auto-generated)
└── prompts/                 # Prompt templates (v1 preserved)
```

## Development

```bash
# Install in development mode
pip install -e .

# Install dev dependencies
pip install -e ".[dev]"

# Run tests (once written)
pytest

# Type checking
mypy workflow_orchestrator

# Linting
ruff check workflow_orchestrator
```

## Migration from v1 to v2

### What changed:
- Added plugin system (`plugins/` directory)
- Added workflow engine (`engine.py`)
- Added YAML workflow support (`workflows/` directory)
- Added scheduler (`scheduler.py`, APScheduler)
- Added execution reports (`reports.py`, `reports/` directory)
- Added project scanner (`scanner.py`)
- Added Rich CLI (`python main.py` now has colored output)
- Added Typer CLI (`workflow` command)
- Added configuration profiles (`profiles/` directory, YAML format)
- Updated `config.py` for profile support and merging
- Updated `requirements.txt` with new dependencies

### Backward Compatibility:
- `python main.py` still works and now has a Rich interface
- All v1 menu items and action handlers are preserved
- `data/config.json` still works (profiles override it)
- `modules/` directory is unchanged

### New Dependencies:
- `PyYAML>=6.0`
- `rich>=13.0`
- `typer>=0.9.0`
- `apscheduler>=3.10.0`

### New Directories:
- `plugins/` — Plugin system
- `profiles/` — YAML configuration profiles
- `workflows/` — YAML workflow definitions
- `reports/` — Execution reports (auto-generated)

## Roadmap

### v2.1 (Next)
- Built-in workflow templates (GitHub Actions, CI/CD, deploy)
- Web dashboard for monitoring executions
- Slack/email notifications on workflow completion
- Environment variable interpolation in workflow steps
- Parallel step execution

### v3.0 (Future)
- Remote agent execution (run workflows on other machines)
- Visual workflow builder (drag-and-drop UI)
- Workflow marketplace (share plugins and workflows)
- AI-assisted workflow generation (context-aware suggestions)
- Cross-platform GUI application

## License

MIT
