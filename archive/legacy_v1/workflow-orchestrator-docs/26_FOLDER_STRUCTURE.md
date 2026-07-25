# 26 — Folder Structure

## Purpose
Defines the conceptual repository/package layout that mirrors the layered architecture in `02_ARCHITECTURE.md`, so implementers have an unambiguous place for every new module.

## Responsibilities
- Map architectural layers to top-level directories.
- Establish the convention that adapters (providers/agents/tools/deployment targets) live under a single `adapters/` root, never scattered.

## Goals
- Directory structure alone should communicate the dependency rule (Layer 1 code physically cannot import Layer 4 adapter code without an obviously-wrong cross-directory import).

## Non-Goals
- Does not prescribe language/build-tool specifics (package.json vs. pyproject.toml etc.) — purely conceptual.

## Architecture
```
workflow-orchestrator/
  core/                      # Layer 1 — deterministic orchestration
    workflow-engine/
    state-engine/
    execution-engine/
    event-bus/
    dependency-resolver/
    decision-engine/
  domain/                    # Layer 2 — domain services
    capability-registry/
    context-engine/
    project-contract/
    artifact-manager/
    verification-engine/
    error-recovery/
    resume-engine/
    report-engine/
    project-scanner/
    deployment-engine/
    supporting/              # metrics, policy, audit, resource, cache,
                              # workspace, notification, version, template-registry
  adapters/                  # Layer 3 — abstraction/adapters
    providers/
      anthropic-claude/
      chatgpt/
      gemini/
    agents/
      claude-code/
      cursor/
      codex/
      github-copilot/
      opencode/
      freebuff/
    tools/
      git/
      vscode/
      browser/
      terminal/
      clipboard/
    deployment-targets/
      vercel/
      render/
  plugins/                   # Plugin System runtime + installed plugin cache
  cli/                       # Layer 0 — entry points
    commands/
    live-view/
  config/                    # Configuration System defaults + schema
  docs/                      # this documentation set
```

## Interfaces
N/A.

## Data Models
N/A.

## Workflow
N/A — structural reference only.

## Examples
A new agent adapter is added entirely under `adapters/agents/<name>/`, registers via the Plugin System or built-in bootstrap, and never requires touching `core/`.

## Failure Scenarios
A contributor adds orchestration logic inside `adapters/` (e.g., retry logic that belongs in `core/execution-engine`) — code review should flag this as a layering violation.

## Future Expansion
A `daemon/` directory for the future background-process mode (`29_ROADMAP.md`).

## Trade-offs
A monorepo-style single structure is simpler to navigate than many small repos, at the cost of coarser-grained versioning; acceptable for a v1 open-source project.

## Open Questions
Should adapters eventually be split into separate repositories/packages once the plugin marketplace matures?

## References
`02_ARCHITECTURE.md`, `11_PLUGIN_SYSTEM.md`, `28_EXTENSION_GUIDE.md`
`docs/ARCHITECTURE_FREEZE.md` — Contains the definitive folder structure for v3.0.0.
This document's structure is aspirational; the frozen architecture defines the target.
