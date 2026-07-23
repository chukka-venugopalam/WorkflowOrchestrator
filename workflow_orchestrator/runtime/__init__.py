"""Runtime Layer — transforms the orchestration framework into a working system.

This package contains the runtime implementations that coordinate
providers, agents, transports, sessions, prompts, artifacts, and
project memory into a cohesive execution system.

Packages:
    provider_runtime: Provider lifecycle and execution management
    agent_runtime: Agent lifecycle and task execution management
    transport_runtime: Transport lifecycle and communication management
    session_runtime: Persistent session management with pause/resume/restore
    prompt_runtime: Template rendering, context injection, prompt versioning
    artifact_runtime: Provider/agent output storage with provenance tracking
    project_memory: ``.state/`` directory management for persistent project memory
"""

from __future__ import annotations

from workflow_orchestrator.runtime.provider_runtime import ProviderRuntime
from workflow_orchestrator.runtime.agent_runtime import AgentRuntime
from workflow_orchestrator.runtime.transport_runtime import TransportRuntime
from workflow_orchestrator.runtime.session_runtime import SessionRuntime
from workflow_orchestrator.runtime.prompt_runtime import PromptRuntime
from workflow_orchestrator.runtime.artifact_runtime import ArtifactRuntime
from workflow_orchestrator.runtime.project_memory import ProjectMemory

__all__ = [
    "ProviderRuntime",
    "AgentRuntime",
    "TransportRuntime",
    "SessionRuntime",
    "PromptRuntime",
    "ArtifactRuntime",
    "ProjectMemory",
]
