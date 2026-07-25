# 10 — Project Contract (Special Document)

## Purpose
The Project Contract is the immutable (per-version) specification of *what* is being built and under what constraints. It is the one artifact every Provider, Agent, and verification step must read and never violate. It is the closest thing this system has to a "constitution" for a given project.

## Responsibilities
- Capture outcome, constraints, tech stack, style conventions, and acceptance criteria in a structured, machine-readable form.
- Be the single input that both humans and every AI provider agree defines "correct."
- Version itself so that changes to intent are explicit, auditable events, not silent drift.

### Definition
The contract is **immutable per version**: once a `ProjectContract@vN` is finalized (moves out of `Draft` status), no component may mutate it in place. A change of intent produces `ProjectContract@vN+1`, and any in-flight `WorkflowRun` continues against the version it started with unless explicitly told to re-plan against the new version. This is what "nothing may violate the contract" means operationally — not that intent can never evolve, but that evolution is always a new, explicit, versioned fact, never a silent edit.

### Every provider reads this contract
Every `ContextBundle` (`08_CONTEXT_ENGINE.md`) includes the current contract's summary layer by construction — no step type is exempt. Verification Engine's acceptance criteria are derived directly from the contract's `acceptanceCriteria` field, so "did the AI do the right thing" is always checked against the same source of truth the AI was given.

## Goals
- Structured enough to be machine-checked (Verification Engine), flexible enough to express a landing page or a backend migration equally well.
- Human-editable (plain YAML/JSON) and diffable via normal version control.
- Composable: a contract can extend/import shared conventions (e.g., an org-wide style guide) without duplicating them per project.

## Non-Goals
- Not a full requirements-management system (no ticketing, no stakeholder sign-off workflow) — it is the *technical* contract, not a product-management artifact.
- Does not itself execute anything; it is pure data read by every other component.

## Architecture
```mermaid
flowchart TB
    User[User Outcome Statement] --> Draft[Contract Draft]
    SharedConv[Shared/Org Conventions] --> Draft
    ScannerFacts[Project Scanner facts, for existing repos] --> Draft
    Draft --> Review[Human Review / Confirm]
    Review --> Finalized[ProjectContract@vN - Immutable]
    Finalized --> CE[Context Engine]
    Finalized --> VE[Verification Engine]
    Finalized --> DecE[Decision Engine]
    Finalized --> Store[(Contract Store, versioned)]
```

## Interfaces
```
interface IProjectContract {
  outcome: string
  version: string                       // semver-like, monotonic per project
  status: "draft" | "finalized" | "superseded"
  techStack: TechStackSpec
  constraints: Constraint[]              // hard rules, e.g. "no new npm deps without approval"
  styleConventions: StyleSpec
  acceptanceCriteria: AcceptanceCriterion[]
  imports?: ContractRef[]                // shared/org-level conventions
}

interface AcceptanceCriterion {
  id: string
  description: string
  verificationMethod: "build" | "test" | "lint" | "visual-diff" | "manual-gate" | "custom-script"
}
```

## Data Models
`ProjectContract`, `Constraint`, `StyleSpec`, `AcceptanceCriterion`, `ContractRef` — `25_DATA_MODELS.md`.

## Workflow
1. User states an outcome (new project) or points at an existing repo (Project Scanner infers facts, `18_PROJECT_SCANNER.md`).
2. Draft contract assembled, optionally importing shared conventions.
3. Human reviews/confirms (CLI prompt or config file edit) — this is the one mandatory manual gate in the entire lifecycle by default.
4. Contract finalized, versioned, stored; workflow planning begins against it.
5. If intent changes mid-project, a new version is drafted and finalized the same way; existing runs are unaffected until explicitly re-planned.

## Examples
```yaml
outcome: "Build a premium SaaS landing page"
version: "1.0.0"
status: "finalized"
techStack:
  framework: "nextjs@15"
  styling: "tailwindcss"
  deployment: "vercel"
constraints:
  - "no analytics scripts without explicit opt-in"
  - "must pass WCAG AA contrast checks"
acceptanceCriteria:
  - id: "builds-clean"
    description: "next build completes with zero errors"
    verificationMethod: "build"
  - id: "lighthouse-perf"
    description: "Lighthouse performance score >= 90"
    verificationMethod: "custom-script"
```

## Failure Scenarios
- An agent proposes a dependency not permitted by `constraints` — Verification Engine must reject the step's output even if it "works," because contract violation is itself a failure mode, not just broken code.
- Contract left in `Draft` indefinitely — Workflow Engine refuses to start execution steps (only `plan`-type steps) against a non-finalized contract.

## Future Expansion
- Org-wide contract template registry (`32_SUPPORTING_SYSTEMS.md` — Template Registry) for consistent conventions across many projects.
- Machine-assisted contract drafting (a provider proposes a draft from a one-line outcome) — still requires the human confirmation gate before finalization.

## Trade-offs
- Requiring a mandatory human confirmation gate for finalization slows the "fully autonomous" fantasy but is the deliberate safety/control anchor of the whole system.

## Open Questions
- Should constraints support arbitrary custom-script validation at draft time (catching contradictions before finalization), beyond the acceptance-criteria-level custom scripts?

## References
`00_VISION.md`, `08_CONTEXT_ENGINE.md`, `20_VERIFICATION_ENGINE.md`, `18_PROJECT_SCANNER.md`, `31_DECISION_ENGINE.md`
`docs/ARCHITECTURE_FREEZE.md` — Frozen architecture: Project Contract schema and lifecycle
`docs/IMPLEMENTATION_ROADMAP.md` — Phase 2.3: Project Contract System implementation

**Implementation Status:** Design only — the `WorkflowDefinition` class is a partial seed. See `docs/ARCHITECTURE_AUDIT.md`.
