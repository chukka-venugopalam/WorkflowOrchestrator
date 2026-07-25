# Workflow Orchestrator — Architecture Reference

## 1. Frozen 30 Subsystem Layering Diagram

```
+-----------------------------------------------------------------------------------+
|                            Master Orchestrator Facade                             |
+-----------------------------------------------------------------------------------+
|  Builder Layer      | ProjectInitializer, Classifier, Requirements, Architecture |
|  Intelligence Layer | Decision Engine, Context Engine, Knowledge Base, Rules    |
|  Contract Layer     | ProjectContract, ContractManager, ContractValidator        |
|  Runtime Layer      | WorkflowCompiler, ExecutionEngine, WorkflowReplay         |
|  Integrations Layer | ProviderManager, AgentManager, McpManager, Telemetry      |
|  Core Layer         | Kernel, Service Registry, Event Bus, State Engine          |
+-----------------------------------------------------------------------------------+
```

## 2. Structural Guarantees
- No parallel registries or duplicate state stores.
- Strict Dependency Injection via `Kernel` and `ServiceRegistry`.
- Event-driven communication via `EventBus` pub-sub pattern.
