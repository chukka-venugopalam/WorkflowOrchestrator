# Architecture Freeze

> **Architecture Version:** 3.0.0
> **Freeze Date:** 2026-07-18
> **Status:** FROZEN — Do not modify without Breaking Change Policy approval
> **Project:** Workflow Orchestrator v3

---

## Vision

Workflow Orchestrator is a **deterministic, provider-agnostic workflow operating system** for software engineering. It coordinates:

- **AI Providers** (Claude, ChatGPT, Gemini, future models)
- **Coding Agents** (Claude Code, Cursor, Codex, GitHub Copilot, OpenCode, FreeBuff)
- **Developer Tools** (Git, VS Code, Browser, Terminal, Clipboard)
- **Deployment & Verification Infrastructure** (Render, Vercel, CI runners, test frameworks)

The Orchestrator **never reasons**. It only executes deterministic workflows. All intelligence comes from external providers.

---

## Core Principles

1. **Determinism First** — Given the same inputs, the Orchestrator's control-flow decisions are reproducible. Non-determinism is pushed exclusively to external providers.

2. **Strict Layering** — Control Plane (deterministic) and Intelligence Plane (non-deterministic) are strictly separated. No component in the Control Plane may import or depend on any component in the Intelligence Plane.

3. **Provider Independence** — No core component may hard-code assumptions about any specific AI vendor beyond what is declared through the Provider interface.

4. **Interface over Implementation** — Every component communicates through declared interfaces. No shared mutable state between components.

5. **Immutable Audit Trail** — All state transitions are recorded in an append-only log. Nothing is ever deleted or overwritten.

6. **Human-in-the-Loop by Default** — Verification gates require explicit confirmation for contract finalization, deployment, and contract-violation recovery.

7. **Local-First** — No mandatory SaaS backend, no forced telemetry. The system runs entirely on the user's machine.

---

## Architectural Rules

### Rule 1: Layer Dependency Direction
A layer may depend only on layers at or below it:

```
Layer 0: CLI / Entry Points           → Layer 1 only
Layer 1: Orchestration Core           → no imports from Layer 3 or 4
Layer 2: Domain Services              → Layer 1 interfaces only
Layer 3: Abstraction / Adapters       → Layer 2 interfaces only
Layer 4: External Systems             → never calls upward
```

### Rule 2: No Reasoning in Core
No module in Layer 0, 1, or 2 may:
- Call an AI model provider directly
- Generate or evaluate code quality
- Make subjective judgments
- Perform LLM-based matching

All reasoning is delegated to Layer 4 through Layer 3 adapters.

### Rule 3: Singleton-Free Injection
No component may access a global singleton directly. Dependencies must be injected:
- ✅ `Engine(registry=registry)` 
- ❌ `engine._registry = default_registry`

### Rule 4: Write-Ahead Persistence
Every state transition must be persisted to the append-only log BEFORE any side-effecting action is taken. Never after.

### Rule 5: Capability Namespacing
All capability IDs must be namespaced:
- Core capabilities: `codegen.nextjs`, `deploy.vercel`, `verify.build`
- Community capabilities: `community.author.capability-name`

### Rule 6: Verification Before Deploy
No deployment step may execute unless all preceding verification steps have passed.

### Rule 7: Bounded Loops
Every `loop` construct must declare a maximum iteration bound or an explicit exit condition. Infinite loops are forbidden.

---

## Non-Negotiable Decisions

| Decision | Rationale |
|---|---|
| **No AI in the core** | Preserves determinism, auditability, and provider-independence |
| **Append-only transition log** | Required for crash recovery, audit, and rollback |
| **Human gate on contract finalization** | Prevents silent drift of project intent |
| **Plugin sandboxing** | Required for safe parallel agent execution |
| **YAML workflow specs** | Human-readable, diffable, PR-reviewable |
| **CLI-first (no GUI in v3)** | Keeps core scriptable and composable with CI |
| **Local-first architecture** | No vendor lock-in, offline-capable |

---

## Folder Structure

