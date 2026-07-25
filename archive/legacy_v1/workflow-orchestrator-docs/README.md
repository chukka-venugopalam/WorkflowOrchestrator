# Workflow Orchestrator — Engineering Documentation

This is the frozen architecture RFC for Workflow Orchestrator, an AI Workflow Operating System that coordinates AI providers, coding agents, developer tools, and deployment services to automate software engineering. The orchestrator itself performs no reasoning and generates no code — it only plans, routes, verifies, and ships.

## Reading Order

**Start here:** `00_VISION.md` → `01_PRODUCT.md` → `02_ARCHITECTURE.md` → `03_SYSTEM_OVERVIEW.md`

**Core Engine:** `04_WORKFLOW_ENGINE.md`, `09_STATE_ENGINE.md`, `14_EXECUTION_ENGINE.md`, `31_DECISION_ENGINE.md`

**Intelligence Plane Integration:** `05_PROVIDER_SYSTEM.md`, `06_AGENT_SYSTEM.md`, `07_CAPABILITY_REGISTRY.md`, `08_CONTEXT_ENGINE.md`

**Project & Contract:** `10_PROJECT_CONTRACT.md`, `18_PROJECT_SCANNER.md`

**Extensibility:** `11_PLUGIN_SYSTEM.md`, `12_CONFIGURATION_SYSTEM.md`, `28_EXTENSION_GUIDE.md`

**Workflow Definition:** `13_WORKFLOW_SPECIFICATION.md`

**Delivery Pipeline:** `15_REPORT_ENGINE.md`, `16_ARTIFACT_MANAGER.md`, `17_EVENT_BUS.md`, `19_DEPLOYMENT_ENGINE.md`, `20_VERIFICATION_ENGINE.md`, `21_ERROR_RECOVERY.md`, `22_RESUME_ENGINE.md`

**Product Surface:** `23_CLI_DESIGN.md`, `24_CONFIGURATION_WIZARD.md`

**Reference:** `25_DATA_MODELS.md`, `26_FOLDER_STRUCTURE.md`, `27_API_SPECIFICATION.md`, `30_GLOSSARY.md`

**Ecosystem:** `32_SUPPORTING_SYSTEMS.md`

**Planning:** `29_ROADMAP.md`, `33_ARCHITECTURE_REVIEW.md`

## Document Index

| # | Document | Special |
|---|---|---|
| 00 | Vision | |
| 01 | Product | |
| 02 | Architecture | |
| 03 | System Overview | |
| 04 | Workflow Engine | |
| 05 | Provider System | |
| 06 | Agent System | |
| 07 | Capability Registry | ⭐ |
| 08 | Context Engine | ⭐ |
| 09 | State Engine | ⭐ |
| 10 | Project Contract | ⭐ |
| 11 | Plugin System | |
| 12 | Configuration System | |
| 13 | Workflow Specification | |
| 14 | Execution Engine | ⭐ |
| 15 | Report Engine | |
| 16 | Artifact Manager | |
| 17 | Event Bus | |
| 18 | Project Scanner | |
| 19 | Deployment Engine | |
| 20 | Verification Engine | |
| 21 | Error Recovery | |
| 22 | Resume Engine | |
| 23 | CLI Design | |
| 24 | Configuration Wizard | |
| 25 | Data Models | |
| 26 | Folder Structure | |
| 27 | API Specification | |
| 28 | Extension Guide | |
| 29 | Roadmap | |
| 30 | Glossary | |
| 31 | Decision Engine | added |
| 32 | Supporting Systems | added |
| 33 | Architecture Review | added |

⭐ = designated "special document" in the original brief, given exceptional detail.
"added" = identified as missing from the original structure during critical review; see `33_ARCHITECTURE_REVIEW.md`.

## Architecture Freeze Docs (v3.0.0)

In addition to the RFC documents above, the following contain the **frozen architecture**:

| Document | Description |
|---|---|
| `docs/ARCHITECTURE_FREEZE.md` | Official frozen architecture v3.0.0 — supersedes `02_ARCHITECTURE.md` |
| `docs/ARCHITECTURE_AUDIT.md` | Complete audit of all 33 RFCs against the codebase |
| `docs/IMPLEMENTATION_ROADMAP.md` | Phased, file-level implementation plan superseding `29_ROADMAP.md` |

**Reading Order (v3):** `00_VISION.md` → `01_PRODUCT.md` → `docs/ARCHITECTURE_FREEZE.md` → `docs/IMPLEMENTATION_ROADMAP.md` → individual component docs (03–33) as needed.
