# Context Engine

## Architecture

The Context Engine assembles layered context from multiple sources for use by providers and agents. All context assembly is deterministic — no AI reasoning.

```
┌─────────────────────────────────────────────────────────────────┐
│                        ContextEngine                            │
│                                                                 │
│  ┌────────────┐  ┌─────────────┐  ┌─────────┐  ┌───────────┐  │
│  │ ContextBldr │  │ContextBudget│  │Compressor│  │ContextIdx │  │
│  └──────┬─────┘  └──────┬──────┘  └────┬────┘  └─────┬─────┘  │
│         │               │              │             │          │
│         ▼               ▼              ▼             ▼          │
│  ┌────────────────────────────────────────────────────────┐     │
│  │                   ContextAssembly                       │     │
│  │  8 layers with budget enforcement and pruning info     │     │
│  └────────────────────────────────────────────────────────┘     │
│         │                                │                      │
│         ▼                                ▼                      │
│  ┌────────────┐                  ┌──────────────┐              │
│  │ContextCache│                  │SnapshotMgr   │              │
│  └────────────┘                  └──────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## 8 Context Layers

| Layer | Priority | Never Pruned | Description |
|---|---|---|---|
| 1. Project Contract | CRITICAL | ✅ | Project vision, requirements, constraints |
| 2. Workflow State | CRITICAL | ✅ | Current execution status, completed steps |
| 3. Relevant Artifacts | HIGH | ❌ | Step outputs, build logs, test results |
| 4. Execution History | HIGH | ❌ | Prior step results and decisions |
| 5. Relevant Knowledge | NORMAL | ❌ | Knowledge base matches for current context |
| 6. User Preferences | NORMAL | ❌ | User-configured preferences |
| 7. Recent Errors | LOW | ❌ | Recent errors for context-aware recovery |
| 8. Rolling Summary | OPTIONAL | ❌ | Compressed summary of prior steps |

## Budget Enforcement

1. CRITICAL layers always included in full
2. HIGH layers included if budget allows
3. NORMAL layers compressed if budget is tight
4. LOW layers only if ample budget remains
5. OPTIONAL layers pruned first

## Key Components

| Component | Description |
|---|---|
| ContextEngine | Main orchestrator for assembly, caching, snapshots |
| ContextBuilder | Collects content from data sources |
| ContextBudget | Allocates and enforces token budgets |
| ContextCompressor | Deterministic compression (truncation, sections, keywords) |
| ContextIndex | Fast key/layer/tag-based content lookup |
| ContextSelector | Selects relevant context for steps, errors, phases |
| ContextSnapshot | Persistent context snapshots for reuse/rollback |
| ContextCache | TTL-based caching with content-hash keys |