```
workflow_orchestrator/
├── core/                          # Layer 1 — Deterministic Orchestration
│   ├── workflow-engine/           # Graph walking, step dispatch
│   ├── state-engine/              # State machine, transition log, snapshots
│   ├── execution-engine/          # Scheduling, parallelism, retry, timeout
│   ├── event-bus/                 # In-process pub/sub
│   ├── dependency-resolver/       # Dependency detection, conflict prevention
│   ├── decision-engine/           # Rule-based planning, fallback selection
│   └── __init__.py
│
├── domain/                        # Layer 2 — Domain Services
│   ├── capability-registry/       # Capability indexing, resolution, ranking
│   ├── context-engine/            # Context assembly, summarization, rendering
│   ├── project-contract/          # Contract versioning, validation
│   ├── artifact-manager/          # Content-addressed storage, provenance
│   ├── verification-engine/       # Criteria execution, verdict aggregation
│   ├── error-recovery/            # Error classification, recovery strategies
│   ├── resume-engine/             # Run reconstruction, checkpoint management
│   ├── report-engine/             # Multi-format report generation
│   ├── project-scanner/           # Existing project analysis
│   ├── deployment-engine/         # Deploy/rollback/smoke-check abstraction
│   ├── workspace-manager/         # Sandboxed workspace provisioning
│   ├── metrics-engine/            # Telemetry aggregation
│   ├── policy-engine/             # Declarative rules for risky actions
│   ├── audit-engine/              # Immutable, tamper-evident action log
│   ├── cache-manager/             # Memoization layer
│   ├── resource-manager/          # Budget tracking, concurrency enforcement
│   ├── template-registry/         # Workflow template storage
│   ├── workflow-registry/         # Named workflow definitions
│   └── __init__.py
│
├── adapters/                      # Layer 3 — Abstraction / Adapters
│   ├── providers/                 # IProvider implementations
│   │   ├── anthropic-claude/
│   │   ├── chatgpt/
│   │   ├── gemini/
│   │   └── __init__.py
│   ├── agents/                    # IAgent implementations
│   │   ├── claude-code/
│   │   ├── cursor/
│   │   ├── codex/
│   │   ├── github-copilot/
│   │   ├── opencode/
│   │   ├── freebuff/
│   │   └── __init__.py
│   ├── tools/                     # ITool implementations
│   │   ├── git/
│   │   ├── vscode/
│   │   ├── browser/
│   │   ├── terminal/
│   │   ├── clipboard/
│   │   └── __init__.py
│   ├── deployment-targets/        # IDeploymentTarget implementations
│   │   ├── vercel/
│   │   ├── render/
│   │   └── __init__.py
│   ├── step-handlers/             # Custom step type implementations
│   │   └── __init__.py
│   └── __init__.py
│
├── plugins/                       # Plugin System runtime + installed plugins
│   ├── loader/                    # Plugin loader, validator, sandbox
│   ├── marketplace/               # Future marketplace integration
│   └── installed/                 # Installed community plugins
│
├── cli/                           # Layer 0 — Entry Points
│   ├── commands/                  # Command implementations
│   ├── live-view/                 # Event Bus-driven progress rendering
│   ├── wizard/                    # Configuration wizard
│   └── __init__.py
│
├── config/                        # Configuration System
│   ├── defaults.yaml              # Built-in defaults
│   ├── schema.json                # Config schema for validation
│   └── __init__.py
│
├── data/                          # Data storage (user-local)
│   ├── config.json                # Merged configuration
│   └── profiles/                  # YAML config profiles
│
├── docs/                          # Architecture documentation
│   ├── ARCHITECTURE_FREEZE.md     # This file
│   ├── ARCHITECTURE_AUDIT.md      # Audit of all documents
│   └── IMPLEMENTATION_ROADMAP.md  # Implementation phases
│
├── reports/                       # Execution reports (auto-generated)
│
├── tests/                         # Test suite
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   ├── conformance/               # Plugin/adapter conformance tests
│   └── fixtures/                  # Test data
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Core Components

### 1. Workflow Engine (Layer 1)
**Purpose:** Interpret a Workflow Spec (declarative graph of steps) and drive it to completion.

**Interfaces:**
```
IWorkflowEngine:
  loadSpec(spec: WorkflowSpec) → WorkflowGraph
  start(graph, contract) → RunHandle
  advance(run) → StepBatch           # returns next ready steps
  reportResult(run, stepId, result) → void
  status(run) → WorkflowStatus
  cancel(run) → void
```

**Key Properties:**
- Walks a directed acyclic graph, never a flat list
- Each step has states: `pending → ready → running → {succeeded, failed, skipped}`
- Delegates execution to ExecutionEngine, persistence to StateEngine
- Emits lifecycle events for every transition

### 2. Execution Engine (Layer 1)
**Purpose:** Schedule and dispatch ready steps with parallelism, retry, and timeout management.

**Interfaces:**
```
IExecutionEngine:
  execute(batch: StepBatch) → Promise<StepResultBatch>
  cancelStep(stepId) → void
  cancelRun(runId) → void
