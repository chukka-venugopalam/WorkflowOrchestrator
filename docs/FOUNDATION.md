# Foundation — Workflow Orchestrator v3

> **Architecture Version:** 3.0.0
> **Phase:** 0 — Foundation Refactor
> **Status:** Complete

## Overview

This document describes the foundation of the Workflow Orchestrator v3 architecture. Phase 0 establishes the stable architectural foundation that all future features will build upon.

## Architecture Principles

1. **Determinism First** — Given the same inputs, control-flow decisions are reproducible.
2. **Strict Layering** — Control Plane (deterministic) and Intelligence Plane (non-deterministic) are strictly separated.
3. **Provider Independence** — No core component hard-codes assumptions about specific AI vendors.
4. **Interface over Implementation** — Every component communicates through declared interfaces.
5. **Immutable Audit Trail** — All state transitions are recorded in an append-only log.
6. **Human-in-the-Loop by Default** — Verification gates require explicit confirmation.
7. **Local-First** — No mandatory SaaS backend, no forced telemetry.

## Layer Architecture

```
Layer 0: CLI / Entry Points           →  Uses Layer 1 only
Layer 1: Core (Deterministic)        →  No imports from Layer 3 or 4
Layer 2: Domain Services             →  Layer 1 interfaces only
Layer 3: Adapters / Abstractions     →  Layer 2 interfaces only
Layer 4: External Systems            →  Never calls upward
```

## Folder Structure

```
workflow_orchestrator/
├── core/                # Layer 1 — Deterministic Orchestration
├── domain/              # Layer 2 — Domain Services (placeholder)
├── adapters/            # Layer 3 — Adapters (placeholder)
├── plugins/             # Plugin System
├── cli/                 # Layer 0 — CLI Entry Points
├── config/              # Unified Configuration System
├── data/                # Runtime data (config.json, state, artifacts)
├── profiles/            # YAML configuration profiles
├── workflows/           # YAML workflow definitions
├── reports/             # Execution reports (auto-generated)
├── prompts/             # Prompt templates
├── tests/               # Test suite
│   ├── unit/            # Unit tests
│   ├── integration/     # Integration tests
│   ├── conformance/     # Plugin/adapter conformance tests
│   └── fixtures/        # Test data
├── docs/                # Architecture documentation
├── modules/             # Legacy module implementations (v1/v2)
├── pyproject.toml
├── README.md
└── main.py              # Legacy Rich menu entry point
```

## Core Components (Layer 1)

### Kernel

The `Kernel` is the application entry point. It orchestrates:
- **Startup sequence** — configuration loading, plugin loading, service registration
- **Dependency injection** — through the `ServiceRegistry`
- **Lifecycle hooks** — startup/shutdown through the `LifecycleManager`
- **Plugin discovery** — automatic plugin loading
- **Graceful shutdown** — signal handling and clean teardown

```python
kernel = Kernel.create_default()
kernel.boot()
# ... application runs ...
kernel.shutdown()
```

### Service Registry (Dependency Injection)

The `ServiceRegistry` replaces all global mutable singletons. Services are registered and resolved through the registry:

```python
registry = ServiceRegistry()
registry.register("config", config_manager_instance)
registry.register_factory("engine", lambda r: WorkflowEngine(r.get("plugin_registry")))
engine = registry.get("engine")
```

Supports:
- Direct instance registration
- Lazy factory registration (with singleton caching)
- Type-safe resolution (`get_typed`)
- Service discovery

### Lifecycle Manager

The `LifecycleManager` manages ordered execution of startup and shutdown hooks:

```python
lifecycle = LifecycleManager()
lifecycle.on_startup("load_config", load_config, priority=HookPriority.CRITICAL)
lifecycle.on_shutdown("save_state", save_state)
lifecycle.run_startup()
```

Hooks run in priority order (CRITICAL → HIGH → NORMAL → LOW → LAST).

### Event Bus

The `EventBus` provides in-process publish/subscribe with typed events:

```python
bus = EventBus()
sub = bus.subscribe("step.*", lambda e: print(f"Step event: {e.type}"))
bus.publish(Event(type="step.completed", data={"step": "build"}))
bus.unsubscribe(sub)
```

Event taxonomy: `workflow.*`, `step.*`, `state.*`, `capability.*`, `provider.*`, `agent.*`, `deployment.*`, `plugin.*`, `verification.*`, `report.*`

### State Engine

The `StateEngine` manages workflow run state with an append-only transition log:

```python
store = FileSystemStateStore(Path("/tmp/states"))
engine = StateEngine(store=store)
run = engine.create_run("my-workflow")
engine.transition(run.run_id, "running")
engine.transition(run.run_id, "completed")
```

