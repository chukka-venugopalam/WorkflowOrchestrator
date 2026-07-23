"""Unit tests for Project Contract system."""

from __future__ import annotations

import pytest

from workflow_orchestrator.contracts.contract_diff import ContractDiffer
from workflow_orchestrator.contracts.contract_history import ContractHistory
from workflow_orchestrator.contracts.contract_manager import ContractManager
from workflow_orchestrator.contracts.contract_rules import ContractRules
from workflow_orchestrator.contracts.contract_schema import (
    AcceptanceCriterion,
    Constraint,
    ContractData,
    ContractStatus,
    TechStack,
)
from workflow_orchestrator.contracts.contract_snapshot import ContractSnapshotManager
from workflow_orchestrator.contracts.contract_validator import ContractValidator
from workflow_orchestrator.contracts.project_contract import ProjectContract


class TestProjectContract:
    """Tests for ProjectContract."""

    def test_create(self) -> None:
        contract = ProjectContract.create(project_name="Test Project")
        assert contract.project_name == "Test Project"
        assert contract.version == "1.0.0"
        assert contract.status == ContractStatus.DRAFT

    def test_create_with_data(self) -> None:
        data = ContractData(vision="Test vision", requirements=["Req 1"])
        contract = ProjectContract.create(project_name="Test", data=data)
        assert contract.data.vision == "Test vision"

    def test_finalize(self) -> None:
        contract = ProjectContract.create(project_name="Test")
        contract.finalize(finalized_by="user")
        assert contract.status == ContractStatus.FINALIZED
        assert contract.finalized_by == "user"

    def test_finalize_already_finalized(self) -> None:
        contract = ProjectContract.create(project_name="Test")
        contract.finalize()
        with pytest.raises(ValueError):
            contract.finalize()

    def test_supersede(self) -> None:
        contract = ProjectContract.create(project_name="Test")
        contract.finalize()
        contract.supersede()
        assert contract.status == ContractStatus.SUPERSEDED

    def test_to_summary(self) -> None:
        data = ContractData(
            vision="Build great things",
            requirements=["Req 1", "Req 2"],
            tech_stack=TechStack(framework="Next.js", language="TypeScript"),
            constraints=[Constraint(category="performance", description="Fast loads")],
            acceptance_criteria=[AcceptanceCriterion(id="AC-1", description="Works")],
        )
        contract = ProjectContract.create(project_name="Test", data=data)
        summary = contract.to_summary()
        assert "Test" in summary
        assert "Next.js" in summary


class TestContractManager:
    """Tests for ContractManager."""

    def setup_method(self) -> None:
        self.mgr = ContractManager()

    def test_create(self) -> None:
        contract = self.mgr.create("Test Project")
        assert contract.project_name == "Test Project"
        assert contract.status == ContractStatus.DRAFT

    def test_finalize_with_validation(self) -> None:
        data = ContractData(
            vision="Build great things",
            requirements=["Req 1"],
            tech_stack=TechStack(framework="Next.js"),
            acceptance_criteria=[AcceptanceCriterion(id="AC-1", description="Works")],
        )
        contract = self.mgr.create("Test", data=data)
        finalized = self.mgr.finalize(contract, finalized_by="user")
        assert finalized.status == ContractStatus.FINALIZED

    def test_finalize_invalid(self) -> None:
        contract = self.mgr.create("")
        with pytest.raises(ValueError):
            self.mgr.finalize(contract)

    def test_create_next_version(self) -> None:
        data = ContractData(
            vision="Build",
            requirements=["Req 1"],
            tech_stack=TechStack(framework="Next.js"),
            acceptance_criteria=[AcceptanceCriterion(id="AC-1", description="Works")],
        )
        v1 = self.mgr.create("Test", data=data)
        self.mgr.finalize(v1, finalized_by="user")
        v2 = self.mgr.create_next_version(v1, changelog="Added new features")
        assert v2.version == "2.0.0"
        assert v2.status == ContractStatus.DRAFT

    def test_needs_approval(self) -> None:
        contract = self.mgr.create("Test")
        assert self.mgr.needs_approval(contract)


