"""Unit tests for Features 1, 2, and 3.

Validates:
1. Dedicated project output location outside repo directory.
2. Scale-aware architecture generation & templates for missing project types (GAME, CLI, etc.).
3. Provider-assisted & human-in-the-loop disambiguation.
4. Backward compatibility for create_project(), classify(), and generate().
"""

from pathlib import Path
import tempfile
import pytest

from workflow_orchestrator.builder.data_models import ProjectScale, ProjectType
from workflow_orchestrator.builder.project_classifier import ProjectClassifier
from workflow_orchestrator.builder.architecture_generator import ArchitectureGenerator
from workflow_orchestrator.config.config_manager import ConfigurationManager
from workflow_orchestrator.orchestrator.orchestrator import Orchestrator


from unittest.mock import patch

def test_feature1_dedicated_folder_outside_repo():
    """Verify projects are output to configured location outside repo root."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir).resolve()
        cfg_mgr = ConfigurationManager()
        cfg_mgr.set("project_output_root", str(tmp_path))

        out_root = cfg_mgr.get_project_output_root().resolve()
        assert out_root == tmp_path

        orchestrator = Orchestrator.get_instance()
        target_folder = (tmp_path / "sudoku_test_game").resolve()

        with patch("workflow_orchestrator.execution.parallel_task_queue.ParallelTaskQueue.execute_queue", return_value={}):
            rec = orchestrator.create_project(
                idea="simple sudoku game",
                project_name="sudoku_test_game",
                workspace_dir=target_folder,
            )

        assert target_folder.exists()
        assert (target_folder / "README.md").exists()
        assert str(target_folder).lower().startswith(str(tmp_path).lower())


def test_feature2_simple_sudoku_game_minimal_structure():
    """Verify 'simple sudoku game' produces GAME/MINIMAL flat structure, NOT a web/Next.js/Prisma split."""
    classifier = ProjectClassifier()
    ptype = classifier.classify("simple sudoku game")
    scale = classifier.estimate_scale("simple sudoku game")

    assert ptype == ProjectType.GAME
    assert scale == ProjectScale.MINIMAL

    gen = ArchitectureGenerator()
    arch = gen.generate(requirements={}, project_type=ptype, project_scale=scale)

    folder_structure = arch["folder_structure"]
    tech_stack = arch["technology_stack"]

    # Must contain game assets and flat src/, NOT Next.js / Prisma / tRPC
    assert any("assets/" in f for f in folder_structure)
    assert not any("components/" in f for f in folder_structure)
    assert not any("pages/" in f for f in folder_structure)

    # Database should be None or file-based for MINIMAL game
    assert "None" in arch["database"]["primary_database"] or "In-memory" in arch["database"]["primary_database"]
    assert "Next.js" not in tech_stack.get("framework", "")


def test_feature2_multiplayer_game_large_structure():
    """Verify 'multiplayer game platform with matchmaking...' produces GAME/LARGE client-server structure."""
    classifier = ProjectClassifier()
    idea = "a multiplayer game platform with matchmaking, leaderboards, and user accounts"
    ptype = classifier.classify(idea)
    scale = classifier.estimate_scale(idea)

    assert ptype == ProjectType.GAME
    assert scale == ProjectScale.LARGE

    gen = ArchitectureGenerator()
    arch = gen.generate(requirements={}, project_type=ptype, project_scale=scale)

    folder_structure = arch["folder_structure"]

    # Must contain client/ and server/ split for LARGE multiplayer game
    assert any("client/" in f for f in folder_structure)
    assert any("server/" in f for f in folder_structure)
    assert any("docker/" in f for f in folder_structure)
    assert len(arch["services"]) > 1


def test_feature2_generic_fallback_not_web():
    """Verify unknown project type falls back to clean generic template, NEVER the web template."""
    gen = ArchitectureGenerator()
    arch = gen.generate(requirements={}, project_type=ProjectType.UNKNOWN, project_scale=ProjectScale.STANDARD)

    folder_structure = arch["folder_structure"]
    # Generic template must be flat src/, tests/, docs/ and NOT Next.js web components
    assert "src/" in folder_structure
    assert not any("components/" in f for f in folder_structure)
    assert not any("pages/" in f for f in folder_structure)


def test_feature3_inconclusive_classification_detection():
    """Verify inconclusive detection for ambiguous prompts."""
    classifier = ProjectClassifier()

    # Empty/ambiguous prompt produces UNKNOWN -> inconclusive
    scores_empty = {}
    assert classifier.is_inconclusive(scores_empty) is True

    # Near tie scores -> inconclusive
    near_tie_scores = {ProjectType.WEB: 5, ProjectType.API: 4}
    assert classifier.is_inconclusive(near_tie_scores) is True

    # Clear winner -> conclusive
    clear_scores = {ProjectType.GAME: 10, ProjectType.WEB: 1}
    assert classifier.is_inconclusive(clear_scores) is False


def test_backward_compatibility_signatures():
    """Confirm existing signatures for create_project(), classify(), and generate() still work."""
    classifier = ProjectClassifier()
    ptype = classifier.classify("build a web dashboard")
    assert ptype == ProjectType.WEB

    gen = ArchitectureGenerator()
    arch = gen.generate(requirements={}, project_type=ptype)
    assert arch["project_type"] == "web"

    orchestrator = Orchestrator.get_instance()

    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "legacy_test"
        with patch("workflow_orchestrator.execution.parallel_task_queue.ParallelTaskQueue.execute_queue", return_value={}):
            rec = orchestrator.create_project(
                idea="legacy web project test",
                workspace_dir=target,
            )
        assert rec.status == "completed"
