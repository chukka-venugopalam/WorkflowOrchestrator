# Execution Engine

## Architecture

The Execution Plane is the deterministic core of the Workflow Orchestrator. It coordinates the execution of workflows without any knowledge of AI providers, agents, or external services. It communicates only through interfaces.

```
┌─────────────────────────────────────────────────────────────┐
│                    WorkflowEngine                            │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │  Loader  │  │ Validator│  │ Compiler │  │DependencyRes │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
│       └──────────────┴─────────────┴────────────────┘        │
│                              │                               │
│                     ExecutionGraph                           │
│                              │                               │
│                      ExecutionEngine                          │
│           ┌─────────────┬────┴────┬────────────────┐        │
│           │             │         │                │         │
│    StepExecutor   RetryEngine  EventBus      StateEngine    │
│           │                                                │
│      Plugin Registry                                       │
└─────────────────────────────────────────────────────────────┘
```

## Execution Lifecycle

### 1. Workflow Loading

Workflows are loaded from YAML or JSON files by the `WorkflowLoader`. The loader auto-detects format from file extension and supports custom format handlers.

**Supported formats:**
- `.yaml` / `.yml` — YAML format
- `.json` — JSON format
- Custom — via `register_handler()` extension point

### 2. Validation

The `WorkflowValidator` performs these checks:

| Check | Description |
|---|---|
| **Structure** | Required fields, valid types |
| **Dependencies** | Valid step references, no circular deps |
| **Variables** | Variable references resolve correctly |
| **References** | Step references are valid |
| **Capabilities** | Required capabilities are declared |

### 3. Compilation

The `WorkflowCompiler` transforms workflow definitions into an `ExecutionGraph`:

```
ExecutionGraph
├── nodes: dict[str, ExecutionNode]
│   ├── node_id: str (e.g., "step_1")
│   ├── plugin: str
│   ├── config: dict
│   ├── depends_on: list[str]
│   └── on_failure: str
├── edges: list[ExecutionEdge]
│   ├── from_node_id: str
│   ├── to_node_id: str
│   └── type: str
├── entry_nodes: list[str]
└── terminal_nodes: list[str]
```

### 4. Dependency Resolution

The `DependencyResolver` computes execution order using Kahn's algorithm for topological sort. It also:

- **Detects cycles** via DFS with color-marking
- **Identifies parallel candidates** — steps at the same level can run concurrently
- **Computes ready batches** — the next set of steps whose dependencies are satisfied
- **Detects conflicts** — steps writing to the same output

### 5. Execution

The `ExecutionEngine` executes steps via the `StepExecutor`:

1. **Dispatch** — Resolve the plugin for the step
2. **Execute** — Run the plugin with step config + context variables
3. **Track** — Record results in the ExecutionContext
4. **Publish** — Emit events to the EventBus (step.started, step.completed, step.failed)
5. **State** — Update the StateEngine with transitions and heartbeats
6. **Retry** — If failure occurs, evaluate retry policy

### 6. Completion

The `WorkflowEngine` finalizes:

- Mark run as `completed` or `failed`
- Emit workflow.completed event
- Record final state in StateEngine

## Workflow Lifecycle

```
    ┌──────────┐
    │ Pending  │
    └────┬─────┘
         │ run()
         ▼
    ┌──────────┐
    │ Running  │◄────────────────────┐
    └────┬─────┘                      │
         │ pause_run()                │ resume_run()
         ▼                            │
    ┌──────────┐                      │
    │ Paused   ├──────────────────────┘
    └────┬─────┘
         │ cancel_run()
         ▼
    ┌──────────┐
    │Cancelled │
    └──────────┘

    Running ──► Completed (all steps succeed)
    Running ──► Failed (step fails with on_failure=stop)
```

## Retry Model

The `RetryEngine` supports configurable retry policies per step:

