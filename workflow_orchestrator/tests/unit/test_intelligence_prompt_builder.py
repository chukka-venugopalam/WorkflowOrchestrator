"""Unit tests for the PromptBuilder."""

from __future__ import annotations

from workflow_orchestrator.intelligence.prompt_builder import PromptBuilder
from workflow_orchestrator.intelligence.models import (
    ArtifactReference,
    ContextBundle,
    Prompt,
)


class TestPromptBuilder:
    def setup_method(self) -> None:
        self.builder = PromptBuilder()

    def test_build_minimal(self) -> None:
        prompt = self.builder.build(goal="Build a login page")
        assert prompt.goal == "Build a login page"
        assert prompt.context == ""
        assert prompt.constraints == []
        assert prompt.artifacts == []

    def test_build_full(self) -> None:
        prompt = self.builder.build(
            goal="Build a login page",
            context="Project uses Next.js",
            artifacts=[ArtifactReference(name="design.png", content_type="image/png")],
            constraints=["Use TypeScript", "Add tests"],
            history=[{"role": "user", "content": "Hello"}],
            budget={"remaining": 4000},
        )
        assert prompt.goal == "Build a login page"
        assert len(prompt.artifacts) == 1
        assert len(prompt.constraints) == 2
        assert len(prompt.history) == 1
        assert prompt.budget["remaining"] == 4000

    def test_build_trims_whitespace(self) -> None:
        prompt = self.builder.build(goal="  Build a page  ", context="  Some context  ")
        assert prompt.goal == "Build a page"
        assert prompt.context == "Some context"

    def test_build_from_bundle(self) -> None:
        bundle = ContextBundle(
            immutable_core="Project: Build a landing page",
            working_set=[ArtifactReference(name="page.tsx", content_type="typescript")],
            rolling_summary="Completed design phase",
            recent_history=[{"role": "user", "content": "Review page"}],
            budget_remaining=5000,
        )
        prompt = self.builder.build_from_bundle(
            bundle,
            goal="Finish the landing page",
            constraints=["Use Tailwind CSS"],
        )
        assert prompt.goal == "Finish the landing page"
        assert "Project: Build a landing page" in prompt.context
        assert "Completed design phase" in prompt.context
        assert len(prompt.constraints) == 1
        assert prompt.budget["remaining"] == 5000

    def test_render_plain_text(self) -> None:
        prompt = self.builder.build(
            goal="Build a page",
            context="Use React",
            constraints=["TypeScript"],
        )
        text = self.builder.render_plain_text(prompt)
        assert "# Goal" in text
        assert "Build a page" in text
        assert "# Constraints" in text
        assert "TypeScript" in text
        assert "# Context" in text
        assert "Use React" in text

    def test_render_structurally(self) -> None:
        prompt = self.builder.build(
            goal="Build a page",
            context="Use React",
            artifacts=[ArtifactReference(name="file.tsx", content_type="typescript")],
        )
        structured = self.builder.render_structurally(prompt)
        assert structured["objective"] == "Build a page"
        assert len(structured["artifacts"]) == 1
        assert structured["artifacts"][0]["name"] == "file.tsx"
        assert structured["budget"]["remaining"] == 0

    def test_max_artifact_limit(self) -> None:
        builder = PromptBuilder(max_artifact_summaries=2)
        artifacts = [
            ArtifactReference(name=f"file{i}.txt") for i in range(10)
        ]
        prompt = builder.build(goal="Test", artifacts=artifacts)
        assert len(prompt.artifacts) == 2

    def test_max_artifact_setter(self) -> None:
        assert self.builder.max_artifact_summaries == 5
        self.builder.max_artifact_summaries = 10
        assert self.builder.max_artifact_summaries == 10
