# Decision Engine

## Overview

The Decision Engine determines **WHAT should happen next** in a workflow execution. It is entirely **rule-based and deterministic** — it never performs AI reasoning, never knows provider names, and only reasons using capabilities, project state, execution results, and configuration.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DecisionEngine                            │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ GoalAnalyzer  │  │ PhaseManager │  │ DecisionRules    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                     │            │
│         ▼                 ▼                     ▼            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ProviderSelect│  │ AgentSelect  │  │WorkflowSelect    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                     │            │
│         └─────────────────┴─────────────────────┘            │
│                              │                              │
│                              ▼                              │
│                    ┌──────────────────┐                     │
│                    │  RoutingPolicy   │                     │
│                    └────────┬─────────┘                     │
│                             │                               │
│                             ▼                               │
│                    ExecutionDecision                        │
└─────────────────────────────────────────────────────────────┘
```

## Decision Flow

### Primary Flow: `decide_next_step()`

```
1. Build DecisionContext (from execution state, project state, registries)
2. Analyze goal → required capabilities (GoalAnalyzer)
3. Determine project phase (PhaseManager)
4. Select provider (ProviderSelector)
5. Select agent (AgentSelector)
6. Select workflow (WorkflowSelector)
7. Apply routing policy (RoutingPolicy)
8. Evaluate decision rules (DecisionRules)
9. Return ExecutionDecision
```

### Error Recovery Flow: `decide_recovery()`

```
1. Receive error details (type, message, severity)
2. Update DecisionContext with error
3. Evaluate recovery rules → retry, fallback, escalate, or halt
4. Return ExecutionDecision with recovery action
```

### Workflow Selection Flow: `decide_workflow()`

```
1. Analyze goal → capabilities
2. Match capabilities to workflow definitions
3. Score by: phase compatibility, keyword match, tag overlap, capability overlap
4. Return best workflow or "not found"
```

## Core Components

### DecisionEngine
| Method | Purpose |
|---|---|
| `decide_next_step()` | Primary: determines what to do next |
| `decide_recovery()` | Error recovery planning |
| `decide_workflow()` | Workflow selection |

### GoalAnalyzer
- Maps user goals to required capabilities via keyword matching
- Extracts constraints from goal text
- Infers capabilities from project phase
- Returns priority-scored capability list

### PhaseManager
- Determines project phase from goals, execution state, and capabilities
- Supports phase transitions: Discovery → Planning → Coding → Verification → Deployment → Maintenance
- Keyword-based scoring against phase patterns

### ProviderSelector
- Selects best provider from context
- Scores by capability coverage, cost, quality, latency
- Applies routing policy preferences

### AgentSelector
- Selects best agent from context
- Considers capability coverage, provider compatibility, runtime requirements

### WorkflowSelector
- Matches goals to available workflow definitions
- Scores by phase compatibility, keyword overlap, tag matching, capability overlap
- Supports custom workflow registration

### DecisionRules
- Rule-based evaluation engine
- 7 built-in rules evaluated in priority order:
  1. Error Recovery (priority 10)
  2. Route Execution (priority 20)
  3. Select Capabilities (priority 30)
  4. Handle Fallback (priority 40)
  5. Trigger Approval (priority 50)
  6. Skip Step (priority 60)
  7. Complete or Halt (priority 100)
- Custom rules can be registered

### RoutingPolicy
- Configurable routing policies
- Built-in: `default`, `cost-optimized`, `quality-optimized`, `fast`, `safe`
- Controls: cost/quality tradeoff, preferred providers/agents, approval thresholds, fallback behavior

## Data Flow

```
Goal ("build and deploy the landing page")
    │
    ▼
GoalAnalyzer.analyze()
    │  └─→ codegen.frontend, codegen.nextjs, deploy.vercel, verify.test
    ▼
PhaseManager.determine_phase()
    │  └─→ Phase.CODING
    ▼
DecisionContext { phase=coding, capabilities=[...], providers=[...], ... }
    │
    ▼
ProviderSelector.select() ──→ ProviderSelection { provider_id, confidence, ... }
    │
    ▼
AgentSelector.select() ────→ AgentSelection { agent_id, confidence, ... }
    │
    ▼
WorkflowSelector.select() ──→ WorkflowSelection { name, source, ... }
    │
    ▼
RoutingPolicy.apply() ─────→ Approval requirements, fallback settings
    │
    ▼
DecisionRules.evaluate() ──→ Decision type (route_execution, recover_error, halt, ...)
    │
    ▼
ExecutionDecision { decision_type, selected_provider, selected_agent, ... }
```

## Integration Points

### Capability Registry
- ProviderSelector queries capability coverage from context metadata
- GoalAnalyzer maps goal keywords to capability IDs
- PhaseManager infers capabilities from phase

### Intelligence Layer
- ProviderSelector uses RoutingPolicy (same scoring model as CapabilityMatcher)
- AgentSelector uses the same capability-based matching approach

### Execution Layer
- ExecutionEngine calls DecisionEngine.decide_next_step() to determine routing
- ExecutionEngine calls DecisionEngine.decide_recovery() on errors
- DecisionEngine returns ExecutionDecision with selected provider/agent

### Kernel Bootstrap
- DecisionEngine can be registered as a service via ServiceRegistry
- Components (GoalAnalyzer, PhaseManager, Selectors) can be overridden via DI

## Models

| Model | Description |
|---|---|
| `ExecutionDecision` | Complete decision with provider, agent, workflow, and approval info |
| `DecisionContext` | All contextual information for making a decision |
| `DecisionRule` | Immutable rule with ID, name, condition, and action |
| `RuleEvaluationResult` | Result of evaluating a rule |
| `ProviderSelection` | Selected provider with confidence and reasoning |
| `AgentSelection` | Selected agent with confidence and reasoning |
| `WorkflowSelection` | Selected workflow with confidence and reasoning |
| `RecoveryAction` | Action to recover from an error |
| `RoutingPolicyConfig` | Configuration for routing policies |

## Enums

| Enum | Values |
|---|---|
| `DecisionType` | select_provider, select_agent, select_workflow, select_capability, route_execution, handle_fallback, trigger_approval, recover_error, skip_step, halt |
| `ProjectPhase` | discovery, planning, coding, verification, deployment, maintenance, unknown |
| `ApprovalRequirement` | not_required, recommended, required, urgent |
| `Priority` | low, normal, high, critical |

## Providers Package

```
workflow_orchestrator/providers/
├── __init__.py        # ProviderConfig, ProviderLoader
├── manifest.py        # ProviderManifest re-exports
├── provider_config.py # ProviderConfig re-export
└── provider_loader.py # ProviderLoader re-export
```

### ProviderConfig
- Configuration for provider adapters
- Supports loading from dicts, env vars, config files
- Provider-agnostic base with metadata for provider-specific settings

### ProviderLoader
- Loads provider configurations
- Stub for future dynamic adapter loading

## Transports Package

```
workflow_orchestrator/transports/
├── __init__.py        # Transport interface exports
├── transport.py       # Abstract Transport base class
├── api_transport.py   # REST API transport interface
├── browser_transport.py  # Browser automation transport interface
├── desktop_transport.py  # Desktop automation transport interface
├── cli_transport.py   # CLI execution transport interface
├── mcp_transport.py   # Model Context Protocol transport interface
└── ssh_transport.py   # SSH communication transport interface
```

All transports are **interface-only** — no implementations. They define the contract for future adapter development.

### TransportRequest
- url, method, headers, body, timeout

### TransportResponse
- status_code, headers, body, duration_ms, success, error

### TransportError
- message, status_code, transport_type, recoverable, retryable
