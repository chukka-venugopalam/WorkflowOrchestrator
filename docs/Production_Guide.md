# Workflow Orchestrator — Production Deployment & Administration Guide

## 1. Overview
The Workflow Orchestrator AI Operating System is a production-grade autonomous software engineering framework designed to coordinate LLM providers, developer CLI agents, dynamic Model Context Protocol (MCP) tools, and deterministic workflow engines.

## 2. Booting the Orchestrator
```python
from workflow_orchestrator.orchestrator import Orchestrator

# Initialize the master orchestrator instance
orch = Orchestrator.get_instance()

# Boot all 30 core subsystems
boot_report = orch.boot(show_dashboard=True)

if boot_report.success:
    print(f"Workflow Orchestrator initialized successfully in {boot_report.boot_time_ms:.2f} ms")
```

## 3. High Availability & Security Configuration
- Enforce the **Approval Gate Engine** for file deletions, force git pushes, secret mutations, and out-of-workspace commands.
- Secure environment secrets using `EncryptedCredentialVault`.
- Enable secret redaction across log outputs via `SecretRedactor`.
