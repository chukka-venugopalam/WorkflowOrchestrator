# Integrations Architecture

## Overview

The Integrations package (`workflow_orchestrator/integrations/`) provides automatic discovery, configuration, and lifecycle management for all external components: providers, agents, browsers, desktop apps, CLI tools, MCP servers, and the runtime environment.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Integration Layer                     │
├─────────────────────────────────────────────────────┤
│  Discovery    │  Configuration  │  Lifecycle         │
│ ┌───────────┐ │ ┌─────────────┐ │ ┌───────────────┐  │
│ │Provider    │ │ │Provider     │ │ │Provider       │  │
│ │Detector    │ │ │Config       │ │ │Manager        │  │
│ ├───────────┤ │ ├─────────────┤ │ ├───────────────┤  │
│ │Agent       │ │ │Credential   │ │ │HealthMonitor  │  │
│ │Detector    │ │ │Manager      │ │ │               │  │
│ ├───────────┤ │ ├─────────────┤ │ ├───────────────┤  │
│ │Browser     │ │ │Transport    │ │ │VersionManager │  │
│ │Manager     │ │ │Factory      │ │ │               │  │
│ ├───────────┤ │ ├─────────────┤ │ ├───────────────┤  │
│ │Desktop     │ │ │Api          │ │ │UpdateManager  │  │
│ │Manager     │ │ │Manager      │ │ │               │  │
│ ├───────────┤ │ ├─────────────┤ │ └───────────────┘  │
│ │CLI         │ │ │YAML Configs │ │                    │
│ │Manager     │ │ └─────────────┘ │                    │
│ ├───────────┤ │                  │                    │
│ │MCP         │ │                  │                    │
│ │Manager     │ │                  │                    │
│ ├───────────┤ │                  │                    │
│ │Environment │ │                  │                    │
│ │Detector    │ │                  │                    │
│ ├───────────┤ │                  │                    │
│ │Workspace   │ │                  │                    │
│ │Detector    │ │                  │                    │
│ ├───────────┤ │                  │                    │
│ │Tool        │ │                  │                    │
│ │Detector    │ │                  │                    │
│ ├───────────┤ │                  │                    │
│ │Dependency  │ │                  │                    │
│ │Detector    │ │                  │                    │
│ └───────────┘ │                  │                    │
└─────────────────────────────────────────────────────┘
```

## Modules

### Discovery Modules

| Module | Purpose | Detection Methods |
|--------|---------|-------------------|
| `ProviderDetector` | Detect installed AI providers | `$ENV_VAR`, `$PATH`, config files |
| `AgentDetector` | Detect coding agents | Binary detection, config files |
| `BrowserManager` | Detect browsers | System paths, platform-specific |
| `DesktopManager` | Detect desktop apps | System paths, common locations |
| `CliManager` | Detect CLI tools | `shutil.which()`, version detection |
| `McpManager` | Discover MCP servers | Manifest files, capability registration |
| `EnvironmentDetector` | Detect runtime environment | `platform`, `os`, `shutil` |
| `WorkspaceDetector` | Detect workspace type | File analysis (package.json, setup.py, etc.) |
| `ToolDetector` | Detect developer tools | `shutil.which()`, binary scanning |
| `DependencyDetector` | Detect project deps | File analysis (requirements.txt, go.mod, etc.) |

### Configuration Modules

| Module | Purpose |
|--------|---------|
| `ProviderConfiguration` | Create/manage provider YAML configs |
| `CredentialManager` | Secure credential storage |
| `TransportFactory` | Dynamic transport creation |
| `ApiManager` | REST API provider management |

### Lifecycle Modules

| Module | Purpose |
|--------|---------|
| `ProviderManager` | Full provider lifecycle |
| `ProviderInstaller` | Installation guidance |
| `HealthMonitor` | Continuous health checking |
| `VersionManager` | Version tracking & compatibility |
| `UpdateManager` | Update checking |

## Discovery Flow

1. User runs `workflow setup` or `workflow doctor`
2. All detectors run automatically
3. Results are cached in the kernel's service registry
4. Health monitor tracks status changes
5. Events published for each discovery

## Event Flow

```
integration.provider_detected
integration.provider_registered
integration.provider_removed
integration.agent_detected
integration.agent_registered
integration.environment_scanned
integration.workspace_detected
integration.transport_ready
integration.setup_completed
integration.health_changed
integration.update_available
```

## Integration with Bootstrap

All integration services are registered automatically in `BootstrapSequence._register_integration_services()`:

1. Provider Manager
2. Provider Detector
3. Provider Installer
4. Provider Configuration
5. Credential Manager
6. Transport Factory
7. Browser Manager
8. Desktop Manager
9. CLI Manager
10. MCP Manager
11. API Manager
12. Agent Detector
13. Workspace Detector
14. Environment Detector
15. Tool Detector
16. Dependency Detector
17. Version Manager
18. Health Monitor
19. Update Manager

Health checkers are registered automatically for providers and CLI tools.
