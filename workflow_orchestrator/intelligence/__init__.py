"""Intelligence Plane — provider-agnostic interfaces for AI providers and agents.

This package contains the provider-agnostic interfaces, registries,
and routing foundations that allow the orchestrator to work with
any AI provider or coding agent.

Contains NO provider-specific implementations.
Contains NO agent-specific implementations.

Structure:
    - ``provider.py``: Abstract ``IProvider`` interface
    - ``agent.py``: Abstract ``IAgent`` interface
    - ``provider_registry.py``: Provider registry
    - ``agent_registry.py``: Agent registry
    - ``session.py``: Session manager
    - ``capability_matcher.py``: Capability-based matching
    - ``router.py``: Capability-to-provider/agent routing
    - ``prompt_builder.py``: Structured prompt assembly
    - ``context_budget.py``: Token-independent context budgeting
    - ``planner.py``: Plan skeleton
    - ``models.py``: All data models
"""

from __future__ import annotations

__all__ = [
    # Provider
    "IProvider",
    "ProviderRegistry",
    "ProviderManifest",
    "ProviderHealth",
    "ProviderStatus",
    "CostEstimate",
    # Agent
    "IAgent",
    "AgentRegistry",
    "AgentManifest",
    "AgentStatus",
    # Provider Registry
    "ProviderRegistry",
    # Agent Registry
    "AgentRegistry",
    # Session
    "SessionManager",
    "Session",
    "SessionState",
    "TaskRecord",
    # Capability Matcher
    "CapabilityMatcher",
    "MatchResult",
    # Router
    "Router",
    "RoutingDecision",
    "RoutingCandidate",
    # Prompt Builder
    "PromptBuilder",
    "Prompt",
    "ContextBundle",
    # Context Budget
    "ContextBudget",
    "ContextBudgetConfig",
    "BudgetAllocation",
    # Planner
    "Planner",
    "Plan",
    # Models
    "Capability",
    "ArtifactReference",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionErrorType",
    "ProviderManifest",
    "AgentManifest",
]

# Provider
from workflow_orchestrator.intelligence.provider import IProvider
from workflow_orchestrator.intelligence.provider_registry import ProviderRegistry

# Agent
from workflow_orchestrator.intelligence.agent import IAgent
from workflow_orchestrator.intelligence.agent_registry import AgentRegistry

# Session
from workflow_orchestrator.intelligence.session import SessionManager
from workflow_orchestrator.intelligence.models import Session, SessionState, TaskRecord

# Capability Matcher
from workflow_orchestrator.intelligence.capability_matcher import CapabilityMatcher, MatchResult

# Router
from workflow_orchestrator.intelligence.router import Router
from workflow_orchestrator.intelligence.models import RoutingDecision, RoutingCandidate

# Prompt Builder
from workflow_orchestrator.intelligence.prompt_builder import PromptBuilder
from workflow_orchestrator.intelligence.models import Prompt, ContextBundle

# Context Budget
from workflow_orchestrator.intelligence.context_budget import ContextBudget, ContextBudgetConfig
from workflow_orchestrator.intelligence.models import BudgetAllocation

# Planner
from workflow_orchestrator.intelligence.planner import Planner
from workflow_orchestrator.intelligence.models import Plan

# Models
from workflow_orchestrator.intelligence.models import (
    Capability,
    ArtifactReference,
    ExecutionRequest,
    ExecutionResult,
    ExecutionErrorType,
    ProviderManifest,
    AgentManifest,
    ProviderStatus,
    AgentStatus,
    CostEstimate,
    ProviderHealth,
)
