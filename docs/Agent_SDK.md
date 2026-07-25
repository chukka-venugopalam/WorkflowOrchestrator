# Workflow Orchestrator — Agent SDK Guide

## Creating a Developer Agent
Subclass `BaseAgent` and implement process isolation, command sandboxing, workspace creation, and execution hooks.

```python
from workflow_orchestrator.agents.base.base_agent import BaseAgent
from workflow_orchestrator.agents.base.models import AgentResponse, AgentCapabilities

class MyAgent(BaseAgent):
    def get_capabilities(self) -> AgentCapabilities:
        return AgentCapabilities(can_edit_code=True, can_run_terminal=True)
```
