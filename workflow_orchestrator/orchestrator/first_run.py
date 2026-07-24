"""First Run Setup Wizard — interactive/automated initial configuration.

When no configuration exists or upon explicit `workflow setup` invocation:
Configures Providers, API Keys, CLI Paths, Workspace, Git, GitHub,
Render, Vercel, MCP Servers, Default Editor, Default Browser, Default Deployment.
Saves working configuration files.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from workflow_orchestrator.config.config_manager import ConfigurationManager
from workflow_orchestrator.integrations.credential_manager import CredentialManager
from workflow_orchestrator.integrations.provider_configuration import ProviderConfiguration
from workflow_orchestrator.orchestrator.discovery import AutoDiscovery

logger = logging.getLogger(__name__)


@dataclass
class SetupConfiguration:
    """Complete setup configuration model."""

    workspace_path: str = field(default_factory=lambda: str(Path.cwd()))
    providers: List[str] = field(default_factory=lambda: ["claude", "chatgpt", "gemini"])
    api_keys: Dict[str, str] = field(default_factory=dict)
    cli_paths: Dict[str, str] = field(default_factory=dict)
    use_git: bool = True
    use_github: bool = True
    use_render: bool = False
    use_vercel: bool = False
    mcp_servers: List[str] = field(default_factory=list)
    default_editor: str = "vscode"
    default_browser: str = "chrome"
    default_deployment: str = "vercel"


class SetupWizard:
    """Setup wizard guiding first-time initialization."""

    def __init__(
        self,
        config_manager: Optional[ConfigurationManager] = None,
        credential_manager: Optional[CredentialManager] = None,
        provider_config: Optional[ProviderConfiguration] = None,
        discovery: Optional[AutoDiscovery] = None,
    ) -> None:
        self.config_mgr = config_manager or ConfigurationManager()
        self.cred_mgr = credential_manager or CredentialManager()
        self.prov_config = provider_config or ProviderConfiguration()
        self.discovery = discovery or AutoDiscovery()

    def run_automated_setup(self, setup_data: Optional[SetupConfiguration] = None) -> SetupConfiguration:
        """Run non-interactive automated setup based on auto-discovery and default parameters."""
        cfg = setup_data or SetupConfiguration()
        audit = self.discovery.run_full_discovery()

        # Update detected options
        cfg.use_git = audit.git_installed
        cfg.use_github = audit.github_cli_installed
        cfg.use_render = audit.render_cli_installed
        cfg.use_vercel = audit.vercel_cli_installed

        # Save settings
        self.config_mgr.set("workspace.root", cfg.workspace_path)
        self.config_mgr.set("editor.default", cfg.default_editor)
        self.config_mgr.set("browser.default", cfg.default_browser)
        self.config_mgr.set("deployment.default", cfg.default_deployment)

        # Store provided API keys
        for key_name, val in cfg.api_keys.items():
            if val:
                self.cred_mgr.set_api_key(key_name, val)

        # Write provider YAML configs
        for p in cfg.providers:
            p_cfg = self.prov_config.read(p) or {"name": p.title(), "provider_id": p}
            p_cfg["enabled"] = True
            if p in cfg.cli_paths:
                p_cfg["cli_path"] = cfg.cli_paths[p]
            self.prov_config.write(p, p_cfg)

        logger.info("Automated setup completed successfully for workspace: %s", cfg.workspace_path)
        return cfg
