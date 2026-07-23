# Setup Guide

## Quick Start

```bash
# Clone and set up
git clone <repository>
cd workflow-orchestrator

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
workflow setup
```

The setup wizard will guide you through:
1. Configuration (paths, URLs, preferences)
2. Automatic environment discovery
3. Provider registration
4. Project memory initialization

## Automatic Setup

```bash
# Full system diagnostics
workflow doctor

# View detected environment
workflow environment

# List detected providers
workflow providers

# List detected agents
workflow agents
```

## Provider Setup

### Claude

```bash
# Get API key from https://console.anthropic.com/
export ANTHROPIC_API_KEY="sk-ant-..."

# Register with orchestrator
workflow provider add claude

# Or use login command
workflow login claude
```

### ChatGPT

```bash
# Get API key from https://platform.openai.com/api-keys
export OPENAI_API_KEY="sk-..."

# Register
workflow provider add chatgpt

# Or use login
workflow login chatgpt
```

### Gemini

```bash
# Get API key from https://aistudio.google.com/app/apikey
export GEMINI_API_KEY="AIza..."

# Register
workflow provider add gemini

# Or use login
workflow login gemini
```

## Configuration Profiles

```bash
# List available profiles
workflow config list-profiles

# Switch profile
workflow config switch-profile home

# View current config
workflow config show

# Set a value
workflow config set brave_executable_path "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
```

## Verification

After setup, verify everything is working:

```bash
workflow doctor
```

This checks:
- Provider availability
- CLI tools (Python, Node, Git, Docker)
- Browser detection
- Environment health
- Version compatibility
- Authentication status

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Provider not detected | Check API key is set in environment |
| CLI tool not found | Install the tool and ensure it's in PATH |
| Health check failed | Run `workflow doctor` for diagnostics |
| Configuration issues | Run `workflow setup` to reconfigure |
| Permission errors | Check file permissions on `.state/` directory |

## Post-Setup

After successful setup, you can:

```bash
# Run a workflow
workflow run workflows/example.yaml

# Build a project autonomously
workflow build "Create a React dashboard"

# Schedule recurring tasks
workflow schedule workflows/morning_setup.yaml --type daily --time 09:00
```
