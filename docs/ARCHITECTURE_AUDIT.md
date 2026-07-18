# Architecture Audit

> **Date:** 2026-07-18
> **Auditor:** Chief Software Architect
> **Status:** Final

## Overview

This document audits every existing RFC document (00–33), the Python source code, and the project structure. Each document is assessed for quality, consistency, contradictions, and alignment with the project vision.

---

## Document-by-Document Audit

### 00 — VISION
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep** — Foundational, stable, well-written |
| Issues | None |
| Recommendations | No changes needed |

### 01 — PRODUCT
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep** |
| Issues | References `24_CONFIGURATION_WIZARD.md` and `23_CLI_DESIGN.md` correctly. No contradictions. |
| Recommendations | Add explicit reference to the new `docs/ARCHITECTURE_FREEZE.md` |

### 02 — ARCHITECTURE
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (with updates)** |
| Issues | The layering diagram is excellent but the "Dependency Resolver" is listed in Layer 1 but implemented nowhere in code. The "Decision Engine" is placed in Layer 1 but its actual role bridges Layer 1 and Layer 2. |
| Contradictions | Doc 26's folder structure (`core/`, `domain/`, `adapters/`) does not match the actual codebase structure (`plugins/`, `modules/`). The codebase has no `core/` or `domain/` or `adapters/` directories. |
| Recommendations | Update diagram to reflect the actual future folder structure. Clarify the Decision Engine's layer placement. |

### 03 — SYSTEM_OVERVIEW
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep** |
| Issues | Sequence diagram references components (Capability Registry, Context Engine, Decision Engine) that don't exist in code yet. This is acceptable for a design document, but the gap between documented vision and code must be noted. |
| Recommendations | Add a note about which components are implemented vs. planned. |

### 04 — WORKFLOW_ENGINE
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (with updates)** |
| Issues | The interface `IWorkflowEngine` is well-defined but the actual `WorkflowEngine` class in `engine.py` is significantly simpler — it only does sequential step execution with no graph traversal, no dependency resolution, no state machine transitions. |
| Contradictions | Doc 04 describes a full state machine with `Pending → Ready → Running → {Succeeded, Failed, Skipped}`. The actual engine has no such states — it iterates steps linearly. |
| Duplication | The `StepDefinition` type is partially duplicated in `models.py`'s `WorkflowStep` class, but missing `requires: Capability[]`, `condition?`, and `timeout?` fields. |
| Recommendations | Enrich `WorkflowStep` to match `StepDefinition`. Implement the state machine. |

### 05 — PROVIDER_SYSTEM
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only — not implemented)** |
| Issues | No `IProvider` interface exists in code. No providers are registered. The existing `plugins/` system wraps developer tools (browser, terminal, git), not AI providers. |
| Contradictions | The doc defines a sophisticated provider system with manifests, health checks, and cost estimation. The codebase has none of this. The gap is 100% — this is pure design documentation. |
| Weakness | The provider lifecycle diagram is strong, but no concrete provider manifests exist. |
| Recommendations | Keep as design intent. Mark as "Not Yet Implemented — Phase 2 target." |

### 06 — AGENT_SYSTEM
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | Same as 05 — no `IAgent` interface exists in code. The plugin system's `Plugin` base class bears no resemblance to `IAgent`. |
| Contradictions | Doc 06 describes agents as autonomous coding tools (Claude Code, Cursor). The code's plugins are simple synchronous wrappers around shell commands. |
| Weakness | The sandboxing model (`WorkspaceHandle`, `SandboxSpec`) is well-described but not implementable with the current `modules/terminal.py` which has no sandboxing at all. |
| Recommendations | Keep as design intent. Flag sandboxing as a critical dependency for agent safety. |

### 07 — CAPABILITY_REGISTRY ⭐
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `ICapabilityRegistry` exists in code. No capabilities are declared by any plugin. The `PluginRegistry` in `plugins/registry.py` is a simple name-based lookup, not a capability-based registry. |
| Contradictions | The taxonomies, resolution rules, and ranking described in the doc are entirely absent from the code. |
| Missing | The document mentions a "Capability Taxonomy" but none is defined. |
| Recommendations | This is the most important infrastructure component to implement. Prioritize in Phase 1. |

