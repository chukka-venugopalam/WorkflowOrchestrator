"""Tests for ArtifactValidator."""

from __future__ import annotations

from workflow_orchestrator.builder.artifact_validator import ArtifactValidator


class TestArtifactValidator:
    """Tests for ArtifactValidator."""

    def setup_method(self) -> None:
        self.validator = ArtifactValidator()

    def test_check_outputs_files(self) -> None:
        results = self.validator.check_outputs({"files": {"main.py": "content"}})
        assert len(results) == 1
        assert results[0].artifact_name == "main.py"
        assert results[0].exists

    def test_check_outputs_empty(self) -> None:
        results = self.validator.check_outputs({})
        assert len(results) >= 1

    def test_check_outputs_none(self) -> None:
        results = self.validator.check_outputs({"files": {}})
        assert len(results) >= 1

    def test_integrity_check(self) -> None:
        valid = self.validator.check_artifact_integrity("test.txt", "content")
        assert valid  # No known hash, should pass

    def test_register_and_check_hash(self) -> None:
        self.validator.register_expected_hash("test.txt", "original")
        valid = self.validator.check_artifact_integrity("test.txt", "original")
        assert valid

    def test_register_and_check_hash_mismatch(self) -> None:
        self.validator.register_expected_hash("test.txt", "original")
        valid = self.validator.check_artifact_integrity("test.txt", "modified")
        assert not valid

    def test_check_outputs_multiple(self) -> None:
        results = self.validator.check_outputs({
            "files": {"main.py": "code", "utils.py": "helpers"},
        })
        assert len(results) == 2

    def test_check_outputs_integrity(self) -> None:
        results = self.validator.check_outputs({"files": {"a.txt": "hello"}})
        for r in results:
            assert r.integrity_pass

    def test_generic_artifact(self) -> None:
        results = self.validator.check_outputs({"output": "some result"})
        assert len(results) > 0
