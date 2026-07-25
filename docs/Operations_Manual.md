# Workflow Orchestrator — System Operations Manual

## 1. Monitoring & Telemetry
- **Telemetry Tracer**: Collects span execution times, dependency graphs, and resource usage.
- **Workflow Doctor**: Run diagnostics on demand via `orch.run_doctor()`.

## 2. Health Monitoring
- Automated periodic checks for provider availability, binary paths, workspace permissions, and disk space.
- Emits health change notifications over the `EventBus`.
