"""Unit tests for the ContextBudget."""

from __future__ import annotations

import pytest
from workflow_orchestrator.intelligence.context_budget import (
    ContextBudget,
    ContextBudgetConfig,
)
from workflow_orchestrator.intelligence.models import ArtifactReference


class TestContextBudget:
    def setup_method(self) -> None:
        self.budget = ContextBudget(total_budget=1000)

    def test_assemble_within_budget(self) -> None:
        bundle = self.budget.assemble(
            immutable_core="Short core",
            working_set=[ArtifactReference(name="file.py")],
            rolling_summary="Short summary",
            recent_history=[{"role": "user", "content": "hi"}],
        )
        assert bundle.budget_remaining > 0
        assert bundle.immutable_core == "Short core"

    def test_assemble_exceeds_budget_triggers_compression(self) -> None:
        budget = ContextBudget(total_budget=100)
        long_content = "A" * 1000
        bundle = budget.assemble(
            immutable_core="Core",
            rolling_summary=long_content,
        )
        # Rolling summary should have been compressed/truncated
        assert len(bundle.rolling_summary) < len(long_content)

    def test_immutable_core_never_summarized(self) -> None:
        budget = ContextBudget(total_budget=10)
        bundle = budget.assemble(
            immutable_core="Short",
            rolling_summary="A" * 100,  # Long but lower priority
        )
        assert bundle.immutable_core == "Short"  # Kept intact

    def test_working_set_truncated_by_config(self) -> None:
        config = ContextBudgetConfig(max_artifact_refs=2)
        budget = ContextBudget(config=config)
        artifacts = [ArtifactReference(name=f"file{i}.py") for i in range(10)]
        bundle = budget.assemble(working_set=artifacts)
        assert len(bundle.working_set) == 2

    def test_set_total_budget(self) -> None:
        self.budget.set_total_budget(5000)
        assert self.budget.config.total_budget == 5000

    def test_set_total_budget_minimum(self) -> None:
        self.budget.set_total_budget(0)
        assert self.budget.config.total_budget == 100  # Minimum

    def test_register_summarizer(self) -> None:
        calls = []

        def my_summarizer(text: str, max_chars: int) -> str:
            calls.append((text, max_chars))
            return text[:max_chars]

        self.budget.register_summarizer("rolling_summary", my_summarizer)
        self.budget.assemble(rolling_summary="Hello World")
        assert len(calls) == 0  # Didn't exceed budget

        # Test with content that exceeds budget
        budget = ContextBudget(total_budget=50)
        budget.register_summarizer("rolling_summary", my_summarizer)
        budget.assemble(rolling_summary="A" * 200)
        assert len(calls) == 1

    def test_set_compression_ratio(self) -> None:
        self.budget.set_compression_ratio("rolling_summary", 0.3)
        assert self.budget.config.compression_ratios["rolling_summary"] == 0.3

    def test_get_allocation(self) -> None:
        self.budget.assemble(immutable_core="Core")
        alloc = self.budget.get_allocation("immutable_core")
        assert alloc is not None
        assert alloc.layer_name == "immutable_core"
        assert alloc.used == len("Core")

    def test_get_allocation_no_assembly(self) -> None:
        assert self.budget.get_allocation("nonexistent") is None

    def test_get_report(self) -> None:
        self.budget.assemble(immutable_core="Core", rolling_summary="Summary")
        report = self.budget.get_report()
        assert report["total_budget"] == 1000
        assert "immutable_core" in report["layers"]
        assert "rolling_summary" in report["layers"]
        assert report["remaining"] >= 0
