# 30 — Glossary

**Agent** — An autonomous coding tool (Claude Code, Cursor, Codex, etc.) that wraps one or more Providers plus tool-use/file access to complete multi-step coding tasks. See `06`.

**Artifact** — Any stored output of a step (file, diff, log, screenshot), addressed by an immutable `ArtifactRef`. See `16`.

**Capability** — A namespaced, declared ability (e.g., `codegen.nextjs`) that Providers/Agents/Tools advertise and that Workflow Steps require. See `07`.

**Capability Registry** — The deterministic component that resolves a capability requirement to a ranked candidate list. See `07`.

**Context Bundle** — A provider-agnostic packaged set of prompt context (contract summary, working set, rolling summary, recent turns). See `08`.

**Decision Engine** — Deterministic planning component that selects among options (never generates new options itself) to produce a workflow plan. See `31`.

**Deployment Target** — An abstraction over a hosting/infra platform (Vercel, Render, etc.) implementing `IDeploymentTarget`. See `19`.

**Event Bus** — In-process pub/sub backbone for observability and reactive extension behavior. See `17`.

**Intelligence Plane** — The set of external, non-deterministic systems (AI Providers, Agents) the Orchestrator coordinates but never replaces. See `00`.

**Control Plane** — The deterministic core (Workflow/State/Execution Engines etc.) that contains zero reasoning. See `02`.

**Plugin** — A third-party package extending the system at a declared extension point without core changes. See `11`.

**Project Contract** — The immutable-per-version specification of intent, constraints, and acceptance criteria for a project. See `10`.

**Provider** — An AI model vendor integration (Claude, ChatGPT, Gemini, etc.) implementing `IProvider`. See `05`.

**Step** — A single node in a Workflow Graph; has a type, dependencies, required capabilities, and a result. See `04`.

**State Engine** — Durable, append-only source of truth for workflow run state, enabling crash recovery and resume. See `09`.

**Verification Engine** — The binary gatekeeper that checks step outputs against acceptance criteria before the graph may advance. See `20`.

**Workflow** — A declarative graph of steps (Workflow Spec YAML) describing how an outcome is achieved. See `13`.

**Workspace** — A sandboxed, scope-limited filesystem/tool context an Agent operates within for a given task. See `06`, `32`.

### v3.0.0 Architecture Freeze Additions

**Audit Engine** — Immutable, tamper-evident record of every consequential action. See `docs/ARCHITECTURE_FREEZE.md`.

**Cache Manager** — Generic memoization layer used by Context Engine, Project Scanner, and Verification Engine.

**Control Plane** — The deterministic orchestration core (Layers 0-2) containing zero reasoning.

**Dependency Resolver** — Component that computes execution order and detects write-scope conflicts.

**Execution Queue** — Priority-based task queue for multi-project orchestration.

**Metrics Engine** — Telemetry aggregation for durations, costs, success rates.

**Policy Engine** — Declarative rules gating risky actions (permissions, auto-resume, auto-deploy).

**Provider Adapter** — An `IProvider` implementation wrapping a specific AI vendor API.

**Resource Manager** — Budget and concurrency enforcement across projects.

**Session Manager** — Multi-project orchestration state coordination.

**Template Registry** — Versioned storage for reusable Workflow Templates.

**Workflow Registry** — Named, versioned workflow definitions.

**Workspace Manager** — Provisions and tears down sandboxed workspaces for Agent tasks.

For the full taxonomy, see `docs/ARCHITECTURE_FREEZE.md` and `docs/ARCHITECTURE_AUDIT.md`.
