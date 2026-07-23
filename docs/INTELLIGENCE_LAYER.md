# Intelligence Layer — Workflow Orchestrator v3

> **Architecture Version:** 3.0.0
> **Phase:** 1 — Intelligence Plane Foundation
> **Status:** Complete

## Overview

The Intelligence Plane provides the provider-agnostic interfaces, registries, and routing foundations that allow the orchestrator to work with any AI provider or coding agent.

**Contains NO provider-specific implementations.**  
**Contains NO agent-specific implementations.**  
**Everything is capability-based.**

## Architecture

```
workflow_orchestrator/intelligence/
├── __init__.py              # Package exports
├── models.py                # All data models
├── provider.py              # Abstract IProvider interface
├── agent.py                 # Abstract IAgent interface
├── provider_registry.py     # Provider registry
├── agent_registry.py        # Agent registry
├── session.py               # Session manager
├── capability_matcher.py    # Capability-based matching
├── router.py                # Capability-to-provider/agent routing
├── prompt_builder.py        # Structured prompt assembly
├── context_budget.py        # Token-independent context budgeting
└── planner.py               # Plan skeleton
```

## Provider Interface

### IProvider (abstract)

All AI providers must implement this interface:

| Method | Description |
|---|---|
| `initialize()` | Establish connections, load credentials |
| `shutdown()` | Close connections, release resources |
| `manifest()` → `ProviderManifest` | Declare metadata, capabilities, limits |
| `capabilities()` → `list[Capability]` | Runtime capabilities offered |
| `health()` → `ProviderHealth` | Health check with latency, error rate |
| `submit(request)` → `ExecutionResult` | Submit task, wait for completion |
| `stream(request)` → `AsyncIterator` | Submit task, stream partial results |
| `cancel(task_id)` | Cancel in-flight task |
| `status(task_id)` → `ExecutionResult` | Check task status |
| `estimate_cost(request)` → `CostEstimate` | Estimate execution cost |
| `estimate_latency(request)` → `float` | Estimate execution latency |

### Provider Lifecycle

```
Registered → Initializing → Available ──→ InUse ──→ Available
                                │                        │
                                ├──→ Degraded ──→ Available
                                │         │
                                │         └──→ Unavailable → HealthChecking → Available
                                │                                          │
                                └──→ Deprecated ──→ [*]
```

### Provider Rules

1. Every provider must implement all methods of `IProvider`
2. Health checks run on startup and after N consecutive failures
3. Raw vendor errors are never passed to the core — adapted into typed error subtypes
4. Provider-specific features require opt-in "extension capabilities"

## Agent Interface

### IAgent (abstract)

All coding agents must implement this interface:

| Method | Description |
|---|---|
| `launch()` | Prepare agent for task execution |
| `shutdown()` | Stop agent, release resources |
| `execute(request)` → `ExecutionResult` | Execute a task |
| `cancel(task_id)` | Cancel a running task |
| `resume(task_id)` → `ExecutionResult` | Resume a paused task |
| `status(task_id)` → `ExecutionResult` | Check task status |
| `heartbeat(task_id)` → `AgentStatus` | Check if agent is alive |
| `manifest()` → `AgentManifest` | Declare metadata, capabilities |
| `supported_capabilities()` → `list[Capability]` | Capabilities this agent supports |

### Agent Rules

1. Agents are black boxes — only artifacts and results flow back
2. Each agent task receives a scoped workspace with explicit permissions
3. Two agents with overlapping write-scopes may never run in parallel
4. Agent outputs are normalized into `ExecutionResult` with diffs, logs, artifact refs

## Routing

### Router

The Router takes required capabilities as input and produces a routing decision:

```python
router = Router(capability_matcher)
decision = await router.route(["reasoning.code-review", "codegen.python"])
print(decision.selected_provider_id)  # "anthropic.claude"
print(decision.selected_agent_id)     # "claude-code"
```

**Algorithm:**
1. Match required capabilities to provider-agent pairs via `CapabilityMatcher`
2. Score candidates by coverage
3. Apply user preferences (preferred provider/agent)
4. Select the best candidate
5. Return `RoutingDecision` with reasoning and trace

**Fallback routing:**
```python
fallback = await router.route_fallback(original_decision, exclude_providers=["failed-provider"])
```

## Capability Matching

### CapabilityMatcher

Given required capabilities, returns ranked provider-agent candidates:

```python
matcher = CapabilityMatcher(provider_registry, agent_registry)
result = matcher.match(["codegen.nextjs", "reasoning.architecture"])
print(result.candidates[0].provider_id)  # Best match
```

**Matching algorithm:**
1. For each required capability, find providers that offer it
2. For each matching provider, find agents that support it
3. Score each provider-agent pair by coverage fraction
4. Return candidates sorted by score descending

**No provider names are hardcoded.** Everything is capability-based.

## Prompt Assembly

