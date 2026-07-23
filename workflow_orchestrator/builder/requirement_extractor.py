"""Requirement Extractor — transforms a simple user idea into structured requirements.

Produces deterministic, structured output:
- Vision: High-level project vision
- Objectives: Clear objectives
- Features: Feature list
- Constraints: Technical and business constraints
- Users: Target user profiles
- Functional Requirements: What the system must do
- Non-functional Requirements: Performance, security, scalability
- Acceptance Criteria: How to verify completion
- Risk List: Identified risks
- Questions: Open questions for clarification

No AI reasoning — purely rule-based extraction using keywords and patterns.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from workflow_orchestrator.core.event_bus import Event, EventBus

logger = logging.getLogger(__name__)


class RequirementExtractor:
    """Extracts structured requirements from a natural-language project idea.

    Uses keyword patterns and domain-specific heuristics to transform
    a user's simple description into a complete requirements document.

    Usage:
        >>> extractor = RequirementExtractor()
        >>> reqs = extractor.extract("Build a food delivery platform")
        >>> print(reqs["vision"][:50])
    """

    # Domain-specific keyword maps for feature extraction
    _DOMAIN_FEATURES: dict[str, list[str]] = {
        "auth": ["login", "signup", "register", "authentication", "oauth", "sso", "password"],
        "payment": ["payment", "checkout", "stripe", "paypal", "billing", "invoice", "subscription"],
        "notification": ["notification", "email", "push", "alert", "sms", "webhook"],
        "search": ["search", "filter", "query", "index", "elasticsearch"],
        "social": ["social", "share", "like", "comment", "follow", "feed", "post"],
        "analytics": ["analytics", "dashboard", "report", "metric", "statistics", "monitoring"],
        "file": ["upload", "download", "file", "image", "document", "storage", "cdn"],
        "realtime": ["realtime", "websocket", "live", "stream", "chat", "presence"],
        "admin": ["admin", "dashboard", "management", "crud", "moderation"],
        "api": ["api", "rest", "graphql", "endpoint", "integration", "webhook"],
        "database": ["database", "sql", "nosql", "postgresql", "mongodb", "redis", "cache"],
        "deployment": ["deploy", "ci/cd", "docker", "kubernetes", "hosting", "cloud"],
    }

    # Technology stack patterns
    _TECH_PATTERNS: dict[str, list[str]] = {
        "python": ["python", "django", "flask", "fastapi"],
        "javascript": ["javascript", "js", "node", "express", "react", "vue", "angular", "svelte"],
        "typescript": ["typescript", "ts", "next.js", "nest"],
        "java": ["java", "spring", "maven", "gradle"],
        "go": ["go", "golang"],
        "rust": ["rust", "cargo"],
        "mobile": ["swift", "kotlin", "flutter", "react native"],
        "infrastructure": ["docker", "kubernetes", "terraform", "ansible"],
    }

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the Requirement Extractor.

        Args:
            event_bus: Optional EventBus for publishing events.
        """
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def extract(self, idea: str, project_name: str = "") -> dict[str, Any]:
        """Extract structured requirements from a project idea.

        Args:
            idea: The user's project idea or description.
            project_name: Optional project name.

        Returns:
            Dict with keys: vision, objectives, features, constraints, users,
            functional_requirements, non_functional_requirements,
            acceptance_criteria, risk_list, questions.
        """
        text = f"{project_name} {idea}".lower()

        requirements: dict[str, Any] = {
            "vision": self._extract_vision(idea, project_name),
            "objectives": self._extract_objectives(idea),
            "features": self._extract_features(text),
            "constraints": self._extract_constraints(text),
            "users": self._extract_users(text),
            "functional_requirements": self._extract_functional_requirements(text),
            "non_functional_requirements": self._extract_non_functional_requirements(text),
            "acceptance_criteria": self._extract_acceptance_criteria(idea),
            "risk_list": self._extract_risks(text),
            "questions": self._extract_questions(text),
        }

        self._publish_event("builder.requirements_extracted", {
            "project_name": project_name or idea[:50],
            "feature_count": len(requirements["features"]),
            "requirement_count": len(requirements["functional_requirements"]),
        })

        logger.info(
            "Extracted %d features, %d functional requirements from '%s'",
            len(requirements["features"]),
            len(requirements["functional_requirements"]),
            project_name or idea[:50],
        )
        return requirements

    def _extract_vision(self, idea: str, project_name: str) -> str:
        """Generate a vision statement from the idea.

        Args:
            idea: The project idea.
            project_name: Optional project name.

        Returns:
            A vision statement.
        """
        name = project_name or "this project"
        return f"Create a {idea.strip().lower()} that delivers an exceptional user experience through modern technology and thoughtful design. {name} aims to solve real user problems with a focus on reliability, performance, and usability."

    def _extract_objectives(self, idea: str) -> list[str]:
        """Extract objectives from the idea.

        Args:
            idea: The project idea.

        Returns:
            List of objective statements.
        """
        return [
            f"Build a fully functional {idea.strip().lower()}",
            "Ensure high code quality through testing and code review",
            "Deliver a seamless user experience with responsive design",
            "Implement robust error handling and monitoring",
            "Create comprehensive documentation for developers and users",
        ]

    def _extract_features(self, text: str) -> list[dict[str, Any]]:
        """Extract feature candidates based on domain keywords.

        Args:
            text: The normalized description text.

        Returns:
            List of feature dicts with name, description, priority.
        """
        features: list[dict[str, Any]] = []
        detected_domains: set[str] = set()

        for domain, keywords in self._DOMAIN_FEATURES.items():
            matched = any(re.search(re.escape(kw), text) for kw in keywords)
            if matched:
                detected_domains.add(domain)

        domain_features: dict[str, tuple[str, str, str]] = {
            "auth": ("User Authentication", "User registration, login, and session management", "high"),
            "payment": ("Payment Processing", "Payment integration with multiple providers", "high"),
            "notification": ("Notifications", "Push, email, and in-app notification system", "medium"),
            "search": ("Search Functionality", "Full-text search with filtering and pagination", "medium"),
            "social": ("Social Features", "Social interactions like sharing and commenting", "medium"),
            "analytics": ("Analytics Dashboard", "Usage analytics and reporting dashboard", "medium"),
            "file": ("File Management", "File upload, storage, and content delivery", "medium"),
            "realtime": ("Real-time Updates", "Real-time data synchronization and live updates", "medium"),
            "admin": ("Admin Panel", "Administrative interface for content management", "high"),
            "api": ("API Layer", "RESTful or GraphQL API for external integrations", "high"),
            "database": ("Data Storage", "Database schema design and data persistence layer", "high"),
            "deployment": ("Deployment Pipeline", "Automated CI/CD pipeline and deployment infrastructure", "high"),
        }

        for domain in detected_domains:
            if domain in domain_features:
                name, desc, priority = domain_features[domain]
                features.append({"name": name, "description": desc, "priority": priority})

        # Always include core features
        core_features = [
            {"name": "Project Setup", "description": "Initialize project structure, dependencies, and tooling", "priority": "high"},
            {"name": "Testing Suite", "description": "Unit, integration, and end-to-end tests", "priority": "high"},
            {"name": "Documentation", "description": "Comprehensive project documentation", "priority": "medium"},
        ]

        return core_features + features

    def _extract_constraints(self, text: str) -> list[dict[str, Any]]:
        """Extract constraints from the description.

        Args:
            text: The normalized description text.

        Returns:
            List of constraint dicts with category, description, severity.
        """
        constraints: list[dict[str, Any]] = [
            {"category": "quality", "description": "All code must pass linting and type checking", "severity": "must"},
            {"category": "testing", "description": "Core functionality must have unit test coverage", "severity": "must"},
            {"category": "documentation", "description": "All public APIs must be documented", "severity": "should"},
            {"category": "security", "description": "Follow security best practices for the tech stack", "severity": "must"},
        ]

        # Add domain-specific constraints
        if any(kw in text for kw in ["payment", "stripe", "billing"]):
            constraints.append({
                "category": "compliance",
                "description": "Payment processing must comply with PCI DSS standards",
                "severity": "must",
            })

        if any(kw in text for kw in ["user", "login", "auth"]):
            constraints.append({
                "category": "security",
                "description": "User data must be encrypted at rest and in transit",
                "severity": "must",
            })

        if any(kw in text for kw in ["mobile", "ios", "android"]):
            constraints.append({
                "category": "performance",
                "description": "Application must perform well on mobile networks",
                "severity": "must",
            })

        return constraints

    def _extract_users(self, text: str) -> list[dict[str, Any]]:
        """Extract user profiles from the description.

        Args:
            text: The normalized description text.

        Returns:
            List of user profile dicts.
        """
        users: list[dict[str, Any]] = [
            {
                "role": "End User",
                "description": "Primary user who interacts with the application",
                "needs": ["Intuitive interface", "Fast response times", "Reliable functionality"],
            },
            {
                "role": "Administrator",
                "description": "User who manages the system and its content",
                "needs": ["Management dashboard", "User management", "Content moderation"],
            },
        ]

        # Add developer if API or library type
        if any(kw in text for kw in ["api", "sdk", "library", "package"]):
            users.append({
                "role": "Developer",
                "description": "Developer integrating with the system",
                "needs": ["Clear API documentation", "SDK/client libraries", "Sandbox environment"],
            })

        return users

    def _extract_functional_requirements(self, text: str) -> list[dict[str, Any]]:
        """Extract functional requirements.

        Args:
            text: The normalized description text.

        Returns:
            List of functional requirement dicts.
        """
        requirements: list[dict[str, Any]] = [
            {"id": "FR-001", "description": "User must be able to access the application", "priority": "high"},
            {"id": "FR-002", "description": "System must handle user input and provide feedback", "priority": "high"},
            {"id": "FR-003", "description": "System must persist data across sessions", "priority": "high"},
            {"id": "FR-004", "description": "System must handle errors gracefully", "priority": "high"},
        ]

        # Add domain-specific requirements
        if any(kw in text for kw in ["login", "auth", "register"]):
            requirements.append({
                "id": "FR-005", "description": "User must be able to register and authenticate", "priority": "high",
            })

        return requirements

    def _extract_non_functional_requirements(self, text: str) -> list[dict[str, Any]]:
        """Extract non-functional requirements.

        Args:
            text: The normalized description text.

        Returns:
            List of non-functional requirement dicts.
        """
        return [
            {"category": "performance", "description": "Application should respond within 2 seconds", "priority": "high"},
            {"category": "availability", "description": "System should be available 99.9% of the time", "priority": "medium"},
            {"category": "security", "description": "All communications must be encrypted via HTTPS", "priority": "high"},
            {"category": "maintainability", "description": "Code must follow clean architecture principles", "priority": "medium"},
            {"category": "scalability", "description": "System should scale horizontally for increased load", "priority": "medium"},
        ]

    def _extract_acceptance_criteria(self, idea: str) -> list[str]:
        """Extract acceptance criteria.

        Args:
            idea: The project idea.

        Returns:
            List of acceptance criteria strings.
        """
        return [
            f"The {idea.strip().lower()} is fully functional and meets all requirements",
            "All tests pass with adequate code coverage",
            "Code passes linting and type checking",
            "Documentation is complete and accurate",
            "Application is deployable to production",
        ]

    def _extract_risks(self, text: str) -> list[dict[str, Any]]:
        """Extract identified risks.

        Args:
            text: The normalized description text.

        Returns:
            List of risk dicts.
        """
        return [
            {"risk": "Scope creep", "likelihood": "medium", "impact": "high", "mitigation": "Clear requirements and phased delivery"},
            {"risk": "Integration complexity", "likelihood": "medium", "impact": "medium", "mitigation": "Early API definition and testing"},
            {"risk": "Performance issues at scale", "likelihood": "low", "impact": "high", "mitigation": "Performance testing and monitoring"},
            {"risk": "Security vulnerabilities", "likelihood": "low", "impact": "critical", "mitigation": "Security review and penetration testing"},
        ]

    def _extract_questions(self, text: str) -> list[str]:
        """Extract open questions for clarification.

        Args:
            text: The normalized description text.

        Returns:
            List of question strings.
        """
        return [
            "What is the primary target audience?",
            "What is the expected scale (users, data volume)?",
            "Are there any specific design or branding requirements?",
            "What is the timeline for delivery?",
            "Are there any existing systems to integrate with?",
        ]

    # ------------------------------------------------------------------
    # Event publishing
    # ------------------------------------------------------------------

    def _publish_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event if an event bus is available.

        Args:
            event_type: The event type string.
            data: Event payload.
        """
        if self._event_bus is None:
            return
        try:
            self._event_bus.publish(Event(
                type=event_type, data=data, source="requirement_extractor",
            ))
        except Exception:
            pass
