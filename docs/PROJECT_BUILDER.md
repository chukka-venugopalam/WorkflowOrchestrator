# Autonomous Project Builder

The Autonomous Project Builder is the highest-level deterministic orchestrator in the Workflow Orchestrator. It transforms a simple natural-language idea into a complete executable project with architecture, workflows, tasks, documentation, and deployment plans.

## Architecture

The Project Builder follows a **pipeline architecture** where each component transforms the output of the previous component:

```
User Idea
    │
    ▼
┌─────────────────────────────┐
│     ProjectInitializer      │  Creates project, workspace, contract, session
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│     ProjectClassifier       │  Classifies project type (Web, Mobile, AI, etc.)
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│    RequirementExtractor     │  Transforms idea into structured requirements
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│   ArchitectureGenerator     │  Creates architecture specification
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│     RoadmapGenerator        │  Creates implementation phases and milestones
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│    TaskGraphBuilder         │  Produces a DAG of tasks
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│    WorkflowGenerator        │  Converts task graph to executable YAML workflows
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│   ProviderAssignment        │  Assigns providers, agents, transports via Decision Engine
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│    ExecutionPlanner         │  Creates execution batches (parallel/sequential)
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│    Execution & Verification │  Executes tasks, verifies results
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│  DocumentationGenerator     │  Auto-generates README, CHANGELOG, etc.
└─────────────────────────────┘
    │
    ▼
┌─────────────────────────────┐
│   DeploymentPlanner         │  Creates deployment plan
└─────────────────────────────┘
    │
    ▼
       Complete Project
```

### Supporting Systems

The pipeline is supported by cross-cutting systems:

- **StateManager**: Tracks project state, phase transitions, task history
- **ProgressTracker**: Tracks metrics (tasks completed, failures, retries, duration)
- **DependencyGraph**: Manages task dependencies, cycle detection, impact analysis
- **RollbackManager**: Creates checkpoints, supports rollback and version recovery
- **ResumeManager**: Supports resume after crash, shutdown, or restart
- **ArtifactValidator**: Validates artifact completeness, integrity, and hashes
- **CompletionChecker**: Determines task/phase/project completion status
- **VerificationManager**: Runs tests, lint, typecheck, contract, and artifact validation

## Lifecycle

The builder follows a strict lifecycle with the following phases:

| # | Phase | Description |
|---|-------|-------------|
| 1 | initializing | Create project, workspace, contract, session |
| 2 | classifying | Classify project type (Web, Mobile, AI, etc.) |
| 3 | requirements | Extract structured requirements |
| 4 | architecture | Generate architecture specification |
| 5 | planning | Generate implementation roadmap |
| 6 | task_creation | Build task dependency graph |
| 7 | workflow_generation | Convert tasks to YAML workflows |
| 8 | provider_assignment | Assign providers/agents/transports |
| 9 | execution_planning | Plan execution batches |
| 10 | executing | Execute tasks |
| 11 | verifying | Verify task/phase/project completion |
| 12 | documenting | Generate documentation |
| 13 | deploying | Generate deployment plan |
| 14 | completed | Project complete |
| - | failed | Project failed |

### Error Recovery

If any phase fails:
1. The project status is set to `failed`
2. A `builder.failed` event is published with error details
3. The project can be resumed from the last checkpoint via `ResumeManager`
4. The `RollbackManager` can restore any previous checkpoint

## Usage Examples

### Basic Usage

```python
from workflow_orchestrator.builder import ProjectBuilder

builder = ProjectBuilder()
result = builder.build("Build a Food Delivery Platform")
print(f"Project ID: {result['project_id']}")
print(f"Status: {result['status']}")
print(f"Type: {result['project_type']}")
```

### With Configuration

```python
from workflow_orchestrator.builder import ProjectBuilder, ProjectBuilderConfig
from workflow_orchestrator.builder.data_models import BuilderConfig

config = ProjectBuilderConfig(
    builder=BuilderConfig(
        max_concurrent_tasks=5,
        auto_verify=True,
    ),
    generate_docs=True,
    generate_deployment=True,
)
builder = ProjectBuilder(config=config)
result = builder.build("Build an AI Interview Platform")
```

### Resume After Crash

```python
builder = ProjectBuilder()

# Detect if a project can be resumed
context = builder.detect_resume()
if context["can_resume"]:
    print(f"Resuming from phase: {context['last_phase']}")
    result = builder.resume()
else:
    result = builder.build("Build a Hospital Management System")
```

### Checkpoints and Rollback

```python
# Create a manual checkpoint
checkpoint = builder.create_checkpoint(
    checkpoint_type="manual",
    description="Before major refactor",
)

# List all checkpoints
checkpoints = builder.list_checkpoints()

# Rollback to a checkpoint
result = builder.rollback(checkpoint.checkpoint_id)
```

## State Transitions

