# 29 — Roadmap

## Purpose
Sequences the architecture defined in this RFC into an implementable order, and lists post-v1 directions referenced throughout the other documents as "future expansion."

## Responsibilities
- Define implementation phases with clear dependency ordering.
- Separate "v1 core" from "explicitly deferred" without pretending deferred items are out of scope forever.

## Recommended Implementation Order

**Phase 0 — Foundation (no user-visible behavior yet)**
1. Configuration System (`12`) + secret handling
2. Event Bus (`17`)
3. Data Models (`25`) as concrete schemas/types
4. State Engine (`09`) — transition log + snapshot, unit-tested against crash-recovery scenarios first

**Phase 1 — Deterministic Core**
5. Workflow Specification parser/validator (`13`)
6. Workflow Engine (`04`) against a stub Execution Engine
7. Dependency Resolver + Execution Engine (`14`) with a fake in-memory provider/agent for testing
8. Decision Engine (`31`) minimal version (rule-based planning only)

**Phase 2 — Intelligence Plane Integration**
9. Provider System (`05`) — one real adapter (e.g., Claude) end-to-end
10. Capability Registry (`07`)
11. Context Engine (`08`) — naive version first (no summarization), summarization added after
12. Project Contract (`10`) + Project Scanner (`18`)

**Phase 3 — Verification & Delivery**
13. Artifact Manager (`16`)
14. Verification Engine (`20`) with `build`/`lint` checks first
15. Error Recovery (`21`) + Resume Engine (`22`)
16. Deployment Engine (`19`) — one target (Vercel) first

**Phase 4 — Agents & Extensibility**
17. Agent System (`06`) — one real adapter (e.g., Claude Code) end-to-end
18. Plugin System (`11`)
19. Second Provider + second Agent adapters, to validate the abstraction under real diversity

**Phase 5 — Product Polish**
20. CLI Design (`23`) full live-view
21. Configuration Wizard (`24`)
22. Report Engine (`15`)

**Phase 6 — Supporting Systems & Ecosystem** (`32`)
23. Metrics Engine, Cache Manager, Workspace Manager (needed for real parallel-agent safety)
24. Policy Engine, Audit Engine (needed before recommending team/enterprise use)
25. Template Registry, Capability Marketplace, Notification System, Version Manager

**Deferred / Post-v1**
- Networked API transport + daemon mode (`27`)
- Team/multi-user mode, shared State Store
- Hosted control-plane product
- Visual/GUI workflow builder
- Learned/benchmarked capability quality scoring

## Trade-offs
Building State Engine and Event Bus before anything user-visible delays the first demo but avoids the common failure mode of retrofitting durability/observability onto an already-complex system.

## Open Questions
Should Phase 2's first real provider integration happen before or after Phase 1's Decision Engine stub — i.e., is it more valuable to validate the deterministic core against total idealized responses first, or against real provider noise as early as possible? Recommendation: real provider as early as possible (Phase 2 before hardening Phase 1 fully), since provider noise is where most design assumptions break.

## References
All documents; this is the sequencing index.

## Supersession Notice
This roadmap is **superseded by** `docs/IMPLEMENTATION_ROADMAP.md` which provides
file-level detail, acceptance criteria, dependencies, and estimated complexity for
each phase. The implementation roadmap accounts for the existing codebase and is
the authoritative sequencing plan.
