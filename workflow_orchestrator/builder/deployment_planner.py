"""Deployment Planner — creates deployment plans automatically.

Produces:
- Environment variables
- Hosting configuration
- Secrets management
- CI/CD configuration
- Monitoring setup
- Rollback strategy
- Scaling configuration
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from workflow_orchestrator.builder.data_models import DeploymentPlan
from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class DeploymentPlanner:
    """Creates deployment plans from architecture and project type.

    Generates complete deployment configuration including hosting,
    environment variables, secrets, CI/CD, monitoring, rollback,
    and scaling strategies.

    Usage:
        >>> planner = DeploymentPlanner()
        >>> plan = planner.plan(architecture, project_id)
        >>> print(plan.hosting_platform)
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Deployment Planner.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def plan(
        self,
        architecture: dict[str, Any],
        project_id: str,
        project_name: str = "",
    ) -> DeploymentPlan:
        """Create a deployment plan from the architecture specification.

        Args:
            architecture: The architecture specification.
            project_id: The project identifier.
            project_name: Optional project name.

        Returns:
            A DeploymentPlan with complete deployment configuration.
        """
        tech_stack = architecture.get("technology_stack", {})
        deployment_info = architecture.get("deployment", {})

        hosting = deployment_info.get("hosting", "Cloud provider")
        framework = tech_stack.get("framework", "")
        language = tech_stack.get("language", "")

        plan = DeploymentPlan(
            plan_id=uuid.uuid4().hex[:12],
            project_id=project_id,
            hosting_platform=self._determine_hosting(framework, language),
            environment_variables=self._generate_env_vars(project_id, framework),
            secrets=self._generate_secrets(framework),
            ci_cd_config=self._generate_cicd_config(framework, language),
            monitoring_config=self._generate_monitoring_config(),
            rollback_config=self._generate_rollback_config(),
            scaling_config=self._generate_scaling_config(),
            additional_steps=self._generate_additional_steps(hosting),
        )

        self._publish_event("builder.deployment_planned", {
            "project_id": project_id,
            "hosting": plan.hosting_platform,
            "secrets_count": len(plan.secrets),
        })

        logger.info("Created deployment plan for project '%s'", project_id)
        return plan

    def _determine_hosting(self, framework: str, language: str) -> str:
        """Determine the best hosting platform.

        Args:
            framework: The web framework.
            language: The programming language.

        Returns:
            Hosting platform name.
        """
        hosting_map: dict[str, str] = {
            "next.js": "Vercel",
            "react": "Vercel / Netlify",
            "vue": "Netlify / Vercel",
            "django": "Railway / Heroku",
            "flask": "Railway / Render",
            "fastapi": "Railway / Render",
            "express": "Railway / Heroku",
            "spring": "AWS Elastic Beanstalk",
            "laravel": "Forge / Vapor",
        }

        framework_lower = framework.lower()
        for key, value in hosting_map.items():
            if key in framework_lower:
                return value

        return "AWS / GCP / Azure"

    def _generate_env_vars(self, project_id: str, framework: str) -> list[dict[str, str]]:
        """Generate required environment variables.

        Args:
            project_id: The project identifier.
            framework: The web framework.

        Returns:
            List of env var dicts with name and description.
        """
        env_vars: list[dict[str, str]] = [
            {"name": "NODE_ENV", "description": "Node environment (development/production)"},
            {"name": "PORT", "description": "Application port"},
            {"name": "DATABASE_URL", "description": "Database connection string"},
            {"name": "REDIS_URL", "description": "Redis connection string (if applicable)"},
            {"name": "LOG_LEVEL", "description": "Logging level (debug/info/warn/error)"},
            {"name": "PROJECT_ID", "description": f"Project ID: {project_id}"},
        ]

        if "next" in framework.lower():
            env_vars.extend([
                {"name": "NEXT_PUBLIC_API_URL", "description": "Public API URL"},
                {"name": "NEXT_PUBLIC_SITE_URL", "description": "Public site URL"},
            ])

        return env_vars

    def _generate_secrets(self, framework: str) -> list[str]:
        """Generate required secrets.

        Args:
            framework: The web framework.

        Returns:
            List of secret names.
        """
        secrets = [
            "DATABASE_PASSWORD",
            "SECRET_KEY",
            "JWT_SECRET",
        ]

        if "next" in framework.lower() or "react" in framework.lower():
            secrets.extend([
                "OAUTH_CLIENT_ID",
                "OAUTH_CLIENT_SECRET",
                "ENCRYPTION_KEY",
            ])

        return secrets

    def _generate_cicd_config(self, framework: str, language: str) -> str:
        """Generate CI/CD configuration description.

        Args:
            framework: The web framework.
            language: The programming language.

        Returns:
            CI/CD configuration description.
        """
        return (
            "Platform: GitHub Actions\n"
            "Triggers: Push to main, Pull requests\n"
            "Stages:\n"
            "  1. Lint and type-check\n"
            "  2. Run tests (unit + integration)\n"
            "  3. Build application\n"
            "  4. Deploy to staging\n"
            "  5. Run integration tests\n"
            "  6. Deploy to production (manual approval)\n"
            f"Framework: {framework}\n"
            f"Language: {language}\n"
            "Caching: npm/yarn/pip cache\n"
            "Notifications: Slack/Email on failure"
        )

    def _generate_monitoring_config(self) -> str:
        """Generate monitoring configuration description.

        Returns:
            Monitoring configuration description.
        """
        return (
            "Application Monitoring:\n"
            "  - Health check endpoint (/health)\n"
            "  - Request logging (structured JSON)\n"
            "  - Error tracking (Sentry)\n"
            "  - Performance monitoring\n"
            "Infrastructure Monitoring:\n"
            "  - Server metrics (CPU, memory, disk)\n"
            "  - Database monitoring\n"
            "  - Uptime monitoring\n"
            "Alerting:\n"
            "  - Error rate threshold alerts\n"
            "  - Latency threshold alerts\n"
            "  - Uptime alerts (PagerDuty/Email)"
        )

    def _generate_rollback_config(self) -> str:
        """Generate rollback strategy description.

        Returns:
            Rollback strategy description.
        """
        return (
            "Deployment Strategy: Blue-green deployment\n"
            "Rollback Trigger:\n"
            "  - Automated: Health check failure after deploy\n"
            "  - Manual: Any time via rollback button\n"
            "Rollback Process:\n"
            "  1. Route traffic back to previous version\n"
            "  2. Run database migration rollback\n"
            "  3. Verify previous version health\n"
            "  4. Notify team of rollback\n"
            "Recovery:\n"
            "  - Previous deployment image tagged and preserved\n"
            "  - Database backups before each migration\n"
            "  - Git tag for every deployment"
        )

    def _generate_scaling_config(self) -> str:
        """Generate scaling configuration description.

        Returns:
            Scaling configuration description.
        """
        return (
            "Horizontal Scaling:\n"
            "  - Load balancer distributing traffic\n"
            "  - Auto-scaling groups (min: 2, max: 10)\n"
            "  - Stateless application design\n"
            "Database Scaling:\n"
            "  - Read replicas for query load\n"
            "  - Connection pooling\n"
            "  - Automated sharding (future)\n"
            "Caching:\n"
            "  - Redis for session and cache\n"
            "  - CDN for static assets\n"
            "  - Database query caching"
        )

    def _generate_additional_steps(self, hosting: str) -> list[str]:
        """Generate additional deployment steps.

        Args:
            hosting: Hosting platform description.

        Returns:
            List of additional deployment steps.
        """
        return [
            f"Set up {hosting} account and configure project",
            "Configure custom domain and SSL certificate",
            "Set up environment variables in hosting platform",
            "Configure secrets in CI/CD pipeline",
            "Set up monitoring and alerting",
            "Configure backup strategy",
            "Set up staging environment",
            "Configure database backup schedule",
            "Document runbook for incident response",
        ]

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available."""
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="deployment_planner",
            ))
        except Exception:
            pass
