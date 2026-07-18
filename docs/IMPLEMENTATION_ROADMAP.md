# Implementation Roadmap

> **Architecture Version:** 3.0.0
> **Last Updated:** 2026-07-18
> **Status:** Active Planning

---

## Phase Overview

| Phase | Name | Dependencies | Est. Effort | Outcome |
|---|---|---|---|---|
| 0 | Codebase Cleanup | None | 3-5 days | Clean foundation for new architecture |
| 1 | Core Orchestration Kernel | Phase 0 | 3-4 weeks | Deterministic core: Event Bus, State Engine, split Engines |
| 2 | Intelligence Plane Integration | Phase 1 | 4-6 weeks | First real provider + agent end-to-end |
| 3 | Verification & Delivery | Phase 2 | 3-4 weeks | Verification gates, artifact storage, deployment |
| 4 | Extensibility & Advanced Features | Phase 3 | 4-5 weeks | Plugin marketplace readiness, parallel execution, workshop mgmt |
| 5 | Product Polish | Phase 4 | 2-3 weeks | CLI live-view, wizard, reporting |
| 6 | Ecosystem & Supporting Systems | Phase 5 | 4-5 weeks | Metrics, audit, policy, notifications |
| 7 | v3.1.0 — Multi-Provider & Scale | Phase 6 | 3-4 weeks | 3+ providers, 1000 workflows verification |

---

## Phase 0: Codebase Cleanup

**Goal:** Eliminate technical debt before architecture-aligned development begins.

### Modules
| Module | Files | Action |
|---|---|---|
| Config Merge | `config.py` (root), `workflow_orchestrator/config.py` | Merge into single `workflow_orchestrator/config/config_manager.py` |
| CLI Consolidation | `main.py` (root), `workflow_orchestrator/main.py`, `workflow_orchestrator/cli.py` | Keep Typer CLI only. Remove both `main.py` files |
| Import Cleanup | All `modules/*.py` | Change imports from `config` to `workflow_orchestrator.config` |
| Circular Dep Fix | `modules/browser.py` → `config` → `modules/...` | Inject config, don't import it |
| Singleton Removal | `plugins/registry.py` default_registry | Make injectable, keep module-level for backward compat |

### Dependencies
None — this phase is entirely self-contained cleanup.

### Acceptance Criteria
- Single `config.py` in `workflow_orchestrator/config/`
- Single CLI entry point: `workflow` command
- No circular imports detected by `import-linter`
- All existing functionality preserved

### Testing
- Manual verification of all CLI commands
- Run `workflow run workflows/example.yaml` end-to-end
- Verify config profiles work: `workflow config switch-profile home`

### Estimated Complexity
**Low** — Mechanical refactoring, no new logic.

### Suggested Commit
```
Phase 0: Codebase cleanup — merge configs, consolidate CLIs, fix imports
```

---

## Phase 1: Core Orchestration Kernel

**Goal:** Implement the deterministic core that all higher-level features depend on.

### 1.1 Event Bus

| Detail | Value |
|---|---|
| Files | `core/event-bus/event_bus.py`, `core/event-bus/__init__.py` |
| Depends on | Phase 0 |
| Interface | `IEventBus` from `ARCHITECTURE_FREEZE.md` |
| Key Classes | `EventBus`, `Subscription`, `OrchestratorEvent` |

