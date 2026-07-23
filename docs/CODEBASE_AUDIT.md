# Codebase Audit

> **Date:** 2026-07-19
> **Phase:** Phase 0 — Foundation Refactor
> **Status:** Final

## Current Structure

```
workflow_orchestrator/              # Main package
├── cli.py                          # Typer-based CLI (primary entry point)
├── config.py                       # Configuration Manager v2 (with profiles)
├── engine.py                       # WorkflowEngine (sequential step execution)
├── main.py                         # Rich interactive CLI menu (legacy v1)
├── models.py                       # Shared dataclasses (WorkflowStep, ExecutionReport, etc.)
├── reports.py                      # Report save/load/statistics
├── scanner.py                      # ProjectScanner (language/framework detection)
├── scheduler.py                    # APScheduler-based workflow scheduler
├── modules/                        # Tool capability implementations (9 modules)
│   ├── browser.py                  # Brave browser automation
│   ├── clipboard.py                # Clipboard operations (pyperclip)
│   ├── github.py                   # Git/GitHub automation
│   ├── logger.py                   # Centralized logging setup
│   ├── prompts.py                  # Prompt template management
│   ├── render.py                   # Render.com dashboard integration
│   ├── terminal.py                 # Shell command execution
│   ├── utils.py                    # Platform detection, path helpers
│   ├── vercel.py                   # Vercel dashboard integration
│   └── vscode.py                   # VS Code integration
├── plugins/                        # Plugin system (8 plugins)
│   ├── base.py                     # Plugin ABC + PluginMetadata
│   ├── registry.py                 # PluginRegistry + default_registry singleton
│   ├── browser_plugin.py           # Browser action wrapper
│   ├── clipboard_plugin.py         # Clipboard action wrapper
│   ├── git_plugin.py               # Git action wrapper
│   ├── open_app_plugin.py          # Desktop app launcher
│   ├── terminal_plugin.py          # Shell command wrapper
│   ├── vscode_plugin.py            # VS Code action wrapper
│   └── wait_plugin.py              # Time delay step
├── prompts/                        # Prompt template files
│   ├── template.txt
│   └── examples/
│       └── add_feature.txt
├── profiles/                       # YAML configuration profiles
│   ├── default.yaml
│   └── home.yaml
├── workflows/                      # YAML workflow definitions
│   ├── example.yaml
│   ├── git_sync.yaml
│   └── morning_setup.yaml
├── data/                           # Runtime data storage
│   └── config.json
├── reports/                        # Execution report storage
│   └── .gitkeep
├── logs/                           # Log files (auto-generated)
├── pyproject.toml                  # Package metadata
├── requirements.txt                # Python dependencies
└── README.md                       # Project documentation

Root level:
├── config.py                       # Configuration Manager v1 (NO profiles) — DUPLICATE
├── main.py                         # Legacy v1 CLI menu — DUPLICATE
├── requirements.txt                # Partial dependency list — DUPLICATE
├── prompts/                        # Duplicate prompt files — DUPLICATE
│   ├── template.txt
│   └── examples/
│       └── add_feature.txt
├── README.md                       # Simpler documentation — DUPLICATE
├── .gitignore
└── docs/                           # Architecture documentation
    ├── ARCHITECTURE_FREEZE.md
    ├── ARCHITECTURE_AUDIT.md
    └── IMPLEMENTATION_ROADMAP.md

workflow-orchestrator-docs/         # Detailed RFC-style design docs (33 documents)
└── README.md
```

## Problems

### Critical

#### P1. Duplicate Files (4 pairs)
| File | Duplicate | Impact |
|---|---|---|
| `config.py` (root) | `workflow_orchestrator/config.py` | Two `ConfigurationManager` classes with overlapping but diverging APIs. Root version lacks profile support. Modules import from root, CLI imports from root, causing confusion. |
| `main.py` (root) | `workflow_orchestrator/main.py` | Two CLI entry points with different interfaces. Root has 14-option text menu. Workflow_orchestrator/main.py has Rich interactive menu. Neither is the primary Typer CLI at `workflow_orchestrator/cli.py`. Three CLIs total. |
| `requirements.txt` (root) | `workflow_orchestrator/requirements.txt` | Root has only `pyperclip>=1.8.2`. Workflow_orchestrator has full dependency list. Root is dangerously incomplete. |
| `prompts/` (root) | `workflow_orchestrator/prompts/` | Identical `template.txt` and `examples/add_feature.txt`. Maintained separately, likely to diverge. |