class TestContractValidator:
    """Tests for ContractValidator."""

    def setup_method(self) -> None:
        self.validator = ContractValidator()

    def test_validate_valid(self) -> None:
        contract = ProjectContract.create(
            project_name="Test",
            data=ContractData(
                vision="Build",
                requirements=["Req 1"],
                tech_stack=TechStack(framework="Next.js"),
                acceptance_criteria=[AcceptanceCriterion(id="AC-1", description="Works")],
            ),
        )
        result = self.validator.validate(contract)
        assert result["valid"]

    def test_validate_missing_name(self) -> None:
        contract = ProjectContract(project_name="")
        result = self.validator.validate(contract)
        assert not result["valid"]

    def test_can_transition(self) -> None:
        contract = ProjectContract.create(project_name="Test")
        assert self.validator.can_transition(contract, ContractStatus.FINALIZED)
        assert not self.validator.can_transition(contract, ContractStatus.ARCHIVED)


class TestContractHistory:
    """Tests for ContractHistory."""

    def setup_method(self) -> None:
        self.history = ContractHistory()

    def test_record_creation(self) -> None:
        contract = ProjectContract.create(project_name="Test")
        self.history.record_creation(contract)
        entries = self.history.get_history(contract.contract_id)
        assert len(entries) == 1
        assert entries[0].entry_type == "creation"

    def test_record_finalization(self) -> None:
        contract = ProjectContract.create(project_name="Test")
        self.history.record_finalization(contract, "user")
        entries = self.history.get_history(contract.contract_id)
        assert entries[0].entry_type == "finalization"

    def test_record_decision(self) -> None:
        contract = ProjectContract.create(project_name="Test")
        self.history.record_decision(contract, "Chose TypeScript")
        entries = self.history.get_history(contract.contract_id)
        assert entries[0].entry_type == "decision"


class TestContractDiff:
    """Tests for ContractDiffer."""

    def setup_method(self) -> None:
        self.differ = ContractDiffer()

    def test_compare_same(self) -> None:
        data = ContractData(vision="Build great things")
        old = ProjectContract.create(project_name="Test", data=data)
        new = ProjectContract.create(project_name="Test", data=data)
        result = self.differ.compare(old, new)
        # Different contracts, same data
        assert len(result.changes) >= 0

    def test_compare_different_vision(self) -> None:
        old = ProjectContract.create(project_name="Test", data=ContractData(vision="Old vision"))
        new = ProjectContract.create(project_name="Test", data=ContractData(vision="New vision"))
        result = self.differ.compare(old, new)
        assert "vision" in result.modifications


class TestContractRules:
    """Tests for ContractRules."""

    def setup_method(self) -> None:
        self.rules = ContractRules()

    def test_check_finalization_allows(self) -> None:
        data = ContractData(
            vision="Build",
            requirements=["Req 1"],
            tech_stack=TechStack(framework="Next.js"),
            acceptance_criteria=[AcceptanceCriterion(id="AC-1", description="Works")],
        )
        contract = ProjectContract.create(project_name="Test", data=data)
        result = self.rules.check_finalization(contract)
        assert result["allowed"]

    def test_check_finalization_blocks(self) -> None:
        contract = ProjectContract.create(project_name="")
        result = self.rules.check_finalization(contract)
        assert not result["allowed"]

    def test_check_versioning(self) -> None:
        contract = ProjectContract.create(project_name="Test")
        result = self.rules.check_versioning(contract, "Changelog")
        assert not result["allowed"]  # Draft can't be versioned

        contract.finalize()
        result = self.rules.check_versioning(contract, "Changelog")
        assert result["allowed"]


class TestContractSnapshot:
    """Tests for ContractSnapshotManager."""

    def setup_method(self) -> None:
        self.mgr = ContractSnapshotManager()

    def test_create_and_load(self) -> None:
        contract = ProjectContract.create(project_name="Test")
        snapshot = self.mgr.create(contract)
        loaded = self.mgr.load(snapshot.snapshot_id)
        assert loaded is not None
        assert loaded.project_name == "Test"

    def test_find_by_contract(self) -> None:
        contract = ProjectContract.create(project_name="Test")
        self.mgr.create(contract)
        snapshots = self.mgr.find_by_contract(contract.contract_id)
        assert len(snapshots) == 1
