# Workflow Orchestrator — Developer & API Guide

## 1. Quickstart: Building a Project from Prompt
```python
from workflow_orchestrator.builder.project_builder import ProjectBuilder, ProjectBuilderConfig, BuilderConfig
from pathlib import Path

# Configure builder workspace
config = ProjectBuilderConfig(builder=BuilderConfig(project_root=Path("./my_new_app")))
builder = ProjectBuilder(config=config)

# Autonomously build application
result = builder.build(
    idea="Build a FastAPI web app with PostgreSQL database and Docker deployment",
    project_name="MyFastAPIApp"
)

print(f"Project built successfully with {len(result.generated_files)} files!")
```

## 2. Decision & Context Routing
- **Decision Engine**: Resolves requirements into imperative steps using fuzzy goal matching and provider quality scores.
- **Context Engine**: Assembles project contract, workflow state, history, knowledge nodes, and error traces into token-budgeted bundles.