#### P2. Circular Import Risk
The `config.py` (root) is imported by `modules/*.py` (which are tool implementations). If config.py ever imports back from modules (e.g., for validation), it creates a circular dependency. Currently: `config → (no modules imports)` is safe, but the pattern `modules → config → modules` is fragile.

#### P3. Global Mutable Singleton
`plugins/registry.py` defines `default_registry = PluginRegistry()` as a module-level singleton. This is:
- Imported by every plugin for auto-registration
- Imported by `engine.py` as default parameter
- Not resettable between tests
- Not mockable without import manipulation

#### P4. No Test Suite
Zero test files exist in the entire repository. No `tests/` directory. No `pytest` configuration. No type checking in CI. No linting in CI.

#### P5. Missing `__init__.py`
`workflow_orchestrator/__init__.py` does not exist, which may cause import issues in some environments or IDE configurations.

### Medium

#### M1. Dead Code in Plugins
- `plugins/browser_plugin.py` imports `StepStatus` but only uses `Plugin._success()` and `Plugin._failure()` — unused import
- Several plugins import model types they don't directly use

#### M2. Inconsistent Import Patterns
- `modules/*.py` use `from config import config_manager` (root config)
- `workflow_orchestrator/cli.py` also uses `from config import config_manager`
- `plugins/*.py` use `from workflow_orchestrator.models import ...`
- `plugins/*.py` use lazy imports for `workflow_orchestrator.modules.*`

#### M3. Tight Coupling — modules to config
Every module in `modules/` directly imports `config_manager` as a global, creating tight coupling that makes testing and isolation difficult.

#### M4. Scheduler Trigger Bug
`_build_trigger("once")` returns `IntervalTrigger(seconds=5)` — "once" maps to a repeating 5-second interval, not a single execution. This is logically incorrect.

#### M5. Version Inconsistency
- `pyproject.toml` declares `version = "2.0.0"`
- `modules/__init__.py` declares `__version__ = "2.0.0"`
- No changelog exists
- Architecture freeze declares `Architecture Version: 3.0.0`

### Low

#### L1. Duplicate Functionality
- `modules/render.py` has `open_dashboard()` and `open_logs()` (using `webbrowser`)
- `modules/browser.py` has `open_render()` and `open_render_logs()` (using Brave)
- These duplicate the same intent with different browser implementations

#### L2. Logging Redundancy
- `modules/logger.py` sets up file + console logging
- `workflow_orchestrator/main.py` calls `setup_logger()` again
- No correlation IDs, execution IDs, or structured logging

#### L3. Missing Type Annotations
Some function definitions lack return type hints (e.g., some `validate_config` methods, `_get_*_module()` helpers).

#### L4. Duplicate Prompt Paths
Prompt template paths are defined in both root-level `prompts.py` and `workflow_orchestrator/modules/prompts.py`, each pointing to different directories.

#### L5. Outdated Docstrings
Some module-level docstrings reference "v1" behavior that has since changed.

## Recommended Fixes

### Fix Priority Order

| Priority | Fix | Files Affected | Complexity |
|---|---|---|---|
| P1 | Merge config.py into `workflow_orchestrator/config/` | 12+ files | High |
| P1 | Consolidate CLIs (keep Typer only) | 3 files | Medium |
| P1 | Remove global `default_registry` singleton | 10+ files | High |
| P1 | Create test suite | New files | High |
| P1 | Create `workflow_orchestrator/__init__.py` | 1 file | Low |
| M1 | Clean up unused imports | 8 files | Low |
| M2 | Standardize import patterns | 12+ files | Medium |
| M3 | Implement DI for config | 12+ files | High |
| M4 | Fix scheduler "once" trigger | 1 file | Low |
| M5 | Bump version, add changelog | 2 files | Low |
| L1 | Consolidate browser/render/vercel modules | 3 files | Low |
| L2 | Create unified logging with correlation IDs | 3 files | Medium |
| L3 | Add missing type annotations | 5 files | Low |

### Detailed Fix Plans

#### Fix P1 — Configuration System
1. Create `workflow_orchestrator/config/__init__.py` with ConfigManager class
2. Implement `config_manager.py` — unified ConfigurationManager
3. Implement `profile_loader.py` — YAML profile loading
4. Implement `settings.py` — Settings dataclass
5. Implement `validators.py` — Configuration validation
6. Delete root `config.py`
7. Delete `workflow_orchestrator/config.py`
8. Update all imports from `from config import ...` to `from workflow_orchestrator.config import ...`
9. Keep root `config.py` as deprecated shim for backward compatibility

