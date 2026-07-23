"""Unit tests for Prompt Runtime."""

from __future__ import annotations

import pytest

from workflow_orchestrator.intelligence.models import ArtifactReference, Prompt


class TestPromptRuntime:
    """Tests for Prompt Runtime."""

    @pytest.fixture
    def prompt_runtime(self):
        """Create a prompt runtime."""
        from workflow_orchestrator.runtime import PromptRuntime
        return PromptRuntime()

    def test_render_goal_no_variables(self, prompt_runtime):
        """Test rendering a goal without variables."""
        result = prompt_runtime.render_goal("Build a login page")
        assert result == "Build a login page"

    def test_render_goal_with_variables(self, prompt_runtime):
        """Test rendering a goal with template variables."""
        result = prompt_runtime.render_goal(
            "Build a $project login page",
            variables={"project": "Next.js"},
        )
        assert result == "Build a Next.js login page"

    def test_build_prompt_basic(self, prompt_runtime):
        """Test building a basic prompt."""
        prompt = prompt_runtime.build_prompt(
            goal="Build a login page",
            constraints=["Use TypeScript"],
        )

        assert prompt.goal == "Build a login page"
        assert len(prompt.constraints) == 1
        assert prompt.constraints[0] == "Use TypeScript"

    def test_build_prompt_with_artifacts(self, prompt_runtime):
        """Test building a prompt with artifact references."""
        artifacts = [
            ArtifactReference(name="design.png", content_type="image/png"),
            ArtifactReference(name="api.ts", content_type="text/typescript"),
        ]

        prompt = prompt_runtime.build_prompt(
            goal="Implement the design",
            artifacts=artifacts,
        )

        assert len(prompt.artifacts) == 2
        assert prompt.artifacts[0].name == "design.png"

    def test_build_prompt_with_knowledge(self, prompt_runtime):
        """Test building a prompt with knowledge injection."""
        prompt = prompt_runtime.build_prompt(
            goal="Build a feature",
            knowledge="The project uses React 18 with TypeScript.",
        )

        assert "React 18" in prompt.context

    def test_build_prompt_with_contract(self, prompt_runtime):
        """Test building a prompt with contract injection."""
        prompt = prompt_runtime.build_prompt(
            goal="Build a feature",
            contract="Project Contract v1.0 - Build a web app",
        )

        assert "Project Contract" in prompt.context

    def test_build_prompt_with_history(self, prompt_runtime):
        """Test building a prompt with history."""
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        prompt = prompt_runtime.build_prompt(
            goal="Continue",
            history=history,
        )

        assert len(prompt.history) == 2

    def test_inject_context_from_dict(self, prompt_runtime):
        """Test injecting context from a dictionary."""
        prompt = Prompt(goal="Test")
        context_dict = {
            "context": "Additional context",
            "summary": "Progress summary",
        }

        updated = prompt_runtime.inject_context(prompt, context_dict)
        assert "Additional context" in updated.context
        assert "Progress summary" in updated.context

    def test_inject_knowledge(self, prompt_runtime):
        """Test injecting knowledge into a prompt."""
        prompt = Prompt(goal="Test")
        updated = prompt_runtime.inject_knowledge(prompt, "React knowledge", "React")

        assert "React" in updated.context
        # The label is "React", so "=== React ===" should be in the context
        assert "React" in updated.context
        assert "knowledge" in updated.context.lower()

    def test_inject_constraints(self, prompt_runtime):
        """Test injecting constraints."""
        prompt = Prompt(goal="Test")
        updated = prompt_runtime.inject_constraints(prompt, ["Use Python", "Use async"])

        assert len(updated.constraints) == 2

    def test_inject_artifacts(self, prompt_runtime):
        """Test injecting artifacts."""
        prompt = Prompt(goal="Test")
        artifacts = [
            ArtifactReference(name="file.py"),
            ArtifactReference(name="file.ts"),
        ]

        updated = prompt_runtime.inject_artifacts(prompt, artifacts)
        assert len(updated.artifacts) == 2

    def test_prompt_has_versioning(self, prompt_runtime):
        """Test that prompts have versioning metadata."""
        prompt = prompt_runtime.build_prompt(goal="Test")

        assert "prompt_version" in prompt.metadata
        assert "generated_at" in prompt.metadata


class TestPromptBuilder:
    """Tests for PromptBuilder."""

    @pytest.fixture
    def prompt_builder(self):
        """Create a prompt builder."""
        from workflow_orchestrator.intelligence.prompt_builder import PromptBuilder
        return PromptBuilder()

    def test_build_basic(self, prompt_builder):
        """Test building a basic prompt."""
        prompt = prompt_builder.build(goal="Test goal", context="Test context")
        assert prompt.goal == "Test goal"
        assert prompt.context == "Test context"

    def test_render_plain_text(self, prompt_builder):
        """Test rendering a prompt as plain text."""
        prompt = Prompt(goal="Test goal", constraints=["C1", "C2"])
        text = prompt_builder.render_plain_text(prompt)

        assert "Test goal" in text
        assert "C1" in text

    def test_render_structurally(self, prompt_builder):
        """Test rendering a prompt as a structured dict."""
        prompt = Prompt(goal="Test goal", constraints=["C1"])
        data = prompt_builder.render_structurally(prompt)

        assert data["objective"] == "Test goal"
        assert "C1" in data["constraints"]
