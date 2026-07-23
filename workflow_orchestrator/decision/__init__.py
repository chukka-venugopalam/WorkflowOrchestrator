"""Decision Engine — rule-based planning, selection, and routing.

The Decision Engine determines WHAT should happen next using only
deterministic rules. It never performs AI reasoning and never knows
provider names. All decisions are capability-based.

Contains NO provider-specific code.
Contains NO AI agent logic.

Structure:
    - ``decision_engine.py``: Main orchestrator for all decisions
    - ``decision_context.py``: Context assembly for decision making
    - ``decision_models.py``: All decision data models
    - ``decision_rules.py``: Rule-based evaluation engine
    - ``routing_policy.py``: Routing policies for provider/agent selection
    - ``provider_selector.py``: Provider selection from candidates
    - ``agent_selector.py``: Agent selection from candidates
    - ``workflow_selector.py``: Workflow selection based on goals
    - ``phase_manager.py``: Project phase determination
    - ``goal_analyzer.py``: Goal → capabilities mapping
"""

from __future__ import annotations

__all__ = [
    # Engine
    "DecisionEngine",
    # Context
    "DecisionContextBuilder",
    "DecisionContext",
    # Models
    "ExecutionDecision",
    "DecisionMetadata",
    "DecisionRule",
    "RuleEvaluationResult",
    "ProviderSelection",
    "AgentSelection",
    "WorkflowSelection",
    "RecoveryAction",
    "DecisionContext",
    "RoutingPolicyConfig",
    "ProjectPhase",
    "DecisionType",
    "ApprovalRequirement",
    "Priority",
    # Rules
    "DecisionRules",
    # Policy
    "RoutingPolicy",
    # Selectors
    "ProviderSelector",
    "AgentSelector",
    "WorkflowSelector",
    # Phase
    "PhaseManager",
    # Goal
    "GoalAnalyzer",
]

from workflow_orchestrator.decision.decision_engine import DecisionEngine
from workflow_orchestrator.decision.decision_context import DecisionContextBuilder
from workflow_orchestrator.decision.decision_models import (
    ExecutionDecision,
    DecisionMetadata,
    DecisionRule,
    RuleEvaluationResult,
    ProviderSelection,
    AgentSelection,
    WorkflowSelection,
    RecoveryAction,
    DecisionContext,
    RoutingPolicyConfig,
    ProjectPhase,
    DecisionType,
    ApprovalRequirement,
    Priority,
)
from workflow_orchestrator.decision.decision_rules import DecisionRules
from workflow_orchestrator.decision.routing_policy import RoutingPolicy
from workflow_orchestrator.decision.provider_selector import ProviderSelector
from workflow_orchestrator.decision.agent_selector import AgentSelector
from workflow_orchestrator.decision.workflow_selector import WorkflowSelector
from workflow_orchestrator.decision.phase_manager import PhaseManager
from workflow_orchestrator.decision.goal_analyzer import GoalAnalyzer
