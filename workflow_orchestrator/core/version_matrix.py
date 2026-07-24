"""Version Matrix Engine — compatibility validation across providers, protocol schemas, and contracts.

Validates compatibility for:
- Provider API versions
- MCP protocol versions (e.g. "2024-11-05")
- Plugin API versions ("1.0.0")
- Workflow YAML schema versions ("1.0.0")
- Project contract schema versions ("1.0.0")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class VersionCompatibilityReport:
    component: str
    target_version: str
    supported_versions: List[str]
    compatible: bool
    message: str = ""


class VersionMatrix:
    """Matrix of supported protocol, API, and schema versions."""

    SUPPORTED_VERSIONS: Dict[str, List[str]] = {
        "mcp_protocol": ["2024-11-05", "2024-10-07", "1.0.0"],
        "plugin_api": ["1.0.0", "1.1.0"],
        "workflow_schema": ["1.0.0", "1.1.0", "2.0.0"],
        "project_contract": ["1.0.0", "2.0.0"],
        "provider_api": ["v1", "v1beta", "2023-06-01", "2024-06-01"],
    }

    @classmethod
    def validate_compatibility(cls, category: str, version: str) -> VersionCompatibilityReport:
        """Validate if a given version string is compatible with the system matrix.

        Args:
            category: Version category key (mcp_protocol, plugin_api, etc.).
            version: Version string to check.

        Returns:
            VersionCompatibilityReport.
        """
        supported = cls.SUPPORTED_VERSIONS.get(category, ["1.0.0"])
        compatible = version in supported or any(version.startswith(s) for s in supported)
        
        msg = (
            f"Version '{version}' is compatible with category '{category}'."
            if compatible
            else f"Version '{version}' is INCOMPATIBLE with category '{category}' (supported: {supported})."
        )
        return VersionCompatibilityReport(
            component=category,
            target_version=version,
            supported_versions=supported,
            compatible=compatible,
            message=msg,
        )

    @classmethod
    def check_all(cls, versions: Dict[str, str]) -> List[VersionCompatibilityReport]:
        """Validate multiple component version targets."""
        reports: List[VersionCompatibilityReport] = []
        for cat, ver in versions.items():
            reports.append(cls.validate_compatibility(cat, ver))
        return reports
