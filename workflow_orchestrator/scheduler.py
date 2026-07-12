"""Workflow scheduler using APScheduler.

Supports scheduling workflows to run:
- once (immediate or at a specific time)
- daily (at a specific time)
- weekly (on a specific day and time)
- at startup (when the scheduler starts)
- by cron expression (full flexibility)

The scheduler runs in the background using APScheduler's
``BackgroundScheduler``.  Each scheduled job executes the
workflow engine and saves the report.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from workflow_orchestrator.engine import WorkflowEngine
from workflow_orchestrator.reports import save_report

logger = logging.getLogger(__name__)


@dataclass
class ScheduledWorkflow:
    """A workflow that has been scheduled for execution.

    Attributes:
        workflow_path: Path to the YAML workflow file.
        name: Display name of this schedule.
        schedule_type: Type of schedule (once, daily, weekly, startup, cron).
        cron_expression: Cron expression (for cron type).
        time: Time string in HH:MM format (for daily/weekly).
        day: Day of week (for weekly).
        job_id: APScheduler job ID (populated after scheduling).
        enabled: Whether the schedule is active.
    """

    workflow_path: str
    name: str = ""
    schedule_type: str = "once"
    cron_expression: str = ""
    time: str = "09:00"
    day: str = "mon"
    job_id: str = ""
    enabled: bool = True


class WorkflowScheduler:
    """Manages scheduled workflow execution using APScheduler.

    Usage:
        >>> scheduler = WorkflowScheduler()
        >>> scheduler.start()
        >>> scheduler.add_job("workflows/daily.yaml", schedule_type="daily", time="09:00")
    """

    def __init__(
        self,
        engine: WorkflowEngine | None = None,
        profile: str = "default",
    ) -> None:
        """Initialize the scheduler.

        Args:
            engine: Workflow engine to use for execution.
                Defaults to a fresh ``WorkflowEngine``.
            profile: Configuration profile to use.
        """
        self._engine = engine or WorkflowEngine()
        self._profile = profile
        self._scheduler: Any = None  # APScheduler BackgroundScheduler
        self._jobs: dict[str, ScheduledWorkflow] = {}
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._running:
            logger.warning("Scheduler is already running.")
            return

        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.executors.pool import ThreadPoolExecutor

            executors = {
                "default": ThreadPoolExecutor(max_workers=5),
            }
            job_defaults = {
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 60,
            }

            self._scheduler = BackgroundScheduler(
                executors=executors,
                job_defaults=job_defaults,
            )
            self._running = True
            self._scheduler.start()
            logger.info("Workflow scheduler started.")
        except ImportError:
            logger.error(
                "APScheduler is not installed. Install it with: pip install apscheduler"
            )
            raise
        except Exception as exc:
            logger.error("Failed to start scheduler: %s", exc)
            raise

    def stop(self) -> None:
        """Stop the scheduler and all running jobs."""
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Workflow scheduler stopped.")

    @property
    def running(self) -> bool:
        """Whether the scheduler is currently running."""
        return self._running

    # ------------------------------------------------------------------
    # Job management
    # ------------------------------------------------------------------

    def add_job(self, workflow_path: str | Path, **kwargs: Any) -> Optional[str]:
        """Add a scheduled workflow job.

        Args:
            workflow_path: Path to the YAML workflow file.
            **kwargs: Schedule configuration:
                - schedule_type: ``once``, ``daily``, ``weekly``, ``startup``, ``cron``
                - time: Time string for daily/weekly (HH:MM)
                - day: Day of week for weekly
                - cron_expression: Cron expression for cron type
                - name: Display name for the schedule

        Returns:
            Optional[str]: The APScheduler job ID, or None if failed.
        """
        path = Path(workflow_path).expanduser().resolve()
        if not path.exists():
            logger.error("Workflow file not found: %s", path)
            return None

        schedule_type = kwargs.get("schedule_type", "once")
        name = kwargs.get("name", path.stem.replace("_", " ").title())
        time_str = kwargs.get("time", "09:00")
        day = kwargs.get("day", "mon")
        cron_expression = kwargs.get("cron_expression", "")

        if not self._scheduler:
            self.start()

        job_id = f"{path.stem}_{schedule_type}_{int(datetime.now().timestamp())}"

        try:
            trigger = self._build_trigger(
                schedule_type, time_str, day, cron_expression
            )

            self._scheduler.add_job(
                self._execute_workflow_job,
                trigger=trigger,
                args=[str(path), name],
                id=job_id,
                name=name,
                replace_existing=False,
            )

            scheduled = ScheduledWorkflow(
                workflow_path=str(path),
                name=name,
                schedule_type=schedule_type,
                cron_expression=cron_expression,
                time=time_str,
                day=day,
                job_id=job_id,
            )
            self._jobs[job_id] = scheduled

            logger.info(
                "Scheduled workflow '%s' (%s): %s",
                name,
                schedule_type,
                path,
            )
            return job_id

        except Exception as exc:
            logger.error("Failed to schedule job: %s", exc)
            return None

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job.

        Args:
            job_id: The APScheduler job ID.

        Returns:
            bool: True if removed successfully.
        """
        try:
            if self._scheduler:
                self._scheduler.remove_job(job_id)
            self._jobs.pop(job_id, None)
            logger.info("Removed scheduled job: %s", job_id)
            return True
        except Exception as exc:
            logger.error("Failed to remove job %s: %s", job_id, exc)
            return False

    def list_jobs(self) -> list[dict[str, Any]]:
        """List all scheduled jobs.

        Returns:
            list[dict]: List of job information dictionaries.
        """
        jobs: list[dict[str, Any]] = []

        for job_id, scheduled in self._jobs.items():
            next_run = None
            if self._scheduler:
                try:
                    job = self._scheduler.get_job(job_id)
                    if job and job.next_run_time:
                        next_run = job.next_run_time.isoformat()
                except Exception:
                    pass

            jobs.append({
                "job_id": job_id,
                "name": scheduled.name,
                "workflow_path": scheduled.workflow_path,
                "schedule_type": scheduled.schedule_type,
                "time": scheduled.time,
                "day": scheduled.day,
                "cron_expression": scheduled.cron_expression,
                "enabled": scheduled.enabled,
                "next_run": next_run,
            })

        return jobs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_trigger(
        self,
        schedule_type: str,
        time_str: str,
        day: str,
        cron_expression: str,
    ) -> Any:
        """Build an APScheduler trigger instance from schedule parameters.

        Args:
            schedule_type: Type of schedule.
            time_str: Time in HH:MM format.
            day: Day of week (for weekly).
            cron_expression: Cron expression (for cron type).

        Returns:
            Trigger instance (CronTrigger, IntervalTrigger, or DateTrigger).
        """
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger

        if schedule_type == "once":
            return IntervalTrigger(seconds=5)

        elif schedule_type == "startup":
            return IntervalTrigger(seconds=3)

        elif schedule_type == "daily":
            try:
                hour, minute = time_str.split(":")
                return CronTrigger(hour=int(hour), minute=int(minute))
            except (ValueError, TypeError):
                return CronTrigger(hour=9, minute=0)

        elif schedule_type == "weekly":
            try:
                hour, minute = time_str.split(":")
                day_map = {
                    "mon": "mon", "tue": "tue", "wed": "wed",
                    "thu": "thu", "fri": "fri", "sat": "sat", "sun": "sun",
                    "monday": "mon", "tuesday": "tue", "wednesday": "wed",
                    "thursday": "thu", "friday": "fri", "saturday": "sat",
                    "sunday": "sun",
                }
                day_abbr = day_map.get(day.lower(), day)
                return CronTrigger(
                    day_of_week=day_abbr,
                    hour=int(hour),
                    minute=int(minute),
                )
            except (ValueError, TypeError):
                return CronTrigger(day_of_week="mon", hour=9, minute=0)

        elif schedule_type == "cron" and cron_expression:
            parts = cron_expression.strip().split()
            cron_kwargs: dict[str, Any] = {}

            if len(parts) >= 1:
                cron_kwargs["minute"] = parts[0]
            if len(parts) >= 2:
                cron_kwargs["hour"] = parts[1]
            if len(parts) >= 3:
                cron_kwargs["day"] = parts[2]
            if len(parts) >= 4:
                cron_kwargs["month"] = parts[3]
            if len(parts) >= 5:
                cron_kwargs["day_of_week"] = parts[4]

            return CronTrigger(**cron_kwargs)

        # Default: run once after 5 seconds
        return IntervalTrigger(seconds=5)

    def _execute_workflow_job(self, workflow_path: str, name: str) -> None:
        """Execute a workflow as a scheduled job callback.

        Args:
            workflow_path: Path to the YAML workflow file.
            name: Workflow display name.
        """
        logger.info("Scheduled job running: '%s' (%s)", name, workflow_path)

        try:
            from workflow_orchestrator.models import WorkflowDefinition

            path = Path(workflow_path).expanduser().resolve()
            workflow = WorkflowDefinition.from_yaml(path)
            report = self._engine.execute(workflow, profile=self._profile)

            # Save the report
            report_path = save_report(report)

            if report.success:
                logger.info(
                    "Scheduled workflow '%s' completed successfully: %d/%d steps (%.2fs)",
                    name,
                    report.successful_steps,
                    report.total_steps,
                    report.duration,
                )
            else:
                logger.warning(
                    "Scheduled workflow '%s' failed: %d/%d steps (%.2fs). Error: %s",
                    name,
                    report.successful_steps,
                    report.total_steps,
                    report.duration,
                    report.error,
                )

        except Exception as exc:
            logger.exception(
                "Scheduled workflow '%s' raised an exception: %s",
                name,
                exc,
            )
