# Project Contract System

## Overview

The Project Contract is an immutable, versioned specification that captures all project intent: vision, requirements, architecture, standards, constraints, milestones, and acceptance criteria.

## Lifecycle

```
DRAFT → FINALIZED → SUPERSEDED → ARCHIVED
         (human gate)
```

- **DRAFT**: Active development, mutable
- **FINALIZED**: Immutable, used by execution engine
- **SUPERSEDED**: Replaced by a newer version
- **ARCHIVED**: Historical record

## Contract Schema

| Field | Description | Required |
|---|---|---|
| Vision | Project vision statement | ✅ |
| Requirements | List of functional/non-functional requirements | ✅ (≥1) |
| Architecture | Architecture description | ❌ |
| Folder Structure | Project structure description | ❌ |
| Coding Standards | Code style/quality standards | ❌ |
| Tech Stack | Framework, language, deployment, etc. | ✅ |
| Constraints | Project constraints (must have ≥1 for finalization) | ❌ |
| Milestones | Project milestones with criteria | ❌ |
| Acceptance Criteria | Verification criteria | ✅ (≥1) |
| Style Conventions | Coding style rules | ❌ |
| Human Decisions | Recorded human decisions | ❌ |

## Key Components

| Component | Description |
|---|---|
| ProjectContract | Immutable contract model with version, status, data |
| ContractManager | Lifecycle management: create, finalize, version |
| ContractValidator | Schema and data validation |
| ContractHistory | Immutable event history (creation, finalization, versions) |
| ContractDiffer | Version-to-version comparison |
| ContractRules | Finalization/versioning/archival rule evaluation |
| ContractSnapshot | Frozen contract snapshots at version points |

## Versioning

Contracts are immutable per version. Changes produce `@vN+1`:
- `v1.0.0` → finalize → `v2.0.0`
- Human approval required for finalization
- Changelog required for versioning
