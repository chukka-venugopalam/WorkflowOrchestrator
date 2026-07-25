# Workflow Orchestrator — Production Deployment Guide

## Containerized Deployment (Docker)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY workflow_orchestrator/ ./workflow_orchestrator/
CMD ["python", "-m", "workflow_orchestrator.cli"]
```

## Environment Variables
- `ANTHROPIC_API_KEY`: Anthropic Claude API Key
- `OPENAI_API_KEY`: OpenAI ChatGPT API Key
- `GEMINI_API_KEY`: Google Gemini API Key
- `OPENROUTER_API_KEY`: OpenRouter Gateway Key
- `OLLAMA_BASE_URL`: Ollama Local Daemon Endpoint (Default: `http://localhost:11434`)
- `AZURE_OPENAI_ENDPOINT`: Azure OpenAI Service Endpoint
- `AZURE_OPENAI_KEY`: Azure OpenAI API Key
