"""Tests for builder data models."""

from __future__ import annotations

from workflow_orchestrator.builder.data_models import (
    ArtifactCheckResult,
    BuilderConfig,
    CheckpointRecord,
    CompletionStatus,
    DeploymentPlan,
    DocumentationSet,
    ExecutionBatch,
    PhaseState,
    ProgressSnapshot,
    ProjectState,
    ResourceAssignment,
    RollbackResult,
    TaskEdge,
    TaskGraph,
    TaskNode,
    TaskPriority,
    TaskStatus,
    ProjectType,
    ProjectPhase,
    VerificationScope,
    CheckpointType,
    RollbackScope,
    VerificationResult,
)


class TestEnums:
    """Tests for builder enums."""

    def test_project_type_values(self) -> None:
        assert ProjectType.WEB.value == "web"
        assert ProjectType.MOBILE.value == "mobile"
        assert ProjectType.DESKTOP.value == "desktop"
        assert ProjectType.CLI.value == "cli"
        assert ProjectType.AI.value == "ai"
        assert ProjectType.ML.value == "ml"
        assert ProjectType.EMBEDDED.value == "embedded"
        assert ProjectType.ROBOTICS.value == "robotics"
        assert ProjectType.UNKNOWN.value == "unknown"
        assert len(set(t.value for t in ProjectType)) == len(list(ProjectType))

    def test_task_priority_values(self) -> None:
        assert TaskPriority.CRITICAL.value == "critical"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.LOW.value == "low"

    def test_task_status_values(self) -> None:
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.SKIPPED.value == "skipped"


class TestTaskNode:
    """Tests for TaskNode."""

    def test_create_default(self) -> None:
        node = TaskNode(task_id="task_001", name="Test Task")
        assert node.task_id == "task_001"
        assert node.name == "Test Task"
        assert node.priority == TaskPriority.MEDIUM
        assert node.status == TaskStatus.PENDING
        assert node.dependencies == []
        assert node.capabilities_required == []

    def test_create_with_all_fields(self) -> None:
        node = TaskNode(
            task_id="task_001",
            name="Test Task",
            description="A test task",
            phase="foundation",
            priority=TaskPriority.HIGH,
            status=TaskStatus.READY,
            dependencies=["task_000"],
            capabilities_required=["codegen.python"],
            expected_outputs=["file1.py"],
            acceptance_criteria=["criterion 1"],
            retry_policy={"max_retries": 3},
        )
        assert len(node.dependencies) == 1
        assert node.priority == TaskPriority.HIGH
        assert node.status == TaskStatus.READY

    def test_to_dict_and_back(self) -> None:
        original = TaskNode(
            task_id="task_001",
            name="Test",
            description="Desc",
            phase="phase1",
            priority=TaskPriority.HIGH,
            status=TaskStatus.COMPLETED,
            dependencies=["dep1"],
        )
        data = original.to_dict()
        restored = TaskNode.from_dict(data)
        assert restored.task_id == original.task_id
        assert restored.name == original.name
        assert restored.priority == original.priority
        assert restored.status == original.status
        assert restored.dependencies == original.dependencies

    def test_from_dict_defaults(self) -> None:
        restored = TaskNode.from_dict({})
        assert restored.task_id == ""
        assert restored.priority == TaskPriority.MEDIUM
        assert restored.status == TaskStatus.PENDING


class TestTaskEdge:
    """Tests for TaskEdge."""

    def test_create(self) -> None:
        edge = TaskEdge(from_task_id="task_001", to_task_id="task_002")
        assert edge.from_task_id == "task_001"
        assert edge.to_task_id == "task_002"
        assert edge.type == "dependency"


class TestTaskGraph:
    """Tests for TaskGraph."""

    def test_empty_graph(self) -> None:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        assert graph.nodes == {}
        assert graph.edges == []
        assert graph.entry_tasks == []
        assert graph.terminal_tasks == []

    def test_with_nodes(self) -> None:
        graph = TaskGraph(graph_id="g1", project_id="p1")
        node1 = TaskNode(task_id="task_001", name="Task 1")
        node2 = TaskNode(task_id="task_002", name="Task 2", dependencies=["task_001"])
        graph.nodes["task_001"] = node1
        graph.nodes["task_002"] = node2
        assert len(graph.nodes) == 2
        assert graph.nodes["task_001"].name == "Task 1"

    def test_phases(self) -> None:
        graph = TaskGraph(project_id="p1")
        graph.phases = ["foundation", "features", "testing"]
        assert len(graph.phases) == 3


class TestProjectState:
    """Tests for ProjectState."""

    def test_create_default(self) -> None:
        state = ProjectState()
        assert state.status == "initializing"
        assert state.phases == {}

    def test_create_with_values(self) -> None:
        state = ProjectState(
            project_id="p1",
            project_name="Test Project",
            project_type="web",
            status="running",
            current_phase="executing",
        )
        assert state.project_id == "p1"
        assert state.project_name == "Test Project"

    def test_phases(self) -> None:
        state = ProjectState(project_id="p1")
        state.phases["planning"] = PhaseState(phase="planning", status="running")
        state.phases["executing"] = PhaseState(phase="executing", status="pending")
        assert len(state.phases) == 2
        assert state.phases["planning"].status == "running"


class TestPhaseState:
    """Tests for PhaseState."""

    def test_create(self) -> None:
        ps = PhaseState(phase="foundation", status="completed")
        assert ps.phase == "foundation"
        assert ps.status == "completed"
        assert ps.completed_tasks == []
        assert ps.failed_tasks == []

    def test_tasks(self) -> None:
        ps = PhaseState(phase="test")
        ps.completed_tasks.append("task_001")
        ps.failed_tasks.append("task_002")
        assert len(ps.completed_tasks) == 1
        assert len(ps.failed_tasks) == 1