Key design:
- Write-ahead: transitions are logged BEFORE side effects
- Append-only: nothing is ever deleted
- Snapshot rebuild: current state is reconstructible from the log
- Heartbeat monitoring for crash detection

### Capability Registry

The `CapabilityRegistry` manages what capabilities are available:

```python
registry = CapabilityRegistry()
registry.register(CapabilityManifest(
    id="codegen.nextjs",
    provider_id="claude",
    quality=QualityLevel.STABLE,
))
result = registry.resolve(CapabilityRequirement(capability_id="codegen.nextjs"))
```

Capability IDs are namespaced: `codegen.*`, `reasoning.*`, `verify.*`, `deploy.*`, `tool.*`, `community.author.name`

### Workspace Manager

The `WorkspaceManager` provisions and tears down isolated workspaces:

```python
manager = WorkspaceManager(base_path=Path("/tmp/workspaces"))
handle = manager.provision(source_path=Path("/path/to/project"))
# ... use workspace at handle.root_path ...
manager.teardown(handle)
```

### Artifact Manager

The `ArtifactManager` stores artifacts with content-addressed storage:

```python
manager = ArtifactManager(base_path=Path("/tmp/artifacts"))
ref = manager.store(b"artifact content", source="build-step", tags=["output"])
content = manager.load(ref)
```

## Configuration System

The configuration system merges values from multiple sources with precedence (lowest to highest):

1. **Built-in defaults** — in `config/settings.py`
2. **Base JSON config** — `data/config.json`
3. **Active profile** — `profiles/{profile}.yaml`
4. **Environment variables** — `WO_*` prefix

```python
from workflow_orchestrator.config import ConfigurationManager, config_manager

# Get a value
path = config_manager.get("default_project_directory")

# Set a value
config_manager.set("log_level", "DEBUG")

# Switch profile
config_manager.switch_profile("home")
```

## Dependency Injection

All global mutable singletons have been removed. Services are resolved through the `ServiceRegistry`:

```python
# Before (bad):
from plugins.registry import default_registry
engine = WorkflowEngine()  # Hidden global dependency

# After (good):
registry = ServiceRegistry()
registry.register("plugin_registry", PluginRegistry())
engine = WorkflowEngine(registry=registry)  # Explicit dependency
```

## Getting Started

### Prerequisites
- Python 3.12+
- pip

### Installation

```bash
cd workflow_orchestrator
pip install -e .
```

### Basic Usage

```python
from workflow_orchestrator.core.kernel import Kernel

# Create and boot the kernel
kernel = Kernel.create_default()
kernel.boot()

# Access services
config = kernel.get_service("config")
event_bus = kernel.get_service("event_bus")

# Run a workflow
from workflow_orchestrator.engine import WorkflowEngine
from workflow_orchestrator.models import WorkflowDefinition

engine = WorkflowEngine(registry=kernel.get_service("plugin_registry"))
workflow = WorkflowDefinition.from_yaml("workflows/example.yaml")
report = engine.execute(workflow)

# Clean shutdown
kernel.shutdown()
```

### CLI

```bash
# Typer CLI
workflow run workflows/example.yaml
workflow list
workflow scan .

# Legacy Rich menu
python main.py
```

## Development

### Running Tests

```bash
cd workflow_orchestrator
pip install -e ".[dev]"
pytest tests/ -v
```

### Code Style

- Type hints everywhere
- Dataclasses for structured data
- Pydantic only when beneficial
- No global mutable state
- Small focused modules
- Test coverage for core components

## Migration Notes

### Breaking Changes

| Change | Impact | Migration |
|--------|--------|-----------|
| `config.py` moved to `config/` | Imports from `config` still work (shim) | Update imports to `workflow_orchestrator.config` |
| `default_registry` replaced by ServiceRegistry | `from plugins.registry import default_registry` still works | Use injected registry via Kernel |
| New `core/` package added | No breaking changes | No action needed |
| New `config/` package added | Backward compatible | No action needed |

### Remaining Phase 1 Work

1. **Split WorkflowEngine** — Extract ExecutionEngine from WorkflowEngine
2. **Implement Event-driven engine** — Wire EventBus into the engine
3. **Implement State engine integration** — Wire StateEngine into the engine
4. **Implement Capability routing** — Wire CapabilityRegistry into plugin resolution
5. **Implement Decision Engine** — Template-first planning
6. **Implement Context Engine** — Context assembly with budget enforcement
7. **Implement Project Contract** — Versioned contract management
8. **Implement Provider System** — First real AI provider adapter
9. **Add integration tests** — End-to-end workflow tests
10. **CI/CD configuration** — GitHub Actions, type checking, linting