```

**Key Properties:**
- Separate Parallel Executor and Sequential Executor
- Dependency Resolver computes conflict-free execution order
- Retry policy with error-class-aware backoff
- Hard timeout enforcement per step

### 3. State Engine (Layer 1)
**Purpose:** Single source of truth for workflow run state with durable, append-only persistence.

**Interfaces:**
```
IStateEngine:
  createRun(project, graph) → RunHandle
  transition(run, event) → RunSnapshot
  currentSnapshot(run) → RunSnapshot
  history(run) → TransitionRecord[]
  interruptedRuns() → RunHandle[]
  rollback(run, toCheckpoint) → RunSnapshot
```

**Key Properties:**
- Append-only transition log (write-ahead, never write-after)
- Materialized current-state snapshot rebuilt from log
- Heartbeat monitoring for crash detection
- Abstracted storage backend (`IStateStore`)

### 4. Event Bus (Layer 1)
**Purpose:** Typed publish/subscribe backbone for observability without coupling.

**Interfaces:**
```
IEventBus:
  publish(event) → void
  subscribe(pattern, handler) → Subscription
  unsubscribe(sub) → void
```

**Key Properties:**
- Event taxonomy: `workflow.*`, `step.*`, `state.*`, `capability.*`, `agent.*`, `provider.*`, `deployment.*`, `plugin.*`
- At-least-once delivery in-process
- Synchronous publish, asynchronous subscriber processing
- Event taxonomy is an open string namespace for plugin extensibility

### 5. Decision Engine (Layer 1)
**Purpose:** Rule-and-policy-based planner and selector. Decides *among* options, never generates them.

**Interfaces:**
```
IDecisionEngine:
  planFromOutcome(outcome, contract) → WorkflowGraph
  chooseFallback(req, excluding) → CandidateRef | null
  decideRecovery(error, context) → RecoveryAction
```

**Key Properties:**
- Template-first planning (fast path), provider-proposed planning (fallback)
- Provider-proposed plans are always validated before acceptance
- Every decision is traceable to an explicit rule

### 6. Dependency Resolver (Layer 1)
**Purpose:** Compute execution order from declared dependencies and write-scope metadata.

**Interfaces:**
```
IDependencyResolver:
  resolve(graph: WorkflowGraph) → ExecutionOrder
  nextReadyBatch(run) → StepBatch
  conflicts(steps) → ConflictReport
```

**Key Properties:**
- Computes DAG from `dependsOn` edges
- Detects write-scope overlaps to prevent parallel conflicts
- Rejects cyclic dependencies before execution

---

## Provider System (Layer 3)

### Provider Interface
```
IProvider:
  manifest() → ProviderManifest
  healthCheck() → Promise<HealthStatus>
  invoke(request) → Promise<ProviderResponse>
  supportsStreaming() → boolean
  estimateCost(request) → CostEstimate

ProviderManifest:
  id, version, capabilities[], costModel, rateLimits, contextWindow, deprecated?
```

### Provider Lifecycle
```
Registered → HealthChecking → {Available | Degraded | Unavailable}
Available → InUse → Available
Degraded → Available | Unavailable
Unavailable → HealthChecking (periodic retry)
Available → Deprecated → [*]
```

### Provider Rules
- Every provider must implement `IProvider` with all five methods
- Health checks run on startup and after N consecutive failures
- Raw vendor errors are never passed to the core — adapted into typed `ProviderError` subclasses
- Provider-specific superpowers require opt-in "extension capabilities"

---

## Agent System (Layer 3)

### Agent Interface
```
IAgent:
  manifest() → AgentManifest
  runTask(task, workspace) → Promise<AgentResult>
  cancel(taskId) → void
  capabilities() → CapabilityDeclaration[]

AgentManifest:
  id, capabilities[], requiresLocalRuntime, supportsParallelTasks, sandboxRequirements
```

### Agent Rules
- Agents are black boxes — only artifacts and results flow back
- Each agent task receives a scoped workspace with explicit file/tool permissions
- Two agents with overlapping write-scopes may never run in parallel
- Agent outputs are normalized into `AgentResult` with diffs, logs, and artifact references

---

## Capability Registry (Layer 2)

### Design
```
ICapabilityRegistry:
  register(manifest) → void
  deregister(candidateId) → void
  resolve(req) → RankedCandidates
  updateHealth(candidateId, status) → void
  listCapabilities() → CapabilityTaxonomyEntry[]
