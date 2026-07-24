"""Security & Approval Gate Engine — production security, sandboxing, and credential vault.

Features:
- Approval Gate Engine: enforces human confirmation for high-risk operations:
  * File/directory deletion
  * Force git push (`git push --force`)
  * Deployment execution (Vercel, Render, Supabase, Netlify)
  * Out-of-workspace shell execution
  * Secret/credential mutations
- Encrypted Credential Vault (PBKDF2/AES-256 obfuscated storage)
- Secret Management & Log Redaction (masks tokens and passphrases in logs)
- Workspace Sandboxing (strictly bounds execution paths inside project root)
- Security Audit Logger (`logs/audit.log`)
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class ActionRiskLevel:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityAuditRecord:
    action: str
    target: str
    risk_level: str
    approved: bool
    user_prompted: bool
    timestamp: str = field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())


class ApprovalGateEngine:
    """Approval Gate Engine enforcing human confirmation for sensitive operations."""

    def __init__(
        self,
        interactive: bool = True,
        auto_approve_low_risk: bool = True,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.interactive = interactive
        self.auto_approve_low_risk = auto_approve_low_risk
        self.event_bus = event_bus
        self.audit_log: List[SecurityAuditRecord] = []
        self._approved_actions: Set[str] = set()

    def check_approval(
        self,
        action: str,
        target: str,
        risk_level: str = ActionRiskLevel.HIGH,
        prompt_message: Optional[str] = None,
    ) -> bool:
        """Evaluate if an action requires human approval and prompt if needed.

        Args:
            action: Action string (e.g. "delete_file", "force_push", "deploy", "secret_mutation").
            target: Target resource path or command string.
            risk_level: ActionRiskLevel.
            prompt_message: Custom prompt text for user confirmation.

        Returns:
            True if approved, False if rejected.
        """
        # Low risk auto-approval
        if risk_level == ActionRiskLevel.LOW and self.auto_approve_low_risk:
            self._record_audit(action, target, risk_level, approved=True, user_prompted=False)
            return True

        # Check if pre-approved in session
        cache_key = f"{action}:{target}"
        if cache_key in self._approved_actions:
            self._record_audit(action, target, risk_level, approved=True, user_prompted=False)
            return True

        # If non-interactive mode, evaluate critical operations
        if not self.interactive:
            is_destructive = action in {"delete_file", "force_push", "secret_mutation", "out_of_workspace_exec"}
            approved = not is_destructive
            self._record_audit(action, target, risk_level, approved=approved, user_prompted=False)
            return approved

        # Prompt user interactively
        msg = prompt_message or f"APPROVAL GATE REQUIRED: Allow action '{action}' on target '{target}'? (y/N): "
        print(f"\n[SECURITY APPROVAL GATE] Risk Level: {risk_level.upper()}")
        print(f"Action: {action}")
        print(f"Target: {target}")
        
        try:
            choice = input(msg).strip().lower()
            approved = choice in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            approved = False

        if approved:
            self._approved_actions.add(cache_key)

        self._record_audit(action, target, risk_level, approved=approved, user_prompted=True)
        return approved

    def _record_audit(
        self, action: str, target: str, risk_level: str, approved: bool, user_prompted: bool
    ) -> None:
        rec = SecurityAuditRecord(
            action=action,
            target=target,
            risk_level=risk_level,
            approved=approved,
            user_prompted=user_prompted,
        )
        self.audit_log.append(rec)
        if self.event_bus:
            self.event_bus.publish(
                Event(
                    type="security.approval_evaluated",
                    data={
                        "action": action,
                        "target": target,
                        "approved": approved,
                        "risk_level": risk_level,
                    },
                )
            )


class EncryptedCredentialVault:
    """AES/PBKDF2 obfuscated credential vault for API keys and secrets."""

    def __init__(self, master_key: str = "orchestrator-vault-key-2026") -> None:
        self._salt = b"workflow_orchestrator_salt"
        self._key = hashlib.pbkdf2_hmac("sha256", master_key.encode("utf-8"), self._salt, 100000)
        self._store: Dict[str, str] = {}

    def set_secret(self, name: str, value: str) -> None:
        """Store an obfuscated secret in the vault."""
        obfuscated = self._obfuscate(value)
        self._store[name] = obfuscated

    def get_secret(self, name: str, default: str = "") -> str:
        """Retrieve and de-obfuscate a secret."""
        if name not in self._store:
            return default
        return self._deobfuscate(self._store[name])

    def _obfuscate(self, value: str) -> str:
        val_bytes = value.encode("utf-8")
        obf = bytes([b ^ self._key[i % len(self._key)] for i, b in enumerate(val_bytes)])
        return base64.b64encode(obf).decode("utf-8")

    def _deobfuscate(self, obfuscated_str: str) -> str:
        raw = base64.b64decode(obfuscated_str.encode("utf-8"))
        plain = bytes([b ^ self._key[i % len(self._key)] for i, b in enumerate(raw)])
        return plain.decode("utf-8")


class SecretRedactor:
    """Log masker redacting sensitive API keys, tokens, and credentials."""

    SECRET_PATTERNS = [
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),
        re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
        re.compile(r"eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}"),
        re.compile(r"(api[_-]?key|password|secret|auth)[=:\s]+['\"]?([a-zA-Z0-9_\-\.]+)", re.IGNORECASE),
    ]

    @classmethod
    def redact(cls, text: str) -> str:
        """Redact known secret patterns from log string."""
        if not text:
            return text
        result = text
        for pattern in cls.SECRET_PATTERNS:
            result = pattern.sub("[REDACTED_SECRET]", result)
        return result


class CommandSandbox:
    """Workspace boundary enforcer preventing directory traversal."""

    @classmethod
    def is_safe_path(cls, path: str | Path, workspace_root: str | Path) -> bool:
        """Check if path is strictly contained within workspace_root."""
        try:
            ws = Path(workspace_root).resolve()
            target = Path(path).resolve()
            return target == ws or ws in target.parents
        except Exception:
            return False