### 08 — CONTEXT_ENGINE ⭐
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `IContextEngine` exists. The `prompts.py` module has a simple template loader/formatter — orders of magnitude simpler than the described Context Engine. |
| Contradictions | The doc describes layered context assembly with summarization, budget enforcement, and cross-provider communication. The code has `format_prompt(template, **kwargs)`. |
| Recommendations | Keep as design. The existing `prompts.py` can serve as a seed for the template rendering sub-component. |

### 09 — STATE_ENGINE ⭐
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `IStateEngine` exists. The `WorkflowEngine` class has no state machine, no transition log, no checkpointing, no crash recovery. |
| Contradictions | The doc's append-only transition log, write-ahead persistence, and resume capability are entirely absent from the code. |
| Weakness | This is the single most critical missing component for reliability. Without it, crash recovery and resume are impossible. |
| Recommendations | Must be implemented in Phase 1. The models.py `ExecutionReport` is a very crude approximation of a state snapshot. |

### 10 — PROJECT_CONTRACT ⭐
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `IProjectContract` exists. The `WorkflowDefinition` class in `models.py` has `name`, `description`, `steps` — but no `version`, `status`, `techStack`, `constraints`, `acceptanceCriteria`. |
| Contradictions | The doc says "every provider reads this contract" — no providers exist. The contract's immutability-per-version design is not reflected in code. |
| Recommendations | Keep as design. The `WorkflowDefinition` class can evolve toward `ProjectContract`. |

### 11 — PLUGIN_SYSTEM
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (with updates)** |
| Issues | This is the closest doc-to-code match. The `Plugin` base class, `PluginRegistry`, and auto-discovery all exist and work. However, the doc's sandboxing, permission model, and `onLoad`/`onUnload` lifecycle are not implemented. |
| Contradictions | Doc 11 describes `PluginContext` with registration methods for providers/agents/tools. The actual `PluginRegistry` has a single `register(plugin)` method. |
| Missing | No plugin hot-reload, no manifest validation against schema, no sandbox enforcement. |
| Recommendations | Update the registry to support the full lifecycle. Add manifest validation. |

### 12 — CONFIGURATION_SYSTEM
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (with updates)** |
| Issues | The `config.py` has TWO copies: root-level (v1, no profiles) and `workflow_orchestrator/config.py` (v2, with profiles). This is a code quality issue. |
| Contradictions | Doc 12 describes `IConfig` with `getSecret` and secret isolation. The actual code stores all config in plain JSON — no secret handling at all. |
| Duplication | Two `ConfigurationManager` classes with overlapping but not identical functionality. |
| Recommendations | Merge the two config managers. Remove root-level `config.py`. Add secret handling (OS keychain). |

### 13 — WORKFLOW_SPECIFICATION
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (with updates)** |
| Issues | The YAML format in the code partially matches the doc. The `from_dict()` method supports short-form and long-form step definitions. Missing: `apiVersion`, `extends`, `defaults`. |
| Contradictions | None significant. The implemented YAML parser is a reasonable subset. |
| Recommendations | Add `apiVersion`, `extends`, and template composition support. |

### 14 — EXECUTION_ENGINE ⭐
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `IExecutionEngine` exists. The `WorkflowEngine.execute()` method combines the roles of Workflow Engine and Execution Engine — it both walks the step list and dispatches to plugins. |
| Contradictions | Doc 14 describes a separate Dependency Resolver, Scheduler, Parallel Executor, and Sequential Executor. The code has a single `for step in workflow.steps:` loop. |
| Missing | No parallelism, no dependency-aware scheduling, no write-scope conflict detection. |
| Recommendations | Extract execution logic from `WorkflowEngine` into a dedicated `ExecutionEngine`. |

### 15 — REPORT_ENGINE
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (with updates)** |
| Issues | The `reports.py` module exists and works. It saves/loads JSON reports and computes statistics. But it's simpler than the doc describes — no Rich HTML/markdown renderers, no offline-viewable self-contained reports. |
| Contradictions | Doc mentions `self-contained single-file HTML` as current default but it's not implemented. |
| Recommendations | Add the HTML and Markdown renderers. Keep the JSON format as the canonical persisted form. |

### 16 — ARTIFACT_MANAGER
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `IArtifactManager` exists. Step outputs are stored in an in-memory `context` dict passed between steps. Nothing is content-addressed, immutable, or provenance-tracked. |
| Contradictions | Doc describes content-addressable storage, diffing, history — none exist. |
| Weakness | Without an artifact manager, verification, rollback, and reporting all lack reliable artifact references. |
| Recommendations | Implement as a local filesystem-based content-store in Phase 3. |