```

### Resolution Algorithm
1. Filter by capability ID match + hard constraints (cost ceiling, min quality)
2. Exclude `Unavailable` candidates
3. Sort by: (a) user pin, (b) quality descending, (c) costTier ascending, (d) latencyClass
4. Return ranked list; Execution Engine uses top, falls back on failure

### Capability Taxonomy
- Versioned, extensible enum-like registry
- New IDs are author-namespaced: `community.author.capability-name`
- Built-in taxonomy: `codegen.*`, `reasoning.*`, `verify.*`, `deploy.*`, `tool.*`

---

## Context Engine (Layer 2)

### Context Assembly Layers
1. **Immutable core** — Project Contract summary (never summarized)
2. **Relevant working set** — files/artifacts from dependency steps
3. **Rolling summary** — compressed summary of prior step outputs
4. **Budget enforcement** — trim layers 3, then 2, before touching layer 1

### Template Rendering
- Each step `type` maps to a prompt template
- Templates are versioned and stored per-project
- Cross-provider communication uses provider-agnostic `ContextBundle` intermediate representation

---

## Project Contract (Layer 2)

### Contract Schema
```
ProjectContract:
  outcome: string
  version: semver
  status: draft | finalized | superseded
  techStack: { framework, styling, deployment, ... }
  constraints: Constraint[]
  styleConventions: StyleSpec
  acceptanceCriteria: AcceptanceCriterion[]
  imports?: ContractRef[]
```

### Contract Rules
- Immutable per version — changes produce `@vN+1`
- Every `ContextBundle` includes the contract summary
- Verification Engine criteria derived directly from `acceptanceCriteria`
- Human confirmation gate required before `Draft → Finalized`

---

## Plugin System (Layer 3)

### Plugin Lifecycle
```
PluginManifest → Validate → Load → onLoad(context) → Register → Active
Active → onUnload() → Deregister → [*]
```

### Extension Points
Plugins may register as:
- `provider` — implements `IProvider`
- `agent` — implements `IAgent`
- `tool` — implements `ITool`
- `step-type` — registers `StepTypeHandler`
- `verification-check` — implements `IVerificationCheck`
- `deployment-target` — implements `IDeploymentTarget`
- `cli-command` — adds CLI subcommands

### Sandbox Rules
- Plugin permissions declared in manifest, enforced at load time
- Permissions cross-checked against Policy Engine rules
- Plugin failure during `onLoad` isolates to that plugin only (non-fatal)

---

## Configuration System (Layer 0)

### Precedence (lowest to highest)
```
Built-in defaults < Global user config < Project config < Environment overrides < CLI flags
```

### Secret Handling
- Secrets resolved lazily, scoped to the specific adapter call
- Never written to logs, reports, or state snapshots
- OS keychain by default, environment variable as fallback

---

## Event Bus Event Taxonomy

| Namespace | Events |
|---|---|
| `workflow.*` | `started`, `completed`, `failed`, `cancelled`, `paused`, `resumed` |
| `step.*` | `pending`, `ready`, `running`, `completed`, `failed`, `skipped`, `retrying` |
| `state.*` | `transition`, `checkpoint`, `snapshot_rebuilt`, `rollback` |
| `capability.*` | `registered`, `deregistered`, `resolved`, `fallback`, `unresolved`, `deprecated_used` |
| `agent.*` | `task_started`, `step`, `tool_call`, `completed`, `failed` |
| `provider.*` | `health_check`, `rate_limited`, `error`, `deprecated` |
| `deployment.*` | `started`, `succeeded`, `failed`, `rolled_back`, `smoke_check` |
| `plugin.*` | `loaded`, `unloaded`, `error`, `permission_denied` |
| `verification.*` | `started`, `criterion_passed`, `criterion_failed`, `completed` |
| `report.*` | `generated` |

---

## Data Model Entity Relationships

```
Project 1──* ProjectContract (versioned)
ProjectContract 1──* WorkflowRun
WorkflowRun 1──1 WorkflowGraph
WorkflowGraph 1──* StepDefinition
StepDefinition 1──* ExecutionAttemptRecord
ExecutionAttemptRecord 1──* ArtifactRef
WorkflowRun 1──* TransitionRecord
StepDefinition 1──* Verdict
WorkflowRun 1──* DeploymentResult
WorkflowRun 1──1 ReportDocument
```

---

## Verification Engine Design

### Verification Flow
```
AcceptanceCriteria + Artifact → IVerificationCheck[] run in workspace
  → Verdict per criterion → Aggregate pass/fail → Workflow Engine