### PromptBuilder

Assembles structured prompts from components:

```python
builder = PromptBuilder()
prompt = builder.build(
    goal="Build a login page",
    context="Project uses Next.js with Tailwind",
    artifacts=[ArtifactReference(name="design.png")],
    constraints=["Use TypeScript"],
    history=[{"role": "user", "content": "..."}],
)
# Provider adapters format this into their own conventions
```

Output is a provider-agnostic `Prompt` object. Each provider adapter
is responsible for formatting it into its own request format.

## Context Budgeting

### ContextBudget

Manages context budgets without assuming a specific tokenization scheme:

```python
budget = ContextBudget(total_budget=8000)
bundle = budget.assemble(
    immutable_core="Project contract...",  # Never summarized
    working_set=[ArtifactReference(name="page.tsx")],
    rolling_summary="Completed design phase...",
    recent_history=[{"role": "user", "content": "..."}],
)
```

**Layers (highest to lowest priority):**
1. **Immutable Core** — Project contract summary (never summarized)
2. **Working Set** — File/artifact references from dependency steps
3. **Rolling Summary** — Compressed summary of prior step outputs
4. **Recent History** — Recent conversation history

When budget is exceeded, lower-priority layers are compressed or trimmed first.

## Session Management

### SessionManager

Tracks units of work across providers and agents:

```python
mgr = SessionManager()
session = mgr.create_session(project="my-app", workflow="build")
mgr.set_provider(session.session_id, "anthropic.claude")
mgr.set_agent(session.session_id, "claude-code")

task = mgr.record_task(session.session_id, task_id="t1", capability_id="codegen.nextjs")
mgr.update_task(session.session_id, "t1", status="completed", result=result)
mgr.complete_session(session.session_id)
```

Tracks: project, provider, agent, artifacts, workflow, task history,
execution history, timestamps, and state.

## Registries

### ProviderRegistry

```python
registry = ProviderRegistry()
registry.register(provider_instance)
provider = registry.lookup("anthropic.claude")
health = await registry.health("anthropic.claude")
providers = registry.find_by_capability("reasoning.code-review")
```

### AgentRegistry

```python
registry = AgentRegistry()
registry.register(agent_instance)
agent = registry.lookup("claude-code")
agents = registry.find_by_capability("codegen.nextjs")
```

## Data Models

All data models are in `models.py`:

| Model | Description |
|---|---|
| `Capability` | A namespaced capability identifier |
| `ProviderManifest` | Provider metadata and declared capabilities |
| `ProviderHealth` | Provider health status at a point in time |
| `CostEstimate` | Estimated cost of a provider invocation |
| `AgentManifest` | Agent metadata and declared capabilities |
| `ExecutionRequest` | A request to execute a task |
| `ExecutionResult` | Result of a provider or agent execution |
| `ArtifactReference` | Reference to an artifact |
| `Session` | A session tracking a unit of work |
| `TaskRecord` | Record of a single task execution |
| `Prompt` | A structured prompt for provider formatting |
| `ContextBundle` | Provider-agnostic intermediate context representation |
| `RoutingDecision` | Result of routing a capability requirement |
| `RoutingCandidate` | A candidate provider-agent pair |
| `BudgetAllocation` | Allocation of context budget across layers |
| `Plan` | A plan produced by the planner |

## Future Provider Adapters

To add a new provider:

1. Create a new package in `adapters/providers/{provider-name}/`
2. Implement `IProvider` interface
3. Register in `ProviderRegistry`
4. Declare capabilities in `ProviderManifest`

```python
class ClaudeProvider(IProvider):
    async def initialize(self) -> None: ...
    def manifest(self) -> ProviderManifest: ...
    async def health(self) -> ProviderHealth: ...
    async def submit(self, request: ExecutionRequest) -> ExecutionResult: ...
    # ... implement all methods

# Register
provider_registry.register(ClaudeProvider())
```

The provider will then be discovered by `CapabilityMatcher`, routable
by `Router`, and usable by the workflow engine — all through the
capability-based system, with no hardcoded references.

## Getting Started

```python
from workflow_orchestrator.intelligence import (
    IProvider, IAgent,
    ProviderRegistry, AgentRegistry,
    CapabilityMatcher, Router,
    PromptBuilder, ContextBudget,
    SessionManager,
)

# Setup registries
provider_registry = ProviderRegistry()
agent_registry = AgentRegistry()

# Setup matching and routing
matcher = CapabilityMatcher(provider_registry, agent_registry)
router = Router(matcher)

# Setup prompt assembly
builder = PromptBuilder()
budget = ContextBudget(total_budget=8000)

# Setup session management
sessions = SessionManager()
```

## Testing

```bash
cd workflow_orchestrator
pip install -e ".[dev]"
pytest tests/unit/ -v
```

Intelligence layer tests are in `tests/unit/` with prefix `test_intelligence_*`.