### 17 — EVENT_BUS
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `IEventBus` exists. The engine logs events via a standard `logging.Logger` — no typed events, no pub/sub, no subscription model. |
| Contradictions | Doc describes a sophisticated bus with typed events, subscribers, and at-least-once delivery. |
| Recommendations | Implement a lightweight in-process event bus in Phase 1 before other core components. |

### 18 — PROJECT_SCANNER
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (mostly implemented)** |
| Issues | The `ProjectScanner` class exists and works well. It detects languages, frameworks, package managers, Git, Docker. This is the most complete implementation-to-doc match in the codebase. |
| Contradictions | Doc references `Detector plugins` but the scanner's detectors are hard-coded in `ProjectScanner.LANGUAGE_INDICATORS`. |
| Recommendations | Make detectors pluggable via the Plugin System. |

### 19 — DEPLOYMENT_ENGINE
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `IDeploymentTarget` exists. The `modules/vercel.py` and `modules/render.py` are URL-opening helpers, not deployment engines. They don't interact with any deployment API. |
| Contradictions | Doc describes deploy/rollback/smokeCheck interface. Code has `webbrowser.open(url)`. |
| Recommendations | The existing modules can serve as seeds, but a proper deployment engine requires API integration. |

### 20 — VERIFICATION_ENGINE
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `IVerificationEngine` exists. The engine has no verification step — step success/failure is determined by plugin exit status, not by contract criteria. |
| Contradictions | Doc describes a sophisticated verification pipeline with pluggable checks, evidence artifacts, and binary verdicts. |
| Recommendations | Implement in Phase 3 when the Project Contract system exists. |

### 21 — ERROR_RECOVERY
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | The engine has basic retry (`RetryConfig`) and failure actions (`OnFailure.STOP/CONTINUE/RETRY`), but no error classification, no debug loop, no escalation to Decision Engine. |
| Contradictions | Doc describes `IErrorRecovery` with typed errors and recovery actions. The code has `_execute_step()` with a simple retry loop. |
| Recommendations | Keep the existing retry as the foundation. Add error classification and escalation. |

### 22 — RESUME_ENGINE
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `IResumeEngine` exists. No checkpointing, no run persistence, no resume capability. |
| Contradictions | Doc describes resume as a user-facing layer over State Engine — neither exists. |
| Recommendations | Cannot be implemented until State Engine exists. Phase 4 target. |

### 23 — CLI_DESIGN
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (mostly implemented)** |
| Issues | The `cli.py` file implements most of the documented command surface (`run`, `list`, `scan`, `config`, `plugins`, `reports`, `schedule`). Missing: `resume`, `rollback`, `abort`, `report --format`. |
| Contradictions | Doc says "CLI is a thin client over the API" but no `OrchestratorApi` exists — the CLI directly imports engine, scanner, etc. |
| Duplication | TWO CLI systems exist: root `main.py` (14-option text menu) and `workflow_orchestrator/cli.py` (Typer). The Rich menu in `workflow_orchestrator/main.py` provides a third interface. |
| Recommendations | Consolidate to the Typer CLI as the only CLI. Remove root `main.py` and `workflow_orchestrator/main.py` Rich menu. Add `resume`, `rollback`, `abort`. |

### 24 — CONFIGURATION_WIZARD
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design reference)** |
| Issues | No wizard exists. The `config.py` has `configure_interactive()` which is a simple prompt-based setup, but no live credential validation, no health-checks. |
| Contradictions | Doc describes a sophisticated wizard with live validation and guided provider setup. |
| Recommendations | Keep as design. `configure_interactive()` can serve as seed. |

### 25 — DATA_MODELS
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (critical reference)** |
| Issues | This document is more comprehensive than the actual `models.py`. Many entities described (`TransitionRecord`, `RunSnapshot`, `CapabilityManifest`, `DeploymentResult`, `Verdict`) don't exist in code. |
| Contradictions | The ER diagram references entities not yet in code. This is fine — the document is the target model. |
| Recommendations | This should become the authoritative schema definition. Generate concrete Python dataclasses from it during implementation. |