```

### Check Types (Extensible)
- `build` — compile/build check
- `test` — test suite execution
- `lint` — code style/lint check
- `visual-diff` — screenshot comparison
- `manual-gate` — human confirmation
- `custom-script` — arbitrary script execution

### Rules
- Binary verdicts only — "close enough" is never accepted
- `CheckError` (infrastructure) vs. `Verdict.passed = false` (genuine failure) are always distinguished
- Evidence (logs, diffs, screenshots) stored via Artifact Manager

---

## Error Recovery Strategy

### Error Classification
| Error Class | Examples | Default Recovery |
|---|---|---|
| `Transient` | Rate limit, network timeout | Auto-retry with backoff |
| `Timeout` | Step exceeded timeout | Retry or escalate |
| `VerificationFailure` | Build failed, lint error | Debug loop (bounded) |
| `ContractViolation` | Agent violated constraint | Escalate to human |
| `CapabilityUnresolved` | No provider for requirement | Fallback or halt |
| `PluginError` | Plugin crash | Halt run |
| `Unknown` | Unclassified error | Escalate then halt |

### Recovery Actions
- `retry` — auto-retry with backoff
- `fallback_candidate` — use next candidate from Capability Registry
- `debug_loop` — insert agent_task with failure context (bounded)
- `escalate` — surface to Decision Engine or human
- `halt` — stop run with clear error message

---

## Deployment Engine Design

### Interface
```
IDeploymentTarget:
  manifest() → DeploymentTargetManifest
  deploy(bundle) → Promise<DeploymentResult>
  rollback(deploymentId) → Promise<void>
  smokeCheck(deploymentId) → Promise<HealthStatus>
```

### Deployment Flow
```
Verification pass → Resolve target → Build DeployableBundle
  → Adapter.deploy() → Smoke check → {pass: report | fail: rollback}
```

---

## Workspace Manager Design

### Interface
```
IWorkspaceManager:
  provision(scope) → WorkspaceHandle
  teardown(handle) → void
```

### Rules
- Each agent task gets an isolated workspace (subset of project or clone/worktree)
- Workspace scope is declared upfront
- Attempting to write outside scope is hard-denied (not silently allowed)
- Workspace is torn down after task completion

---

## Policy Engine Design

### Interface
```
IPolicyEngine:
  evaluate(action) → PolicyDecision  // allow | deny | require_confirmation