**Acceptance Criteria**
- In-process pub/sub with typed events
- Event taxonomy implemented: `workflow.*`, `step.*`, `state.*`, `capability.*`, `provider.*`, `agent.*`, `deployment.*`, `plugin.*`
- Synchronous publish, async subscriber processing
- Subscriber isolation (one subscriber exception doesn't affect others)
- Backpressure for high-frequency events

**Testing**
- Unit test: publish/subscribe/unsubscribe lifecycle
- Unit test: multiple subscribers receive same event
- Unit test: subscriber exception is isolated
- Unit test: pattern matching (`step.*` matches `step.failed`)

### 1.2 State Engine

| Detail | Value |
|---|---|
| Files | `core/state-engine/state_engine.py`, `core/state-engine/state_store.py`, `core/state-engine/__init__.py` |
| Depends on | 1.1 (Event Bus) |
| Interface | `IStateEngine`, `IStateStore` |

**Key Classes**
- `StateEngine` — transition validation, snapshot management
- `StateStore` — abstract persistence backend
- `FileSystemStateStore` — local JSON file implementation
- `TransitionRecord`, `RunSnapshot`, `HeartbeatRecord`

**Acceptance Criteria**
- Append-only transition log per run
- Write-ahead: log before side effect
- Materialized snapshot rebuildable from log alone
- Crash detection via heartbeat monitoring
- Rollback as forward transition (never deletion)
- Atomic compare-and-swap per run id

**Testing**
- Unit test: create run → transition → verify log
- Unit test: crash recovery — simulate crash, reconstruct state
- Unit test: rollback creates new transition, doesn't delete history
- Unit test: illegal transition is rejected
- Integration test: concurrent transition requests

### 1.3 Split Engines

| Detail | Value |
|---|---|
| Files | `core/workflow-engine/workflow_engine.py`, `core/execution-engine/execution_engine.py`, `core/dependency-resolver/dependency_resolver.py` |
| Depends on | 1.1, 1.2 |
| Interfaces | `IWorkflowEngine`, `IExecutionEngine`, `IDependencyResolver` |

**Key Classes**
- `WorkflowEngine` — graph walking, step dispatch to EE
- `ExecutionEngine` — scheduling, retry, timeout
- `DependencyResolver` — topological sort, conflict detection
- `ParallelExecutor`, `SequentialExecutor`

**Acceptance Criteria**
- WorkflowEngine walks graph, not flat list
- Step state machine: `pending → ready → running → {succeeded, failed, skipped}`
- Dependency Resolver computes execution order from `dependsOn` edges
- Parallel executor runs independent steps concurrently
- Sequential executor enforces dependency order
- Retry with exponential backoff per step
- Hard timeout enforcement per step

**Testing**
- Unit test: linear workflow executes steps in order
- Unit test: parallel steps run concurrently
- Unit test: dependency-gated step doesn't run before dependency
- Unit test: cyclic dependency rejected
- Unit test: retry on transient failure
- Unit test: timeout kills long-running step

### 1.4 Capability Registry (Minimal)

| Detail | Value |
|---|---|
| Files | `domain/capability-registry/capability_registry.py`, `domain/capability-registry/taxonomy.py` |
| Depends on | 1.1 |
| Interface | `ICapabilityRegistry` |

**Key Classes**
- `CapabilityRegistry` — indexing, resolution, ranking
- `CapabilityTaxonomy` — built-in capability IDs
- `RankedCandidates` — ordered resolution result

**Acceptance Criteria**
- Register/deregister candidates with capability manifests
- Resolve a `CapabilityRequirement` to ranked list
- Support user pins, quality sorting, cost filtering
- Exclude `Unavailable` candidates
- Produce resolution trace for debugging
- Built-in taxonomy: `codegen.*`, `reasoning.*`, `verify.*`, `deploy.*`, `tool.*`

**Testing**
- Unit test: register → resolve → get correct candidate
- Unit test: resolution respects user pin
- Unit test: unavailable candidate excluded
- Unit test: quality ranking works
- Unit test: resolution trace contains expected decisions

### 1.5 Decision Engine (Minimal)

| Detail | Value |
|---|---|
| Files | `core/decision-engine/decision_engine.py`, `core/decision-engine/template_matcher.py` |
| Depends on | 1.3, 1.4 |
| Interface | `IDecisionEngine` |

**Key Classes**
- `DecisionEngine` — planning, fallback, recovery decisions
- `TemplateMatcher` — outcome-to-template matching
- `PlanToGraphStructurer` — provider-proposed plan validation

**Acceptance Criteria**
- Template-first planning for known patterns
- Fallback to provider-proposed planning (with validation)
- In-run recovery decisions (fallback, retry, escalate)
- Every decision traceable to explicit rule
- Template matching is conservative (prefers fallback rather than forcing bad match)

**Testing**
- Unit test: known outcome matches template
- Unit test: unknown outcome falls back to provider planning
- Unit test: provider-proposed invalid plan is rejected
- Unit test: recovery decision returns expected action

### Phase 1 Dependencies
```
Phase 0
  └─→ 1.1 Event Bus
        ├─→ 1.2 State Engine
        └─→ 1.4 Capability Registry
              └─→ 1.5 Decision Engine
 1.3 Split Engines ──→ depends on 1.1, 1.2
```

### Phase 1 Acceptance Criteria (Overall)
- `workflow run` produces events, persists state, respects dependencies
- Crash recovery: kill process mid-run → `orchestrator resume` reconstructs state
- CLI commands: `run`, `status`, `resume`, `abort` all functional
- All existing YAML workflows work unchanged (backward compatible)

### Phase 1 Estimated Complexity
**High** — This is the most architecturally critical phase.

### Suggested Commit
```
Phase 1: Core orchestration kernel — Event Bus, State Engine, split engines, Capability Registry, Decision Engine
```

---

## Phase 2: Intelligence Plane Integration

**Goal:** Connect the deterministic core to real AI providers and agents.

### 2.1 Provider System

| Detail | Value |
|---|---|
| Files | `adapters/providers/base.py` (IProvider), `adapters/providers/anthropic-claude/` |
| Depends on | Phase 1, 2.2 (Capability Registry) |
| Interfaces | `IProvider`, `ProviderManifest` |

**Key Classes**
- `ProviderBase` — abstract base implementing common logic
- `ClaudeProvider` — first real provider adapter
- `ProviderHealthMonitor` — scheduled health checks
- `ProviderError` — typed error hierarchy

**Acceptance Criteria**
- `IProvider` interface fully implemented
- Claude adapter: manifest, health check, invoke, cost estimate, streaming
- Provider lifecycle: Registered → Available → Degraded → Unavailable
- Health checks on startup + after failures
- Capability Registry integration for selection

**Testing**
- Conformance test suite: every provider must pass
- Mock provider tests: all lifecycle states
- Integration test: actually call Claude API (with fixture for CI)

### 2.2 Context Engine

| Detail | Value |
|---|---|
| Files | `domain/context-engine/context_engine.py`, `domain/context-engine/templates/` |
| Depends on | Phase 1, 2.1 |
| Interface | `IContextEngine` |

**Key Classes**
- `ContextEngine` — assembly, budgeting, rendering
- `ContextAssembler` — pulls from State Engine, Artifact Manager
- `TokenBudgetEnforcer` — layer-by-layer trimming
- `TemplateRenderer` — step-type → prompt mapping

**Acceptance Criteria**
- ContextBundle assembled with 4 layers (immutable core, working set, rolling summary, recent turns)
- Token budget enforcement per provider context window
- Deterministic rendering for given (step_type, context_bundle, template_version)
- Cross-provider communication via provider-agnostic intermediate representation
- Pluggable summarization strategies

**Testing**
- Unit test: bundle assembly with all 4 layers
- Unit test: budget enforcement trims correctly
- Unit test: deterministic rendering
- Integration test: full pipeline with mock provider

### 2.3 Project Contract System

| Detail | Value |
|---|---|
| Files | `domain/project-contract/project_contract.py`, `domain/project-contract/validator.py` |
| Depends on | Phase 1 |
| Interface | `IProjectContract` |

**Key Classes**
- `ProjectContract` — schema, versioning, lifecycle
- `ContractValidator` — schema validation
- `ContractStore` — versioned persistence

**Acceptance Criteria**
- Contract schema: outcome, version, status, techStack, constraints, styleConventions, acceptanceCriteria
- Draft → Finalized → Superseded lifecycle
- Immutable per version (vN never modified, vN+1 created)
- Human confirmation gate required for finalization
- Every ContextBundle includes contract summary

**Testing**
- Unit test: create → finalize → cannot mutate
- Unit test: new version created correctly
- Unit test: human gate blocks finalization without confirmation
- Integration test: contract flows through Context Engine → Provider

### 2.4 Agent System

| Detail | Value |
|---|---|
| Files | `adapters/agents/base.py` (IAgent), `adapters/agents/claude-code/` |
| Depends on | 2.1, 2.3, Phase 1 |
| Interface | `IAgent`, `AgentManifest` |

**Key Classes**
- `AgentBase` — abstract base
- `ClaudeCodeAgent` — first agent adapter
- `AgentSandbox` — scoped workspace enforcement

**Acceptance Criteria**
- `IAgent` interface fully implemented
- Claude Code adapter: manifest, runTask, cancel, capabilities
- Task receives scoped workspace with declared permissions
- Agent output normalized: file diffs, logs, artifact refs
- Workspace scope enforcement (writes outside scope are denied)

**Testing**
- Conformance test suite for IAgent
- Mock agent tests: success, partial, failure, timeout
- Integration test: Claude Code actually running (with CI fixture)

### Phase 2 Dependencies
```
Phase 1
  └─→ 2.1 Provider System ──→ 2.2 Context Engine
  └─→ 2.3 Project Contract ──→ 2.4 Agent System
```

### Phase 2 Estimated Complexity
**High** — First real integration with external AI systems.

### Suggested Commit
```
Phase 2: Intelligence Plane integration — Provider System, Context Engine, Project Contract, Agent System
```

---

## Phase 3: Verification & Delivery

**Goal:** Add verification gates, artifact storage, and deployment.

### 3.1 Artifact Manager

| Detail | Value |
|---|---|
| Files | `domain/artifact-manager/artifact_manager.py` |
| Depends on | Phase 1 |
| Interface | `IArtifactManager` |

**Key Classes**
- `ArtifactManager` — content-addressable store
- `ArtifactRef` — stable pointer (hash-based)
- `ProvenanceIndex` — which step/candidate produced each artifact

**Acceptance Criteria**
- Content-addressable storage (hash → content)
- Provenance tracking per artifact
- Diffing between artifact versions
- Immutable — changes create new version with provenance link
- Pluggable storage backends (local disk first)

**Testing**
- Unit test: store → get → verify content
- Unit test: diff between versions
- Unit test: provenance records correct metadata
- Unit test: concurrent stores at same logical path

### 3.2 Verification Engine

| Detail | Value |
|---|---|
| Files | `domain/verification-engine/verification_engine.py`, `domain/verification-engine/checks/` |
| Depends on | 3.1, 2.3 |
| Interface | `IVerificationEngine`, `IVerificationCheck` |

**Key Classes**
- `VerificationEngine` — criteria execution, aggregation
- `BuildCheck` — run build command, check exit code
- `LintCheck` — run linter, check output
- `TestCheck` — run test suite
- `VisualDiffCheck` — screenshot comparison

**Acceptance Criteria**
- Each acceptance criterion maps to a verification check
- Binary verdict per criterion (pass/fail)
- Evidence stored via Artifact Manager (logs, diffs, screenshots)
- `CheckError` distinguished from `Verdict.passed = false`
- Parallel execution of independent checks
- Tiered verification (cheap checks first, expensive only if cheap pass)

**Testing**
- Unit test: all criteria pass → workflow advances
- Unit test: any criterion fails → error recovery triggered
- Unit test: CheckError is retryable, Verdict failure is not
- Integration test: full verification pipeline with mock check

### 3.3 Error Recovery (Formal)

| Detail | Value |
|---|---|
| Files | `domain/error-recovery/error_recovery.py`, `domain/error-recovery/classifier.py` |
| Depends on | 3.2, Phase 1 |
| Interface | `IErrorRecovery` |

**Key Classes**
- `ErrorRecovery` — classification, strategy selection
- `ErrorClassifier` — error → class mapping
- `RecoveryStrategy` — retry, fallback, debug loop, escalate, halt

**Acceptance Criteria**
- Error classification: Transient, Timeout, VerificationFailure, ContractViolation, CapabilityUnresolved, PluginError, Unknown
- Configurable recovery per error class
- Bounded debug loops (max attempts configurable)
- Escalation to human for contract violations
- Error-during-recovery safely halts

**Testing**
- Unit test: each error class maps to correct recovery
- Unit test: debug loop bounded correctly
- Unit test: escalation surfaces clear message
- Unit test: recovery error falls back to halt

### 3.4 Deployment Engine

| Detail | Value |
|---|---|
| Files | `domain/deployment-engine/deployment_engine.py`, `adapters/deployment-targets/vercel/` |
| Depends on | 3.1, 3.2 |
| Interface | `IDeploymentTarget` |

**Key Classes**
- `DeploymentEngine` — deploy coordination, rollback trigger
- `VercelTarget` — first deployment target adapter
- `SmokeCheckRunner` — post-deploy health check

**Acceptance Criteria**
- Deploy only after verification passes
- Deploy/rollback/smoke check lifecycle
- Automatic rollback on smoke check failure
- Deployment URL recorded as artifact
- Vercel adapter deploys static site / Next.js app

**Testing**
- Unit test: deploy refused if verification failed
- Unit test: deploy → smoke check passes → report
- Unit test: deploy → smoke check fails → rollback
- Integration test: actual Vercel deploy (with CI token)

### Phase 3 Estimated Complexity
**Medium-High** — Verification logic is straightforward but deployment API integration is complex.

### Suggested Commit
```
Phase 3: Verification & Delivery — Artifact Manager, Verification Engine, Error Recovery, Deployment Engine
```

---

## Phase 4: Extensibility & Advanced Features

**Goal:** Scale to multiple agents, parallel execution, and plugin ecosystem readiness.

### 4.1 Full Plugin Lifecycle

| Detail | Value |
|---|---|
| Files | `plugins/loader/plugin_loader.py`, `plugins/loader/manifest_validator.py` |
| Depends on | Phase 0 (existing plugin system) |
| Key Changes | `PluginRegistry` → full lifecycle with `onLoad`/`onUnload` |

**Acceptance Criteria**
- Plugin manifest validation against schema
- `onLoad(context)` / `onUnload()` lifecycle
- Plugin sandbox with permission enforcement
- Hot-load during development
- Failure isolation: one plugin crash doesn't affect others

### 4.2 Workspace Manager

| Detail | Value |
|---|---|
| Files | `domain/workspace-manager/workspace_manager.py` |
| Depends on | Phase 1 |
| Interface | `IWorkspaceManager` |

**Acceptance Criteria**
- Provisions scoped filesystem workspaces
- Enforces write-scope boundaries (hard deny)
- Tears down workspaces after task completion
- No orphaned workspaces on crash

### 4.3 Parallel Execution (Full)

| Detail | Value |
|---|---|
| Files | `core/execution-engine/parallel_executor.py` |
| Depends on | 1.3 (Execution Engine), 4.2 |

**Acceptance Criteria**
- True parallel execution of independent steps
- Configurable `maxParallelTasks`
- Per-provider concurrency ceiling enforcement
- Write-scope conflict prevention at scheduling time
- Event Bus events for parallel task lifecycle

### 4.4 Second Provider + Agent

| Detail | Value |
|---|---|
| Files | `adapters/providers/chatgpt/`, `adapters/agents/cursor/` |
| Depends on | 2.1, 2.4 |

**Acceptance Criteria**
- At least 2 provider adapters operational
- At least 2 agent adapters operational
- Capability Registry correctly resolves between them
- Fallback from primary to secondary works

### 4.5 Resume Engine

| Detail | Value |
|---|---|
| Files | `domain/resume-engine/resume_engine.py` |
| Depends on | 1.2 (State Engine) |
| Interface | `IResumeEngine` |

**Acceptance Criteria**
- Detects interrupted runs via State Engine
- Reconstructs in-memory state from last checkpoint
- Never re-executes already-succeeded steps
- Supports: resume as-is, resume with contract update, abort

### Phase 4 Estimated Complexity
**High** — Parallel safety, sandboxing, and multi-adapter validation.

### Suggested Commit
```
Phase 4: Extensibility — plugin lifecycle, workspace manager, parallel execution, multi-adapter, resume engine
```

---

## Phase 5: Product Polish

**Goal:** Make the CLI beautiful, the wizard helpful, and the reports comprehensive.

### 5.1 CLI Live View

| Detail | Value |
|---|---|
| Files | `cli/live-view/live_renderer.py` |
| Depends on | Phase 1 (Event Bus) |

**Acceptance Criteria**
- Event Bus-driven step tree rendering
- Status icons per step (✓ running, ✔ done, ✗ failed, — skipped)
- In-place terminal updates (no scrolling)
- Auto-detect TTY vs. non-TTY (fallback to line-based)
- JSON output mode for CI

### 5.2 Configuration Wizard

| Detail | Value |
|---|---|
| Files | `cli/wizard/config_wizard.py` |
| Depends on | 2.1 (Provider System), Phase 0 |

**Acceptance Criteria**
- Guided step-by-step setup
- Live credential validation
- Detect existing config, only ask for missing
- Provider/agent/deployment target setup
- Zero-to-first-run in under 5 minutes

### 5.3 Report Engine (Full)

| Detail | Value |
|---|---|
| Files | `domain/report-engine/report_engine.py`, `domain/report-engine/renderers/` |
| Depends on | 3.1 (Artifact Manager), 1.2 (State Engine) |

**Acceptance Criteria**
- Report formats: terminal, Markdown, HTML (self-contained)
- Sections: Summary, Timeline, Steps & Outcomes, Cost & Usage, Verification, Deployment, Errors/Retries
- Report generation from persisted data only (no re-querying)
- Partial runs produce partial reports (with clear labeling)

### Phase 5 Estimated Complexity
**Medium** — Mostly presentational, building on existing foundations.

### Suggested Commit
```
Phase 5: Product polish — CLI live view, configuration wizard, full report engine
```

---

## Phase 6: Ecosystem & Supporting Systems

**Goal:** Production-readiness with monitoring, audit, and scalability.

### 6.1 Metrics Engine
| Files | `domain/metrics-engine/metrics_engine.py` |
| Interface | `IMetricsEngine` |
| Criteria | Duration, cost, success rate aggregation; query interface |

### 6.2 Cache Manager
| Files | `domain/cache-manager/cache_manager.py` |
| Interface | `ICacheManager` |
| Criteria | Memoization with TTL; content-hash-based invalidation for correctness caches |

### 6.3 Policy Engine
| Files | `domain/policy-engine/policy_engine.py` |
| Interface | `IPolicyEngine` |
| Criteria | Plugin permissions, auto-resume, auto-deploy gating; declarative rules |

### 6.4 Audit Engine
| Files | `domain/audit-engine/audit_engine.py` |
| Interface | `IAuditEngine` |
| Criteria | Immutable append-only log; hash-chained entries; queryable |

### 6.5 Resource Manager
| Files | `domain/resource-manager/resource_manager.py` |
| Interface | `IResourceManager` |
| Criteria | Budget tracking; concurrent task enforcement; API spend limits |

### 6.6 Template Registry
| Files | `domain/template-registry/template_registry.py` |
| Interface | `ITemplateRegistry` |
| Criteria | Store/discover versioned workflow templates |

### 6.7 Notification System
| Files | `domain/notification-system/notification_system.py` |
| Interface | `INotificationSystem` |
| Criteria | Webhook/email dispatch on events; channel registration |

### 6.8 Version Manager
| Files | `domain/version-manager/version_manager.py` |
| Interface | `IVersionManager` |
| Criteria | Core/plugin/contract compatibility tracking |

### Phase 6 Estimated Complexity
**Medium** — Many small, independent systems.

### Suggested Commit
```
Phase 6: Ecosystem — metrics, cache, policy, audit, resource manager, template registry, notifications, version manager
```

---

## Phase 7: v3.1.0 — Multi-Provider & Scale

**Goal:** Validated scalability and production readiness.

### Acceptance Criteria
- 100 providers registered in Capability Registry
- 1000 workflows executed
- 100 plugins loaded simultaneously
- Multiple simultaneous projects
- Long-running workflows (1+ hour)
- Pause/Resume across process restarts
- All existing functionality backward compatible

### Key Validations
- Provider fallback chain works with 100 providers
- Event Bus handles 1000 events/sec
- State Engine handles 1000 concurrent runs
- Plugin loading time < 1s for 100 plugins
- CLI response time < 100ms for any command

### Suggested Commit
```
Phase 7: v3.1.0 — scalability validation, 100 providers, 1000 workflows, 100 plugins
```

---

## Post-v3.1.0 (Deferred)

| Feature | Reason Deferred |
|---|---|
| Hosted control plane | Requires networked API transport |
| Visual GUI workflow builder | Requires UI framework dependency |
| Team/multi-user mode | Requires shared state store |
| Learned capability scoring | Requires data collection infrastructure |
| Marketplace | Requires signed packages, review process |
| Operator mode | Requires long-running daemon architecture |
| Knowledge Base | Requires vector store dependency |
| HTTP/gRPC API | Requires transport security design |

---

## Effort Summary

| Phase | Est. Days | Complexity | Risk Level | Dependencies |
|---|---|---|---|---|
| 0 | 3-5 | Low | Low | None |
| 1 | 15-20 | High | High | Phase 0 |
| 2 | 20-30 | High | High | Phase 1 |
| 3 | 15-20 | Medium-High | Medium | Phase 2 |
| 4 | 20-25 | High | Medium | Phase 3 |
| 5 | 10-15 | Medium | Low | Phase 4 |
| 6 | 20-25 | Medium | Low | Phase 5 |
| 7 | 15-20 | Medium | Medium | Phase 6 |

**Total Estimated Effort:** 118-160 days (~6-8 months with a single engineer)

---

## Risk Register

| Risk | Phase | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Provider API changes break adapter | 2 | Medium | High | Adapter isolation, conformance tests |
| State Engine I/O becomes bottleneck | 1 | Low | High | Batched writes, async storage backend |
| Parallel agent file conflicts corrupt data | 4 | Medium | Critical | Workspace Manager enforcement + Dependency Resolver |
| Plugin author bad-faith quality declaration | 6 | Low | Medium | Community ratings (future), local benchmarking |
| Context summarization drops hard constraint | 2 | Medium | High | Immutable core never summarized; contract tests |
| Determinism eroded at provider boundary | 1-2 | Medium | High | Validated structuring after every provider call |
| Circular dependency between domain services | 2 | Low | Medium | Strict layering enforcement; interface-first design |
| LLM provider cost exceeds budget | 2 | Low | Medium | Resource Manager budget tracking |
