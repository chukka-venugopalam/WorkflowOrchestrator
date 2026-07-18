# 33 — Overall Architecture Review

## Purpose
The critical self-assessment requested alongside the specification itself: risks, bottlenecks, missing components (now addressed in `31`/`32`), future opportunities, and recommended implementation order (detailed fully in `29_ROADMAP.md`).

## Overall Assessment
The layered Control-Plane/Intelligence-Plane split (`02_ARCHITECTURE.md`) is the load-bearing idea of this architecture, and it holds up: every subsystem's non-goals consistently reinforce "orchestration logic here, reasoning there." The riskiest seams are at the boundaries where determinism is hardest to maintain — Decision Engine's plan generation, Context Engine's summarization, and Error Recovery's debug loops — because all three sit right at the edge where Provider output re-enters deterministic control flow. The design mitigates this consistently: validated structuring after every Provider call, never trusting raw output as control-flow input directly.

## Risks
1. **Determinism erosion at the edges.** Every place a Provider's freeform output influences control flow (Decision Engine planning, Error Recovery debug context, Context Engine summarization) is a spot where "deterministic given the same inputs" quietly becomes "deterministic given the same inputs *and* the same non-deterministic Provider response." This is inherent to the problem domain, not a flaw, but it must be documented honestly rather than papered over — which is why `31_DECISION_ENGINE.md` explicitly calls out the validated-structuring boundary.
2. **Sandbox/workspace safety under real parallelism.** The Execution Engine's conflict-prevention logic depends entirely on accurate `workspaceScope` declarations from Agent tasks. A misbehaving or under-declaring agent adapter is the single most plausible source of real data corruption in this system. This is why Workspace Manager was flagged for an earlier implementation phase in the roadmap review.
3. **Capability manifest honesty.** The Capability Registry's determinism depends on self-declared `quality`/`costTier` metadata being roughly accurate. A bad-faith or careless community plugin can skew selection. Mitigation (community rating overlays, local benchmarking) is explicitly deferred, which is an acceptable v1 trade-off but a real gap.
4. **Context budget/summarization correctness.** Silently over-aggressive summarization could drop a hard constraint. The design's layered "immutable core never summarized" approach mitigates this but depends on correct classification of what belongs in the immutable core at Project Contract authoring time.

## Bottlenecks
1. **Verification Engine is a serialization point.** Every step that gates further progress (commit, deploy) must pass through it; slow or flaky checks (e.g., full E2E test suites) throttle overall run latency. Mitigate via parallel check execution within a single verification stage and tiered verification (cheap checks first, expensive checks only if cheap ones pass).
2. **State Engine's write-ahead-per-transition guarantee** trades throughput for durability. For very high-frequency event workflows (many small parallel steps), this could become an I/O bottleneck. Mitigate with batched-but-still-atomic-per-run writes if profiling shows this matters in practice — but never relax the "log before side effect" ordering.
3. **Provider rate limits** are an external bottleneck the Capability Registry's fallback logic mitigates but cannot eliminate — genuinely parallel, high-throughput workflows will be gated by vendor-side limits regardless of internal architecture quality.

## Missing Components (Addressed)
Decision Engine (`31`) and the eleven Supporting Systems (`32`) were identified as gaps in the original spec's step-by-step lifecycle and have been added. Of these, **Workspace Manager** and **Cache Manager** are flagged as more architecturally load-bearing than the "supporting" grouping might suggest — both directly gate correctness (safe parallelism, cache-invalidation correctness) rather than being purely nice-to-have, and the roadmap reflects this by moving them earlier than the rest of the group.

## Future Opportunities
- **Operator mode**: a long-running Orchestrator process pursuing a backlog of outcomes autonomously within Policy Engine-defined bounds, rather than one-shot CLI invocations.
- **Learned capability scoring**: opt-in telemetry feeding community-aggregated quality scores, strictly advisory per `07_CAPABILITY_REGISTRY.md`'s open question.
- **Hosted control plane**: a natural extension once the networked API transport (`27_API_SPECIFICATION.md` future work) exists, without needing to change the core's local-first architecture.
- **Cross-project Knowledge Base**: org-wide learned conventions feeding Context Engine and Decision Engine template matching.

## Recommended Implementation Order
See `29_ROADMAP.md` for the full phased plan. Summary: Foundation (config/events/state) → Deterministic Core (workflow/execution/decision) → Intelligence Plane integration (one real provider end-to-end) → Verification & Delivery → Agents & Extensibility → Product Polish → Supporting Systems, with Workspace Manager and Cache Manager pulled forward into the Agents phase rather than left to the end.

## Trade-offs Accepted
This architecture consistently chooses determinism, auditability, and provider-independence over maximum autonomy, raw speed, or minimal implementation effort. That is the correct choice for a system whose stated ambition is to become long-term open-source infrastructure (per `00_VISION.md`'s framing against Kubernetes/Docker/Git/Linux) rather than a fast demo.

## Open Questions Carried Forward
- Where exactly should the line sit between "bounded, validated Provider-influenced planning" and "the Orchestrator has started reasoning"? This document does not resolve it definitively — it is the single most important ongoing design conversation for whoever implements `31_DECISION_ENGINE.md`.
- How much of the Supporting Systems group deserves to graduate into full architectural documents once real usage data exists?

## References
This document synthesizes `00`, `02`, `04`, `09`, `14`, `20`, `21`, `31`, `32`, `29`.

## Supersession Notice
This self-assessment is **superseded by** `docs/ARCHITECTURE_AUDIT.md` which provides
a comprehensive document-by-document audit of all 33 RFCs against the actual codebase.
The audit identifies code-vs-document gaps, contradictions, duplicated concepts, and
missing systems that this earlier review did not cover.