| Parameter | Default | Description |
|---|---|---|
| `max_retries` | 3 | Maximum retry attempts |
| `delay` | 1.0s | Initial delay before first retry |
| `backoff` | 2.0x | Multiplier for exponential backoff |
| `max_delay` | 60.0s | Maximum delay cap |
| `retryable_errors` | None | Error classes to retry (None = all) |
| `abort_on` | None | Error classes to abort immediately |

**Error Classification:**

| Error Class | Detection | Action |
|---|---|---|
| `TRANSIENT` | Network, rate limit, connection errors | Retry |
| `TIMEOUT` | Timeout errors | Retry |
| `VERIFICATION_FAILURE` | Test/lint failures | Retry or escalate |
| `CONTRACT_VIOLATION` | Contract/constraint violations | Escalate (never retry) |
| `CAPABILITY_UNRESOLVED` | Unresolved capability | Escalate (never retry) |
| `PLUGIN_ERROR` | Plugin not found | Abort |
| `UNKNOWN` | Unrecognized errors | Retry |

**Retry Decisions:**
- `RETRY` — Wait with backoff, then retry
- `ABORT` — Stop execution immediately
- `ESCALATE` — Pass to higher level for decision
- `SKIP` — Skip this step and continue

## Dependency Graph

```
Workflow: Build and Deploy

step_1: checkout    ───┐
step_2: install         ├──► step_3: test ──► step_4: build ──► step_5: deploy
                        │                       │
                        └───────────────────────┘

ExecutionOrder:
  Level 0: [step_1, step_2]      (parallel)
  Level 1: [step_3]              (after step_1, step_2)
  Level 2: [step_4]              (after step_1, step_3)
  Level 3: [step_5]              (after step_4)
```

## Queue Model

The `ExecutionQueue` supports three queue modes:

| Mode | Description | Implementation |
|---|---|---|
| **FIFO** | First-in, first-out | Python list |
| **Priority** | Sorted by priority score | `heapq` |
| **Delayed** | Scheduled for future execution | List with promotion |

Delayed items are automatically promoted to the main queue when their execution time arrives.

## Compilation Pipeline

```
YAML/JSON
    │
    ▼
WorkflowDefinition
    │
    ▼
WorkflowValidator.validate()
    │
    ▼
WorkflowCompiler.compile()
    │
    ▼
ExecutionGraph
    │
    ▼
DependencyResolver.resolve()
    │
    ▼
ExecutionOrder (topologically sorted)
    │
    ▼
Execution Engine executes in order
```

## Future: Parallel Execution

The dependency resolver already identifies parallel candidates:

```python
order = resolver.resolve(graph)
for group in order.parallel_groups:
    # group = ["step_1", "step_2"]  # Can run in parallel
    execute_parallel(group)
```

Future implementation will use `concurrent.futures` or `asyncio` to execute parallel groups concurrently.

## Integration Points

### State Engine
- `execution_engine.start_run()` — Creates a run and transitions to `running`
- `execution_engine.complete_run()` — Transitions to `completed` or `failed`
- `execution_engine.update_run_state()` — Transitions to any valid state
- Heartbeats recorded during step execution

### Event Bus
Events published during execution:

| Event Type | When | Payload |
|---|---|---|
| `workflow.started` | Run started | run_id, workflow_name, node_count |
| `workflow.completed` | Run finished | run_id, status, duration, steps |
| `workflow.paused` | Run paused | run_id, workflow_name |
| `workflow.resumed` | Run resumed | run_id, workflow_name |
| `workflow.cancelled` | Run cancelled | run_id, workflow_name |
| `step.started` | Step execution begins | node_id, step_name, plugin |
| `step.completed` | Step succeeds | node_id, duration |
| `step.failed` | Step fails | node_id, error, duration |
| `step.retrying` | Step being retried | node_id, attempt, delay |

### Capability Registry
- Each step can declare required capabilities
- Steps reference capabilities that must be resolved before execution

### Artifact Manager
- Step outputs can be stored as artifacts
- Artifact references are tracked in the ExecutionContext
- Artifact Manager stores content-addressed blobs locally