### 26 — FOLDER_STRUCTURE
| Criterion | Verdict |
|---|---|
| Merge | 🔀 **Merge into ARCHITECTURE_FREEZE.md** |
| Issues | The proposed structure (`core/`, `domain/`, `adapters/`, `plugins/`, `cli/`, `config/`) does not match the actual codebase. The actual structure has `plugins/` and `modules/` as sibling directories, while the RFC proposes moving adapters into `adapters/providers/`, `adapters/agents/`, etc. |
| Contradictions | The doc describes a clean layered structure, but the actual code has modules at the root of `workflow_orchestrator/`, plugins in `plugins/`, and modules in `modules/` — mixing abstraction levels. |
| Recommendations | This document should be the definitive folder structure. The codebase must be refactored to match it. |

### 27 — API_SPECIFICATION
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (design only)** |
| Issues | No `OrchestratorApi` exists. The CLI directly imports engine components. |
| Contradictions | Doc says "CLI is a thin client over this API" — currently false. |
| Recommendations | Extract `OrchestratorApi` class. CLI becomes a thin wrapper. |

### 28 — EXTENSION_GUIDE
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (needs updating)** |
| Issues | The guide references interfaces that don't exist yet (`IProvider`, `IAgent`, `IDeploymentTarget`). |
| Recommendations | Update with concrete implementation examples once interfaces exist. |

### 29 — ROADMAP
| Criterion | Verdict |
|---|---|
| Merge | 🔀 **Merge into IMPLEMENTATION_ROADMAP.md** |
| Issues | The roadmap proposes 6 phases but doesn't reference actual file paths or modules. It's too abstract to serve as an implementation guide. |
| Contradictions | Phase 0 "no user-visible behavior" is at odds with the existing working CLI. The existing code is ahead of the roadmap's Phase 0. |
| Recommendations | Create a new, concrete roadmap that accounts for existing code. |

### 30 — GLOSSARY
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (update with new terms)** |
| Issues | Missing terms added by this freeze: Workspace Manager, Resource Manager, Cache Manager, Policy Engine, Audit Engine, Metrics Engine, Session Manager, Manifest System, Template Registry, Workflow Registry, Provider Adapter Layer, Agent Adapter Layer, Execution Queue, Dependency Resolver. |
| Recommendations | Add new glossary terms. |

### 31 — DECISION_ENGINE (Added)
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep — well-justified addition** |
| Issues | No implementation exists. The "why this was added" section is excellent and explains the gap well. |
| Recommendations | Keep as-is. This is a well-designed addition. |

### 32 — SUPPORTING_SYSTEMS (Added)
| Criterion | Verdict |
|---|---|
| Split | ✂️ **Split into individual documents** |
| Issues | Eleven systems are crammed into one document. The document itself notes "if any grows architecturally significant, it should graduate out." Several already are significant enough: Metrics Engine, Policy Engine, Audit Engine, Workspace Manager. |
| Recommendations | Split off Workspace Manager and Policy Engine into their own documents. Keep the other nine in a condensed reference. |

### 33 — ARCHITECTURE_REVIEW (Added)
| Criterion | Verdict |
|---|---|
| Keep | ✅ **Keep (superseded by this audit)** |
| Issues | This was a pre-freeze self-assessment. It correctly identifies risks (determinism erosion, sandbox safety, manifest honesty, context budget). However, it doesn't identify the code-vs-document gap. |
| Recommendations | Update to reference this ARCHITECTURE_AUDIT.md. |

---

## Cross-Cutting Findings

### Contradictions Summary

| # | Contradiction | Severity |
|---|---|---|
| 1 | Doc 26 folder structure ≠ actual folder structure | HIGH |
| 2 | Doc 04 workflow states ≠ engine.py linear execution | HIGH |
| 3 | Two `config.py` files with different capabilities | HIGH |
| 4 | Two `main.py` files with different menus | HIGH |
| 5 | Doc 05/06 provider/agent interfaces absent from code | HIGH |
| 6 | Doc 07-10, 14, 16-17, 19-22 describe systems absent from code | HIGH |
| 7 | Doc 12 secret handling ≠ plain JSON config | MEDIUM |
| 8 | Doc 27 API design ≠ CLI directly importing engine | MEDIUM |
| 9 | `modules/` import from root `config`, not `workflow_orchestrator.config` | MEDIUM |
| 10 | Capability taxonomy referenced but undefined | LOW |

### Duplicated Concepts

| Concept | Location 1 | Location 2 | Action |
|---|---|---|---|
| ConfigurationManager | `config.py` (root) | `workflow_orchestrator/config.py` | Merge |
| Main entry point | `main.py` (root) | `workflow_orchestrator/main.py` | Remove root, keep Typer |
| Workflow models | `models.py` `WorkflowStep` | Doc 04 `StepDefinition` | Enrich models.py |
| Report storage | `reports.py` | Doc 15 | Already aligned |
| Plugin system | `plugins/base.py` | Doc 11 Plugin interface | Enrich base.py |

