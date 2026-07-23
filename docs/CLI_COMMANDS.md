# CLI Commands Reference

## Overview

The `workflow` CLI provides commands for workflow execution, provider management, automatic discovery, system diagnostics, and environment inspection.

## Core Commands

### `workflow run`

Execute a YAML workflow file.

```bash
workflow run <path> [--profile <name>] [--context <key=value>]
```

**Options:**
- `--profile, -p`: Configuration profile to use (default: "default")
- `--context, -c`: Context key=value pairs (can be repeated)

**Examples:**
```bash
workflow run workflows/morning_setup.yaml
workflow run workflows/build_app.yaml --profile home
workflow run workflows/deploy.yaml --context env=production --context branch=main
```

### `workflow list`

List available workflow files.

```bash
workflow list [--dir <path>]
```

**Options:**
- `--dir, -d`: Directory containing YAML workflows

### `workflow schedule`

Schedule a workflow for automatic execution.

```bash
workflow schedule <path> [--type <type>] [--time <HH:MM>] [--day <day>] [--cron <expr>]
```

**Options:**
- `--type, -t`: Schedule type (`once`, `daily`, `weekly`, `startup`, `cron`)
- `--time`: Time in HH:MM format (for daily/weekly)
- `--day`: Day of week (for weekly)
- `--cron`: Cron expression (for cron type)

### `workflow scan`

Scan a project directory for detected technologies.

```bash
workflow scan [<path>] [--json]
```

**Options:**
- `--json`: Output as JSON

### `workflow config`

Manage configuration and profiles.

```bash
workflow config <action> [<key>] [<value>]
```

**Actions:**
- `show`: Display current configuration
- `set <key> <value>`: Set a configuration value
- `list-profiles`: List available profiles
- `switch-profile <name>`: Switch active profile

## Setup & Diagnostics

### `workflow setup`

Interactive setup wizard. Guides through configuration, automatic discovery, provider registration, and project memory initialization.

```bash
workflow setup
```

### `workflow doctor`

Run complete system diagnostics. Checks providers, CLI tools, browsers, environment, workspace, and version compatibility.

```bash
workflow doctor
```

### `workflow environment`

Print the complete detected runtime environment including OS, hardware, languages, tools, workspace, and dependencies.

```bash
workflow environment
```

## Provider Management

### `workflow providers`

List all detected providers with health, capabilities, transport, and status.

```bash
workflow providers
```

### `workflow provider add`

Register and configure an AI provider.

```bash
workflow provider add <provider_id> [--api-key <key>] [--transport <type>]
```

### `workflow provider list`

List all registered providers.

```bash
workflow provider list
```

### `workflow provider remove`

Remove a registered provider.

```bash
workflow provider remove <provider_id>
```

### `workflow login`

Log in to an AI provider or service. Supports API key entry, OAuth, and browser-based login.

```bash
workflow login <provider_id> [--api-key <key>]
```

**Supported providers:**
- `claude`: API key from ANTHROPIC_API_KEY
- `chatgpt`: API key from OPENAI_API_KEY
- `gemini`: API key from GEMINI_API_KEY
- `github`: OAuth token from GITHUB_TOKEN
- `cursor`: CLI session login

## Agent Management

### `workflow agents`

List installed and detected coding agents with their type, transport, and status.

```bash
workflow agents
```

## Update Management

### `workflow update`

Check for updates to providers, agents, and the CLI.

```bash
workflow update [--all]
```

**Options:**
- `--all, -a`: Check all components

## Reporting

### `workflow reports`

View execution reports and statistics.

```bash
workflow reports [--limit <n>] [--stats]
```

**Options:**
- `--limit, -l`: Number of recent reports to show (default: 10)
- `--stats, -s`: Show summary statistics

### `workflow plugins`

List all registered plugins.

```bash
workflow plugins
```

## YAML Configuration Files

### Provider Configs (`providers/yaml/`)

Each provider configuration is stored as a YAML file:

```yaml
# claude.yaml
name: "Claude (Anthropic)"
id: "anthropic.claude"
transport: "rest_api"
priority: 1
quality: 95
cost: 5
authentication:
  type: api_key
  env_var: "ANTHROPIC_API_KEY"
capabilities:
  - text_generation
  - code_generation
  - code_review
limits:
  max_tokens: 200000
```

### Agent Configs (`agents/yaml/`)

```yaml
# claude_code.yaml
name: "Claude Code"
id: "claude_code"
provider_id: "anthropic.claude"
transport: "cli"
priority: 1
capabilities:
  - code_generation
  - code_editing
  - code_review
```

## Command Quick Reference

| Command | Description |
|---------|-------------|
| `workflow run <file>` | Execute a workflow |
| `workflow list` | List workflow files |
| `workflow schedule <file>` | Schedule a workflow |
| `workflow scan <path>` | Scan project |
| `workflow config show` | View configuration |
| `workflow setup` | Run setup wizard |
| `workflow doctor` | Run diagnostics |
| `workflow environment` | View environment |
| `workflow providers` | List providers |
| `workflow agents` | List agents |
| `workflow login <id>` | Log in to provider |
| `workflow update` | Check updates |
| `workflow reports` | View reports |
| `workflow plugins` | List plugins |