```

### Policy-Checked Actions
- Plugin permissions (`filesystem:write`, `network`, `process:spawn`)
- Auto-resume decisions
- Auto-deploy to production targets
- Contract constraint overrides

---

## Audit Engine Design

### Design
- Immutable, append-only action record
- Hash-chained entries for tamper detection
- Records: plugin loads, state transitions, user decisions, contract changes
- Queryable by time range, action type, plugin ID

---

## Supporting Systems (Layer 2)

| System | Purpose |
|---|---|
| Metrics Engine | Telemetry aggregation (durations, costs, success rates) |
| Resource Manager | Budget enforcement (concurrent tasks, API spend) |
| Cache Manager | Memoization (scan results, context bundles, verified artifacts) |
| Template Registry | Reusable Workflow Template storage and discovery |
| Workflow Registry | Named, versioned workflow definitions |
| Notification System | External channel delivery (webhook, email) |
| Version Manager | Core/plugin/contract schema compatibility tracking |
| Knowledge Base | Project-specific retrieval store for Context Engine |

---

## Future Reserved Components

| Component | Layer | Purpose |
|---|---|---|
| Session Manager | 2 | Multi-project orchestration state |
| Dependency Resolver (formal) | 1 | Already present — placeholder for richer conflict detection |
| Manifest System | 2 | Plugin/Provider/Agent manifest versioning and verification |
| Provider Health Monitor | 3 | Dedicated daemon for provider health tracking |
| Execution Queue | 1 | Priority-based task queuing across projects |
| Retry Policy Engine | 1 | Configurable, error-class-aware retry strategies |
| Version Manager | 2 | Compatibility tracking across all versioned components |
| Script Executor | 2 | General-purpose script execution step |
| Resource Scheduler | 1 | Advanced resource-aware scheduling |
| Event Dispatcher | 1 | Cross-process event forwarding |

---

## Breaking Change Policy

A change is **breaking** if it:

1. Changes any interface in the `I*` namespace
2. Removes or renames a public function/class
3. Changes the YAML workflow spec schema (`apiVersion` bump)
4. Changes the event taxonomy namespace
5. Changes the configuration schema
6. Changes the plugin extension point signature
7. Changes the State Engine transition log format
8. Removes a documented CLI command
9. Changes capability resolution semantics

### Breaking Change Process
1. Document the change in `docs/CHANGELOG.md`
2. Bump major version number
3. Provide migration guide
4. Maintain backward compatibility for one major version cycle

---

## Implementation Rules

1. **Test-first development** — Every interface must have conformance tests before implementation
2. **No global state** — All dependencies injected through constructors
3. **Single file per component** — Each `I*` interface in a dedicated file
4. **Async-first for I/O** — Provider/Agent/Tool adapters use async interfaces
5. **Immutable data models** — All entities are frozen dataclasses
6. **No circular imports** — Enforced by lint rule
7. **Type-annotated everywhere** — `mypy --strict` compliance required
8. **Log through Event Bus** — Direct `logging` calls only for startup/shutdown

---

## Versioning Policy

| Component | Version Source | Bump Triggers |
|---|---|---|
| Architecture | `docs/ARCHITECTURE_FREEZE.md` | Breaking change to any component |
| Core API | `OrchestratorApi` class | Interface changes |
| Workflow Spec | `apiVersion` field in YAML | Schema changes |
| Plugin Interface | `PluginManifest` version | Extension point signature changes |
| Data Models | `models.py` | Field changes to entities |
| Configuration | `schema.json` | Config key changes |
| Event Taxonomy | Event type strings | New or renamed event types |

---

## MVP Scope

### In-Scope (v3.0.0)
- [x] CLI with Typer
- [x] Sequential workflow execution
- [x] Plugin system (7 plugins)
- [x] YAML workflow definitions
- [x] Scheduler
- [x] Project scanning
- [x] Execution reporting
- [x] Configuration profiles
- [ ] Event Bus implementation
- [ ] State Engine with transition log
- [ ] Capability Registry
- [ ] Split WorkflowEngine / ExecutionEngine
- [ ] Provider System (first adapter: Claude)
- [ ] Agent System (first adapter: Claude Code)
- [ ] Context Engine
- [ ] Project Contract system
- [ ] Artifact Manager
- [ ] Verification Engine
- [ ] Error Recovery (formal classification)
- [ ] Workspace Manager
- [ ] Decision Engine (template-first)
- [ ] Resume Engine
- [ ] Deployment Engine (Vercel adapter)
- [ ] Cache Manager
- [ ] Metrics Engine

### Out-of-Scope (v3.0.0)
- Hosted control-plane product
- Visual/GUI workflow builder
- Team/multi-user mode
- Networked API transport (HTTP/gRPC)
- Learned/benchmarked capability scoring
- Marketplace of community plugins
- Operator mode (long-running daemon)
- Webhook/notification system
- Audit Engine (tamper-evident)
- Knowledge Base

---

## Success Criteria

### v3.0.0 Release Criteria
1. **End-to-end workflow**: `orchestrator run "build landing page"` produces a working, deployed Next.js site
2. **Determinism**: Given same contract + provider response, same graph is produced
3. **Resumability**: Crash mid-run recovers to last checkpoint without re-executing steps
4. **Extensibility**: New provider plugin can be added in <100 lines of code
5. **Performance**: 100-step sequential workflow completes within provider latency bounds
6. **Test coverage**: >80% line coverage for core modules
7. **Documentation**: All interfaces documented with examples

### v3.1.0 Release Criteria
8. **Parallel execution**: Independent steps run concurrently within configurable limits
9. **Multi-provider**: At least 3 provider adapters operational
10. **Verification gates**: Build/lint/visual-diff checks block bad deployments
11. **Plugin marketplace**: At least 5 community plugins published

---

## References

- `00_VISION.md` — North star vision document
- `02_ARCHITECTURE.md` — Original architecture diagram (superseded by this document)
- `docs/ARCHITECTURE_AUDIT.md` — Complete audit of all documents and code
- `docs/IMPLEMENTATION_ROADMAP.md` — Phased implementation plan
- All documents 03–33 — Detailed component specifications (aligned to this freeze)