### Weak Architecture

| Weakness | Location | Fix |
|---|---|---|
| No separation between Workflow Engine and Execution Engine | `engine.py` | Split into two classes |
| No event bus — everything logs to stdlib logger | All code | Implement EventBus |
| No state machine — linear iteration only | `engine.py` | Implement state transitions |
| Modules import from config but config may import modules | circular | Fix import direction |
| Plugins are synchronous — no async support | `plugins/base.py` | Add async execute support |
| No verification step — plugin exit = step verdict | `engine.py` | Add Verification Engine |
| No secret isolation | `config.py` | Add OS keychain integration |
| No checkpointing / crash recovery | entire code | State Engine needed |

### Missing Systems

| System | Doc | Code Status | Priority |
|---|---|---|---|
| Event Bus | 17 | Missing | P0 — blocks all observability |
| State Engine | 09 | Missing | P0 — blocks reliability |
| Capability Registry | 07 | Missing | P0 — blocks provider/agent routing |
| Context Engine | 08 | Missing (prompts.py is seed) | P0 — blocks intelligent prompting |
| Execution Engine (separate) | 14 | Merged into WorkflowEngine | P1 |
| Artifact Manager | 16 | Missing | P1 |
| Verification Engine | 20 | Missing | P1 |
| Error Recovery (formal) | 21 | Basic retry only | P1 |
| Provider System | 05 | Missing | P2 |
| Agent System | 06 | Missing | P2 |
| Deployment Engine | 19 | URL openers only | P2 |
| Decision Engine | 31 | Missing | P2 |
| Resume Engine | 22 | Missing | P3 |
| Project Contract | 10 | Missing | P2 |
| Supporting Systems | 32 | Missing | P3 |

### Circular Dependencies

| Risk | Path | Resolution |
|---|---|---|
| Context Engine ↔ Capability Registry | Context needs provider capabilities; Registry needs context for scoring | Make scoring pure function of declared metadata |
| Config ↔ Engine ↔ Plugins | Config loads profiles that reference plugins via engine | Config must never import engine; use interface injection |
| Modules ↔ Config | `modules/browser.py` imports `config`; `config.py` may indirectly import modules | Modules must use IConfig interface, not concrete config |

### Poor Naming

| Current Name | Issue | Suggested Name |
|---|---|---|
| `modules/` | Too generic — suggests any module, not capability implementations | `capabilities/` or `tools/` |
| `github.py` | Only does Git, not GitHub API | `git.py` |
| `WorkflowStep` | Missing type field, capability requirements | Align with `StepDefinition` |
| `WorkflowDefinition` | More like a spec than a definition | `WorkflowSpec` |
| `Plugin` | Not a traditional plugin — it's a step executor | `StepHandler` or keep but clarify |
| `default_registry` | Global mutable singleton | Risk for testing; inject instead |
| `OnFailure` enum | `OnFailure.STOP` reads awkwardly | `FailureAction.STOP` |

### Inconsistent Terminology

| Term | Doc Usage | Code Usage | Issue |
|---|---|---|---|
| Provider | AI vendor (Claude, ChatGPT) | Not used at all in code | Gap |
| Agent | Coding tool (Cursor, Claude Code) | `Plugin` classes used instead | Gap |
| Capability | Declared ability identifier | Not used in code | Gap |
| Workflow | YAML-specified graph | YAML-specified step list | Doc=graph, Code=list |
| Step | Graph node with dependencies | Sequential list element | Doc has DAG, Code is linear |
| Plugin | Extension point | Step executor | Doc has broader meaning |
| Artifact | Immutable, content-addressed | `step.output` in memory dict | Gap |

---

## Document Disposition Summary