#### Fix P1 — CLI Consolidation
1. Keep `workflow_orchestrator/cli.py` (Typer) as the primary CLI
2. Remove `workflow_orchestrator/main.py` (Rich menu)
3. Keep root `main.py` as backward compat entry point (delegate to Typer)
4. Update `pyproject.toml` entry points

#### Fix P1 — Dependency Injection
1. Create `core/service_registry.py` with `ServiceRegistry` class
2. Define `ServiceRegistry` as the single source of truth for all services
3. Update `PluginRegistry` to accept optional registry parameter
4. Remove `default_registry` global, replace with registry injection
5. Update `WorkflowEngine` to require registry injection

#### Fix P4 — Test Suite
1. Create `tests/unit/` directory
2. Create `tests/unit/test_config_manager.py`
3. Create `tests/unit/test_kernel.py`
4. Create `tests/unit/test_event_bus.py`
5. Create `tests/unit/test_state_engine.py`
6. Create `tests/unit/test_workspace_manager.py`
7. Create `tests/unit/test_artifact_manager.py`
8. Create `tests/conftest.py` with shared fixtures

## Migration Notes

### Backward Compatibility Strategy

1. **Config**: Root `config.py` will become a thin re-export shim that imports from `workflow_orchestrator.config`. All internal code will be updated to import directly from the new location.

2. **CLI Entry Points**: Both `main.py` files will be kept temporarily but marked deprecated, delegating to the Typer CLI.

3. **Plugin Registry**: The `default_registry` singleton will be replaced with a module-level lazy getter that returns the registry from the kernel's ServiceRegistry. Existing auto-registration patterns will continue to work.

4. **Imports**: All internal imports will be updated. External API consumers may need to update imports from `from config import ...` to `from workflow_orchestrator.config import ...`.

### Remaining Phase 1 Work

After Phase 0 is complete, the following remain for Phase 1 (Core Orchestration Kernel):

1. **Event Bus**: Flesh out full event taxonomy, async subscribers, backpressure
2. **State Engine**: Add write-ahead persistence, heartbeat monitoring, crash recovery
3. **Split Engines**: Separate WorkflowEngine from ExecutionEngine, add DependencyResolver
4. **Capability Registry**: Add resolution ranking, user pins, quality filtering
5. **Decision Engine**: Add template-first planning, fallback selection

### Files to Remove

1. `config.py` (root) — replaced by `workflow_orchestrator/config/`
2. `workflow_orchestrator/main.py` — replaced by Typer CLI
3. `requirements.txt` (root) — incomplete duplicate
4. `prompts/` (root) — duplicate of `workflow_orchestrator/prompts/`

### Files to Add

1. `workflow_orchestrator/__init__.py` — package marker
2. `workflow_orchestrator/core/__init__.py` — core package
3. `workflow_orchestrator/core/kernel.py` — Kernel class
4. `workflow_orchestrator/core/service_registry.py` — ServiceRegistry class
5. `workflow_orchestrator/core/lifecycle.py` — LifecycleManager
6. `workflow_orchestrator/core/bootstrap.py` — Bootstrap logic
7. `workflow_orchestrator/core/shutdown.py` — Shutdown logic
8. `workflow_orchestrator/core/event_bus.py` — Event Bus skeleton
9. `workflow_orchestrator/core/state_engine.py` — State Engine skeleton
10. `workflow_orchestrator/core/capability_registry.py` — Capability Registry skeleton
11. `workflow_orchestrator/core/workspace_manager.py` — Workspace Manager
12. `workflow_orchestrator/core/artifact_manager.py` — Artifact Manager
13. `workflow_orchestrator/config/__init__.py` — Config package
14. `workflow_orchestrator/config/config_manager.py` — Config Manager
15. `workflow_orchestrator/config/profile_loader.py` — Profile Loader
16. `workflow_orchestrator/config/settings.py` — Settings models
17. `workflow_orchestrator/config/validators.py` — Config validators
18. `tests/unit/*.py` — Unit tests
19. `tests/conftest.py` — Test fixtures
20. `workflow_orchestrator/core/logger.py` — Unified logging
21. `docs/FOUNDATION.md` — Foundation documentation

### Files to Move

None — Phase 0 keeps existing files in place and adds new infrastructure alongside. Backward-compatible shims prevent breaking changes.
