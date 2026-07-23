# MCP Integration

## Overview

The Model Context Protocol (MCP) integration enables automatic discovery and registration of MCP servers. The `McpManager` discovers MCP manifests, registers capabilities, and exposes them through the Capability Registry.

## Architecture

```
┌─────────────────────────────────────────────┐
│              McpManager                       │
├─────────────────────────────────────────────┤
│  Discovery    │  Registry    │  Runtime      │
│ ┌───────────┐ │ ┌─────────┐ │ ┌───────────┐ │
│ │ Manifest   │→│ Server   │→│ Capability │ │
│ │ Scanner    │ │ Registry │ │ Resolution │ │
│ ├───────────┤ │ ├─────────┤ │ ├───────────┤ │
│ │ Config     │ │ │ Life-   │ │ │ Transport │ │
│ │ Watcher    │ │ │ cycle   │ │ │ Dispatch  │ │
│ └───────────┘ │ └─────────┘ │ └───────────┘ │
└───────────────┴─────────────┴───────────────┘
        │               │               │
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ File System │ │ Capability  │ │  Transport  │
│             │ │  Registry   │ │   Runtime   │
└─────────────┘ └─────────────┘ └─────────────┘
```

## Server Configuration

MCP servers are configured with a command and arguments:

```python
from workflow_orchestrator.integrations.mcp_manager import McpServerInfo, McpManager

server = McpServerInfo(
    name="filesystem",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/workspace"],
    capabilities=["read_file", "write_file", "search", "list_directory"],
)

manager = McpManager(event_bus=event_bus)
manager.register(server)
```

## Supported MCP Servers

The system can discover any MCP server implementing the protocol:

| Server | Command | Capabilities |
|--------|---------|--------------|
| Filesystem | `npx @modelcontextprotocol/server-filesystem` | read, write, search, list |
| Git | `npx @modelcontextprotocol/server-git` | clone, commit, push, pull, log |
| GitHub | `npx @modelcontextprotocol/server-github` | issues, PRs, repos, files |
| Browser | `npx @modelcontextprotocol/server-browser` | navigate, click, extract |
| Database | `npx @modelcontextprotocol/server-database` | query, schema, transactions |
| Custom | Any command | User-defined |

## Automatic Discovery

MCP servers are discovered from:

1. **Config directories:** Scan specified directories for MCP manifest files
2. **Package managers:** Detect MCP servers in node_modules, pip packages, etc.
3. **Environment variables:** Check for MCP-related environment configuration
4. **Common paths:** Check well-known MCP server installation locations

## Capability Registration

When an MCP server is registered, its capabilities are automatically registered in the Capability Registry:

```
mcp.filesystem.read_file
mcp.filesystem.write_file
mcp.filesystem.search
mcp.git.clone
mcp.git.commit
...
```

## Events

MCP servers publish these events:

| Event | Description |
|-------|-------------|
| `mcp.server_discovered` | New MCP server found |
| `mcp.server_registered` | Server registered in manager |
| `mcp.server_removed` | Server removed from manager |
| `mcp.server_error` | Server encountered an error |
| `mcp.capabilities_updated` | Server capabilities changed |

## CLI Commands

MCP servers are managed through the programmatic API. See CLI Commands documentation for general provider management.

```bash
# MCP servers are automatically discovered and managed
# through the integration services registered during setup

# View all registered capabilities
workflow providers
```

## Example: Custom MCP Server

```python
from workflow_orchestrator.integrations.mcp_manager import McpManager, McpServerInfo
from workflow_orchestrator.core.kernel import Kernel

# Get kernel and MCP manager
kernel = Kernel.create_default()
kernel.boot()
mcp_manager = kernel.get_service("mcp_manager")

# Register a custom server
server = McpServerInfo(
    name="custom-database",
    command="python",
    args=["-m", "mcp_server_database", "--db-url", "postgresql://localhost/mydb"],
    capabilities=["query", "execute", "schema"],
)
mcp_manager.register(server)

# List all registered servers
for s in mcp_manager.list_servers():
    print(f"{s.name}: {', '.join(s.capabilities)}")
```

## Integration with Capability Registry

MCP capabilities are indexed alongside provider and agent capabilities:

```python
# Capability lookup
capability_registry = kernel.get_service("capability_registry")
db_servers = capability_registry.find_providers("mcp.database.query")
```