```
INITIALIZING → CLASSIFYING → REQUIREMENTS → ARCHITECTURE → PLANNING →
TASK_CREATION → WORKFLOW_GENERATION → PROVIDER_ASSIGNMENT →
EXECUTION_PLANNING → EXECUTING → VERIFYING → DOCUMENTING →
DEPLOYING → COMPLETED

Any phase → FAILED (on error)
FAILED → Any phase (via resume/rollback)
```

## Event Flow

The builder publishes the following events through the EventBus:

| Event | Source | When |
|-------|--------|------|
| `builder.started` | project_builder | Build process started |
| `builder.initialized` | project_initializer | Project initialized |
| `builder.contract_created` | project_initializer | Contract created |
| `builder.plan_created` | project_builder | Implementation plan created |
| `builder.workflow_generated` | workflow_generator | Workflow YAML files generated |
| `builder.execution_started` | project_builder | Task execution started |
| `builder.phase_completed` | state_manager | Phase completed |
| `builder.phase_transition` | state_manager | Phase transition occurred |
| `builder.verification_complete` | verification_manager | Verification completed |
| `builder.documentation_updated` | documentation_generator | Documentation generated |
| `builder.project_completed` | project_builder | Project completed successfully |
| `builder.failed` | project_builder | Project failed |
| `builder.resumed` | resume_manager | Project resumed from checkpoint |
| `builder.checkpoint_created` | rollback_manager | Checkpoint created |
| `builder.rolled_back` | rollback_manager | Rollback performed |

## Integration Points

The Project Builder integrates with all existing subsystems:

| Subsystem | Integration Point |
|-----------|-------------------|
| **Kernel** | Registered as `builder` service via BootstrapSequence |
| **EventBus** | Publishes builder events through `_publish_event()` |
| **ServiceRegistry** | All dependencies injected via constructor |
| **DecisionEngine** | ProviderAssignment uses DecisionEngine for routing |
| **ExecutionEngine** | _execute_task dispatches through execution engine |
| **WorkflowEngine** | Generated YAML workflows run through WorkflowEngine |
| **StateEngine** | Phase transitions recorded via StateManager |
| **ContextEngine** | Context assembled for provider execution |
| **KnowledgeSystem** | Knowledge base queried for relevant context |
| **ProjectContract** | Contract created by ProjectInitializer |
| **ProviderRuntime** | Provider execution routed through ProviderRuntime |
| **AgentRuntime** | Agent execution routed through AgentRuntime |
| **TransportRuntime** | Transports selected based on provider/agent |
| **SessionRuntime** | Sessions created for each project |
| **PromptRuntime** | Prompts built for provider execution |
| **ArtifactRuntime** | Artifacts stored and validated |
| **ProjectMemory** | Project state persisted via .state/ directory |
| **CapabilityRegistry** | Capabilities matched for task requirements |
| **WorkspaceManager** | Workspace provisioned for project |

## Developer Guide

### Adding a New Component

1. Create the component file in `workflow_orchestrator/builder/`
2. Follow the pattern: class with constructor accepting optional dependencies
3. Integrate with EventBus via `_publish_event()`
4. Add the component to `ProjectBuilder.__init__()`
5. Store component state as instance variables (no global state)
6. Add comprehensive tests in `tests/unit/builder/`

### Code Conventions

- All classes use `from __future__ import annotations`
- All public methods have type hints and docstrings
- No provider-specific logic (no hardcoded Claude/ChatGPT names)
- No global mutable state
- Dependency injection via constructor parameters
- Events published for observability

### Testing

Tests are in `workflow_orchestrator/tests/unit/builder/`. Run with:

```bash
pytest workflow_orchestrator/tests/unit/builder/ -v
```

All tests use real imports (no mocks required for unit tests) except for
the verification manager and provider assignment tests which use simple
mocks that don't require external dependencies.

## Package Structure

```
workflow_orchestrator/builder/
    __init__.py              # Package exports
    data_models.py           # Shared data models (dataclasses, enums)
    project_builder.py       # Main orchestrator
    project_initializer.py   # Creates projects, workspaces, contracts
    project_classifier.py    # Classifies project type
    requirement_extractor.py # Extracts structured requirements
    architecture_generator.py # Generates architecture specs
    roadmap_generator.py     # Creates implementation roadmaps
    task_graph_builder.py    # Builds task DAGs
    workflow_generator.py    # Generates YAML workflows
    provider_assignment.py   # Assigns providers/agents/transports
    execution_planner.py     # Plans execution batches
    verification_manager.py  # Verifies tasks/phases/projects
    artifact_validator.py    # Validates artifacts
    completion_checker.py    # Checks completion status
    deployment_planner.py    # Creates deployment plans
    documentation_generator.py # Generates documentation files
    state_manager.py         # Tracks project state
    resume_manager.py        # Handles resume after interruptions
    rollback_manager.py      # Manages checkpoints and rollback
    progress_tracker.py      # Tracks progress metrics
    dependency_graph.py      # Manages task dependency graph
```
