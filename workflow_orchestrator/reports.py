"""Execution report management for the Workflow Orchestrator.

Handles generating, storing, and retrieving execution reports
as JSON files in the ``reports/`` directory.  Also provides
summary statistics across multiple reports.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.models import ExecutionReport

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def _ensure_reports_dir() -> Path:
    """Create the reports directory if it doesn't exist."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def save_report(report: ExecutionReport) -> Path:
    """Save an execution report to disk as JSON.

    Args:
        report: The execution report to save.

    Returns:
        Path: The path to the saved report file.
    """
    reports_dir = _ensure_reports_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in report.workflow_name)
    safe_name = safe_name.strip().replace(" ", "_")[:50]

    filename = f"{timestamp}_{safe_name}.json"
    filepath = reports_dir / filename

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        logger.info("Execution report saved to %s", filepath)
    except OSError as exc:
        logger.error("Failed to save report to %s: %s", filepath, exc)

    return filepath


def load_report(path: Path) -> Optional[dict[str, Any]]:
    """Load a single execution report from disk.

    Args:
        path: Path to the report JSON file.

    Returns:
        Optional[dict]: Report data as a dictionary, or None if loading failed.
    """
    if not path.exists():
        logger.warning("Report file not found: %s", path)
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load report %s: %s", path, exc)
        return None


def list_reports(limit: int = 20) -> list[dict[str, Any]]:
    """List recent execution reports, newest first.

    Args:
        limit: Maximum number of reports to return.

    Returns:
        list[dict]: List of report summaries (name, timestamp, status).
    """
    if not REPORTS_DIR.exists():
        return []

    reports: list[dict[str, Any]] = []
    for path in sorted(REPORTS_DIR.glob("*.json"), reverse=True):
        data = load_report(path)
        if data:
            reports.append({
                "path": str(path),
                "workflow_name": data.get("workflow_name", "unknown"),
                "timestamp": data.get("timestamp", ""),
                "duration": data.get("duration", 0),
                "success": data.get("success", False),
                "successful_steps": data.get("successful_steps", 0),
                "total_steps": data.get("total_steps", 0),
                "failed_steps": data.get("failed_steps", 0),
                "error": data.get("error"),
            })
        if len(reports) >= limit:
            break

    return reports


def get_statistics() -> dict[str, Any]:
    """Compute summary statistics across all execution reports.

    Returns:
        dict: Statistics including total runs, success rate, etc.
    """
    if not REPORTS_DIR.exists():
        return {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "success_rate": 0.0,
            "total_duration": 0.0,
            "average_duration": 0.0,
            "most_run_workflow": "",
        }

    reports = list_reports(limit=1000)
    if not reports:
        return {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "success_rate": 0.0,
            "total_duration": 0.0,
            "average_duration": 0.0,
            "most_run_workflow": "",
        }

    total_runs = len(reports)
    successful_runs = sum(1 for r in reports if r["success"])
    failed_runs = total_runs - successful_runs
    total_duration = sum(r["duration"] for r in reports)
    avg_duration = total_duration / total_runs if total_runs > 0 else 0.0
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0.0

    # Most run workflow
    workflow_counts: dict[str, int] = {}
    for r in reports:
        name = r["workflow_name"]
        workflow_counts[name] = workflow_counts.get(name, 0) + 1
    most_run = max(workflow_counts, key=workflow_counts.get) if workflow_counts else ""

    return {
        "total_runs": total_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "success_rate": round(success_rate, 1),
        "total_duration": round(total_duration, 2),
        "average_duration": round(avg_duration, 2),
        "most_run_workflow": most_run,
    }
