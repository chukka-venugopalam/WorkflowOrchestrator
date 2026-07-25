# Workflow Orchestrator — Disaster Recovery Guide

## 1. Deterministic State & Log Replay
The Workflow Orchestrator maintains write-ahead transaction logs (`transitions.json` and `snapshot.json`) under the state storage path.

To replay and reconstruct any execution run:
```python
from workflow_orchestrator.orchestrator import Orchestrator

orch = Orchestrator.get_instance()
# Replay workflow state from exact transition history
replay_report = orch.replay_workflow("run_id_12345")

if replay_report.success:
    print(f"Workflow reconstructed cleanly across {replay_report.replayed_steps} steps")
```

## 2. Checkpoint Rollback
```python
from workflow_orchestrator.builder.project_builder import ProjectBuilder

builder = ProjectBuilder()
# Rollback project to last verified checkpoint
builder.rollback_checkpoint(checkpoint_id="chk_004")
```
