# Workflow Orchestrator — Plugin Engine SDK

## Creating a Custom Plugin
Plugins are discovered dynamically via `manifest.json`.

### Example manifest.json
```json
{
  "name": "custom-linter",
  "version": "1.0.0",
  "entrypoint": "plugin.py",
  "dependencies": ["python>=3.10"]
}
```

### Implementing BasePlugin
```python
from workflow_orchestrator.orchestrator.plugin_engine import BasePlugin

class CustomLinterPlugin(BasePlugin):
    def initialize(self) -> None:
        print("Custom Linter Plugin Loaded!")
        
    def execute(self, config: dict) -> dict:
        return {"status": "success", "linted_files": 12}
```
