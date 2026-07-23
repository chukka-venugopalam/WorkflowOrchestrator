"""Domain services — Layer 2 of the Workflow Orchestrator.

This package will contain domain services such as:
- Context Engine: Context assembly, summarization, rendering
- Project Contract: Contract versioning, validation
- Verification Engine: Criteria execution, verdict aggregation
- Report Engine: Multi-format report generation
- Project Scanner: Existing project analysis
- Deployment Engine: Deploy/rollback/smoke-check abstraction
- Error Recovery: Error classification, recovery strategies
- Resume Engine: Run reconstruction, checkpoint management

These are NOT implemented yet. This package is a placeholder
for Phase 1+ implementation.
"""

from __future__ import annotations

__version__ = "3.0.0"
