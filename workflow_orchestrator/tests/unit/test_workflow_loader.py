"""Unit tests for WorkflowLoader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from workflow_orchestrator.execution.workflow_loader import WorkflowLoader


class TestWorkflowLoader:
    """Tests for the WorkflowLoader."""

    def setup_method(self) -> None:
        self.loader = WorkflowLoader()

    def test_load_yaml_string(self) -> None:
        """Test loading a workflow from a YAML string."""
        yaml_content = """
name: Test Workflow
description: A test workflow
steps:
  - terminal:
      command: echo hello
  - terminal:
      command: echo world
"""
        workflow = self.loader.loads(yaml_content, format="yaml")
        assert workflow.name == "Test Workflow"
        assert len(workflow.steps) == 2
        assert workflow.steps[0].plugin == "terminal"

    def test_load_json_string(self) -> None:
        """Test loading a workflow from a JSON string."""
        json_content = json.dumps({
            "name": "JSON Workflow",
            "description": "From JSON",
            "steps": [
                {"terminal": {"command": "echo test"}},
            ],
        })
        workflow = self.loader.loads(json_content, format="json")
        assert workflow.name == "JSON Workflow"
        assert len(workflow.steps) == 1

    def test_load_yaml_file(self, tmp_path: Path) -> None:
        """Test loading a workflow from a YAML file."""
        yaml_file = tmp_path / "test_workflow.yaml"
        yaml_file.write_text(yaml.dump({
            "name": "File Workflow",
            "steps": [
                {"terminal": {"command": "ls"}},
            ],
        }))

        workflow = self.loader.load(yaml_file)
        assert workflow.name == "File Workflow"
        assert len(workflow.steps) == 1

    def test_load_json_file(self, tmp_path: Path) -> None:
        """Test loading a workflow from a JSON file."""
        json_file = tmp_path / "test_workflow.json"
        json_file.write_text(json.dumps({
            "name": "JSON File Workflow",
            "steps": [
                {"terminal": {"command": "npm test"}},
            ],
        }))

        workflow = self.loader.load(json_file)
        assert workflow.name == "JSON File Workflow"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].plugin == "terminal"

    def test_load_nonexistent_file(self) -> None:
        """Test loading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            self.loader.load("/nonexistent/workflow.yaml")

    def test_unsupported_format(self) -> None:
        """Test that unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported"):
            self.loader.loads("test", format="toml")

    def test_supported_formats(self) -> None:
        """Test that supported formats are listed."""
        formats = self.loader.supported_formats()
        assert ".yaml" in formats
        assert ".json" in formats

    def test_register_custom_handler(self) -> None:
        """Test registering a custom format handler."""
        def mock_handler(path: Path) -> object:
            from workflow_orchestrator.models import WorkflowDefinition
            return WorkflowDefinition(name="custom", steps=[])

        self.loader.register_handler(".toml", mock_handler)
        assert ".toml" in self.loader.supported_formats()

    def test_empty_content_raises(self) -> None:
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="Empty"):
            self.loader.loads("", format="yaml")

    def test_loads_yaml_with_tags(self) -> None:
        """Test loading YAML with tags and schedule."""
        yaml_content = """
name: Scheduled Workflow
tags: [daily, maintenance]
schedule:
  cron: "0 6 * * *"
steps:
  - terminal:
      command: cleanup
"""
        workflow = self.loader.loads(yaml_content, format="yaml")
        assert workflow.tags == ["daily", "maintenance"]
        assert workflow.schedule is not None
        assert workflow.schedule["cron"] == "0 6 * * *"
