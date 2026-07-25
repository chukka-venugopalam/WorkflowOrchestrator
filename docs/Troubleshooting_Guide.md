# Workflow Orchestrator — Troubleshooting Guide

## Common Diagnostics & Fixes

### 1. Provider Missing API Key
- **Symptom**: Warning logged `Provider anthropic.claude initialized in simulation mode`.
- **Fix**: Set environment variable `export ANTHROPIC_API_KEY="sk-ant-..."` and re-run.

### 2. Developer CLI Agent Binary Not Found
- **Symptom**: `RuntimeError: Claude CLI not found at 'claude'`.
- **Fix**: Install the CLI global binary e.g. `npm install -g @anthropic-ai/claude-code` or set binary path explicitly in `AgentConfig`.

### 3. Out-of-Bounds Workspace Access Blocked
- **Symptom**: Approval gate error `Action Risk High: Path outside workspace bounds`.
- **Fix**: Ensure all relative paths are within `ProjectBuilderConfig.builder.project_root`.