| Doc | Action | Reason |
|---|---|---|
| 00 | Keep | Foundational vision, no changes needed |
| 01 | Keep (update references) | Add reference to freeze docs |
| 02 | Keep (update diagram) | Add Decision Engine, fix layering |
| 03 | Keep | Good overview, no major issues |
| 04 | Keep (align with code) | State machine must be implemented |
| 05 | Keep (mark unimplemented) | Critical design, Phase 2 target |
| 06 | Keep (mark unimplemented) | Critical design, Phase 4 target |
| 07 | Keep (mark unimplemented) | Most important Phase 1 component |
| 08 | Keep (mark unimplemented) | Phase 2 target, prompts.py as seed |
| 09 | Keep (mark unimplemented) | Phase 1 critical path |
| 10 | Keep (mark unimplemented) | Phase 2 target |
| 11 | Keep (enrich code) | Closest doc-code match, needs lifecycle |
| 12 | Keep (enrich code) | Merge configs, add secret handling |
| 13 | Keep (enrich code) | Add apiVersion, extends |
| 14 | Keep (split from WE) | Phase 1 critical path |
| 15 | Keep (enrich code) | Add HTML/markdown renderers |
| 16 | Keep (mark unimplemented) | Phase 3 target |
| 17 | Keep (mark unimplemented) | Phase 1 critical path |
| 18 | Keep (mostly implemented) | Best doc-code match, add plugin detectors |
| 19 | Keep (mark unimplemented) | Phase 3 target |
| 20 | Keep (mark unimplemented) | Phase 3 target |
| 21 | Keep (enrich code) | Add error classification, Phase 3 |
| 22 | Keep (mark unimplemented) | Phase 4 target |
| 23 | Keep (enrich code) | Consolidate CLIs, add missing commands |
| 24 | Keep (design reference) | Phase 5 target, seed exists |
| 25 | Keep (critical reference) | Schema authority, generate dataclasses |
| 26 | **Merge** into ARCHITECTURE_FREEZE.md | Redundant as standalone doc |
| 27 | Keep (design only) | Phase 6 target |
| 28 | Keep (update) | Update after interfaces implemented |
| 29 | **Merge** into IMPLEMENTATION_ROADMAP.md | Replace with concrete plan |
| 30 | Keep (enrich) | Add new glossary terms |
| 31 | Keep | Well-justified, Phase 2 target |
| 32 | Split into individual docs | Workspace Manager, Policy Engine need own docs |
| 33 | Keep (superseded) | Refer to this audit for current review |

---

## Code-Level Issues

### Critical
1. **Two config.py files** with overlapping but different functionality — merge risk
2. **Two main.py files** — confusing to contributors
3. **No test suite** — not a single test file exists in the entire project
4. **No typechecking in CI** — `pyproject.toml` has `mypy` in dev deps but no CI config
5. **Global mutable singleton** (`default_registry`) — hard to test, hard to reason about

### Medium
6. `modules/browser.py` only supports Brave — should support configurable browser
7. `WorkflowEngine.execute()` is 100+ lines — violates Single Responsibility
8. Config profiles are YAML but config.json is JSON — inconsistent serialization choices
9. No environment variable interpolation in workflow step configs
10. Scheduler's `_build_trigger` maps "once" to `IntervalTrigger(seconds=5)` — logically incorrect

### Low
11. Docstrings are good but some module-level docstrings are outdated
12. `requirements.txt` at root has only pyperclip; the one in `workflow_orchestrator/` is more complete
13. Some functions lack `->` return type annotations despite overall good typing
14. `open_render()` and `render_open_dashboard()` duplicate functionality
15. Version is declared as `2.0.0` in multiple places but no changelog exists

---

## Recommendations Summary

### Immediate Actions (Pre-Freeze)
1. Merge the two `config.py` files
2. Consolidate to the Typer CLI, remove legacy `main.py` files
3. Add `docs/ARCHITECTURE_FREEZE.md` and `docs/IMPLEMENTATION_ROADMAP.md`
4. Update all docs to reference the freeze doc

### Short-Term (Phase 1 Before Code)
5. Implement Event Bus (17)
6. Implement State Engine (09) with transition log
7. Implement Capability Registry (07)
8. Split WorkflowEngine into WorkflowEngine + ExecutionEngine
9. Enrich WorkflowStep to match StepDefinition schema

### Medium-Term (Phase 2-3)
10. Implement Provider System (05) with first real adapter
11. Implement Context Engine (08)
12. Implement Artifact Manager (16)
13. Implement Verification Engine (20)
14. Implement Project Contract (10)
15. Add test suite with pytest

### Long-Term (Phase 4-6)
16. Implement Agent System (06)
17. Implement Decision Engine (31)
18. Implement Resume Engine (22)
19. Implement Deployment Engine (19)
20. Implement Supporting Systems (32)
21. Add CI/CD configuration
22. Add webhook/notification support