class TestBuilderConfig:
    """Tests for BuilderConfig."""

    def test_defaults(self) -> None:
        config = BuilderConfig()
        assert config.max_concurrent_tasks == 3
        assert config.auto_verify is True
        assert config.checkpoint_frequency == 5

    def test_custom(self) -> None:
        config = BuilderConfig(
            project_root="/projects",
            max_concurrent_tasks=5,
            auto_verify=False,
        )
        assert config.project_root == "/projects"
        assert config.max_concurrent_tasks == 5
        assert config.auto_verify is False


class TestExecutionBatch:
    """Tests for ExecutionBatch."""

    def test_create(self) -> None:
        batch = ExecutionBatch(batch_id="b1", tasks=["t1", "t2"])
        assert batch.batch_id == "b1"
        assert len(batch.tasks) == 2
        assert batch.mode == "parallel"

    def test_sequential(self) -> None:
        batch = ExecutionBatch(batch_id="b2", tasks=["t1"], mode="sequential")
        assert batch.mode == "sequential"


class TestResourceAssignment:
    """Tests for ResourceAssignment."""

    def test_defaults(self) -> None:
        ra = ResourceAssignment(task_id="t1")
        assert ra.task_id == "t1"
        assert ra.provider_id == ""
        assert ra.transport == "rest_api"
        assert ra.confidence == 0.0

    def test_assigned(self) -> None:
        ra = ResourceAssignment(
            task_id="t1",
            provider_id="anthropic.claude",
            agent_id="claude-code",
            confidence=0.95,
        )
        assert ra.provider_id == "anthropic.claude"
        assert ra.agent_id == "claude-code"


class TestVerificationResult:
    """Tests for VerificationResult."""

    def test_defaults(self) -> None:
        vr = VerificationResult()
        assert vr.passed is False
        assert vr.tests_pass is True
        assert vr.issues == []

    def test_all_pass(self) -> None:
        vr = VerificationResult(scope="task", target_id="t1", passed=True)
        assert vr.scope == "task"
        assert vr.target_id == "t1"


class TestArtifactCheckResult:
    """Tests for ArtifactCheckResult."""

    def test_defaults(self) -> None:
        acr = ArtifactCheckResult(artifact_name="main.py")
        assert acr.artifact_name == "main.py"
        assert acr.exists is False

    def test_valid(self) -> None:
        acr = ArtifactCheckResult(
            artifact_name="main.py",
            exists=True,
            complete=True,
            integrity_pass=True,
        )
        assert acr.complete


class TestCompletionStatus:
    """Tests for CompletionStatus."""

    def test_defaults(self) -> None:
        cs = CompletionStatus()
        assert cs.is_complete is False
        assert cs.completion_percentage == 0.0
        assert cs.can_proceed is True

    def test_complete(self) -> None:
        cs = CompletionStatus(scope="task", target_id="t1", is_complete=True, completion_percentage=100.0)
        assert cs.is_complete


class TestDeploymentPlan:
    """Tests for DeploymentPlan."""

    def test_defaults(self) -> None:
        dp = DeploymentPlan()
        assert dp.hosting_platform == ""
        assert dp.secrets == []

    def test_with_data(self) -> None:
        dp = DeploymentPlan(
            plan_id="dp1",
            project_id="p1",
            hosting_platform="Vercel",
            secrets=["API_KEY", "DB_PASSWORD"],
        )
        assert dp.hosting_platform == "Vercel"
        assert len(dp.secrets) == 2


class TestDocumentationSet:
    """Tests for DocumentationSet."""

    def test_defaults(self) -> None:
        ds = DocumentationSet()
        assert ds.readme == ""
        assert ds.changelog == ""
        assert ds.additional == {}

    def test_with_content(self) -> None:
        ds = DocumentationSet(project_id="p1", readme="# Project", changelog="# Changelog")
        assert "# Project" in ds.readme
        assert ds.project_id == "p1"


class TestProgressSnapshot:
    """Tests for ProgressSnapshot."""

    def test_defaults(self) -> None:
        ps = ProgressSnapshot()
        assert ps.completed_tasks == 0
        assert ps.failed_tasks == 0
        assert ps.duration_seconds == 0.0

    def test_with_data(self) -> None:
        ps = ProgressSnapshot(
            completed_tasks=5,
            failed_tasks=1,
            total_tasks=10,
            duration_seconds=120.5,
        )
        assert ps.completed_tasks == 5
        assert ps.contract_completion == 0.0


class TestCheckpointRecord:
    """Tests for CheckpointRecord."""

    def test_defaults(self) -> None:
        cr = CheckpointRecord()
        assert cr.checkpoint_type == "automatic"

    def test_with_data(self) -> None:
        cr = CheckpointRecord(
            checkpoint_id="cp1",
            checkpoint_type="phase",
            phase="executing",
        )
        assert cr.checkpoint_id == "cp1"


class TestRollbackResult:
    """Tests for RollbackResult."""

    def test_defaults(self) -> None:
        rr = RollbackResult()
        assert rr.success is False
        assert rr.issues == []

    def test_failed(self) -> None:
        rr = RollbackResult(
            rollback_id="r1",
            success=False,
            issues=["Checkpoint not found"],
        )
        assert not rr.success
        assert len(rr.issues) == 1
