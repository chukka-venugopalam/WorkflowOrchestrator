# Workflow Orchestrator — Provider & Agent SDK Reference

## 1. Provider SDK (`BaseProvider`)
Implement `BaseProvider` to add new custom LLM model adapters:
```python
from workflow_orchestrator.providers.base_provider import BaseProvider
from workflow_orchestrator.intelligence.models import ExecutionRequest, ProviderResponse

class CustomLLMProvider(BaseProvider):
    async def _execute_impl(self, request: ExecutionRequest) -> ProviderResponse:
        return ProviderResponse(content="Generated response", tokens_used=150, model="custom-llm")
```

## 2. Agent SDK (`BaseAgent`)
Implement `BaseAgent` for custom developer agents:
```python
from workflow_orchestrator.agents.base.base_agent import BaseAgent
from workflow_orchestrator.agents.base.models import AgentResponse

class CustomDevAgent(BaseAgent):
    async def _execute_impl(self, task: dict) -> AgentResponse:
        return AgentResponse(success=True, output="Executed task successfully")
```
