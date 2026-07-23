# Provider Configuration

## Overview

Providers are configured through YAML files in `providers/yaml/`. Each provider configuration defines its transport, authentication, capabilities, limits, and environment requirements.

## Configuration Schema

```yaml
# Required fields
name: "Provider Display Name"
id: "provider.id"
transport: "rest_api"  # rest_api, cli, browser, desktop, ssh, mcp

# Priority & Quality
priority: 1           # Lower = higher priority (1-10)
quality: 95           # Quality score (0-100)
cost: 5               # Cost score (1-10)

# Timeouts (seconds)
timeouts:
  connect: 30
  read: 120
  write: 60

# Retry configuration
retry:
  max_retries: 3
  backoff_base: 2.0
  backoff_max: 60.0

# Authentication
authentication:
  type: api_key           # api_key, oauth, cli_session, browser_login
  env_var: "API_KEY_ENV"
  location: "header"      # header, env, session
  header_name: "X-API-Key"
  header_prefix: "Bearer "

# Capabilities
capabilities:
  - text_generation
  - code_generation
  - code_review
  - analysis

# Rate limits
limits:
  max_tokens: 200000      # Context window
  max_concurrent: 5       # Concurrent requests
  rate_limit: 1000        # Requests per period
  rate_limit_period: "minute"

# Workspace defaults
workspace:
  default_model: "model-name"

# Environment requirements
environment:
  required_python: "3.9"
  required_memory_mb: 512
```

## Available Providers

| ID | Name | Transport | Priority |
|----|------|-----------|----------|
| `anthropic.claude` | Claude (Anthropic) | REST API | 1 |
| `openai.chatgpt` | ChatGPT (OpenAI) | REST API | 2 |
| `google.gemini` | Gemini (Google) | REST API | 3 |
| `openai.codex` | Codex CLI (OpenAI) | CLI | 4 |
| `cursor.editor` | Cursor (Editor Agent) | CLI | 5 |
| `github.copilot` | GitHub Copilot | CLI | 6 |

## Authentication Types

### API Key

```yaml
authentication:
  type: api_key
  env_var: "ANTHROPIC_API_KEY"
  location: "header"
  header_name: "x-api-key"
```

### OAuth

```yaml
authentication:
  type: oauth
  env_var: "GITHUB_TOKEN"
  location: "header"
  header_name: "Authorization"
  header_prefix: "Bearer "
```

### CLI Session

```yaml
authentication:
  type: cli_session
  location: "session"
```

### Browser Login

```yaml
authentication:
  type: browser_login
  location: "session"
```

## Capabilities

| Capability | Description |
|------------|-------------|
| `text_generation` | General text generation |
| `code_generation` | Code generation and editing |
| `code_review` | Code review and analysis |
| `code_completion` | Code completion suggestions |
| `code_editing` | Inline code editing |
| `analysis` | Deep analysis and reasoning |
| `planning` | Task and project planning |
| `reasoning` | Complex reasoning |
| `explanation` | Code and concept explanation |
| `documentation` | Documentation generation |
| `terminal_operations` | Terminal command execution |
| `file_operations` | File read/write operations |
| `git_operations` | Git command operations |

## Transport Types

| Transport | Description | Use Case |
|-----------|-------------|----------|
| `rest_api` | HTTP REST API | Cloud AI providers |
| `cli` | Command line interface | Local CLIs and agents |
| `browser` | Browser automation | Web-based providers |
| `desktop` | Desktop application | Chat desktop apps |
| `ssh` | SSH remote execution | Remote servers |
| `mcp` | Model Context Protocol | MCP servers |

## CLI Management

```bash
# Register a provider
workflow provider add claude

# Register with custom transport
workflow provider add claude --transport cli

# List registered providers
workflow provider list

# Remove a provider
workflow provider remove claude

# Log in to a provider
workflow login claude
```
