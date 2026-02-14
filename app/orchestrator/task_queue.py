import logging
from datetime import datetime
from typing import Optional, Dict, Any
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.database.database import SessionLocal
from app.database.models import Job, JobStatus
from app.monitoring import metrics

logger = logging.getLogger(__name__)


class TaskQueue:
    """Simple APScheduler wrapper for scheduling extraction jobs."""

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self.started = False

    def start(self) -> None:
        if not self.started:
            logger.info("TaskQueue: Starting scheduler")
            self.scheduler.start()
            self.started = True

    def shutdown(self, wait: bool = True) -> None:
        if self.started:
            logger.info("TaskQueue: Shutting down scheduler")
            self.scheduler.shutdown(wait=wait)
            self.started = False

    def schedule_job(
        self,
        job_id: str,
        run_at: Optional[datetime] = None,
        interval_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Schedule a job to run once (`run_at`) or repeatedly (`interval_seconds`)."""
        if run_at and interval_seconds:
            # schedule first at run_at, then as interval
            trigger = DateTrigger(run_date=run_at)
            self.scheduler.add_job(
                self._run_job,
                trigger=trigger,
                args=[job_id, metadata or {}],
                id=f"{job_id}-once",
                replace_existing=True,
            )
            # add interval job
            interval_trigger = IntervalTrigger(seconds=interval_seconds)
            self.scheduler.add_job(
                self._run_job,
                trigger=interval_trigger,
                args=[job_id, metadata or {}],
                id=f"{job_id}-interval",
                replace_existing=True,
            )
            logger.info(f"TaskQueue: Scheduled recurring job {job_id} starting at {run_at}")
            return

        if run_at:
            trigger = DateTrigger(run_date=run_at)
            self.scheduler.add_job(
                self._run_job,
                trigger=trigger,
                args=[job_id, metadata or {}],
                id=str(job_id),
                replace_existing=True,
            )
            logger.info(f"TaskQueue: Scheduled one-off job {job_id} at {run_at}")
            return

        if interval_seconds:
            trigger = IntervalTrigger(seconds=interval_seconds)
            self.scheduler.add_job(
                self._run_job,
                trigger=trigger,
                args=[job_id, metadata or {}],
                id=str(job_id),
                replace_existing=True,
            )
            logger.info(f"TaskQueue: Scheduled interval job {job_id} every {interval_seconds}s")
            return

        raise ValueError("Either run_at or interval_seconds must be provided")

    def remove_job(self, job_id: str) -> None:
        try:
            self.scheduler.remove_job(str(job_id))
            logger.info(f"TaskQueue: Removed job {job_id}")
        except Exception:
            # ignore if job not found
            logger.debug(f"TaskQueue: No job to remove for {job_id}")

    async def _run_job(self, job_id: str, metadata: Dict[str, Any]) -> None:
        """Internal runner executed by APScheduler."""
        logger.info(f"TaskQueue: Executing scheduled job {job_id}")
        start_ts = None
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.warning(f"TaskQueue: Job {job_id} not found in DB")
                return

            # start metrics + update job status
            source_name = job.source_name or metadata.get("source", "unknown")
            start_ts = metrics.job_start(source_name)

            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            db.add(job)
            db.commit()

            # Import here to avoid circular imports
            from app.extractors.engine import ExtractionEngine

            engine = ExtractionEngine(db)
            try:
                result = await engine.extract_from_all(job_id, job.source_name, job.source_name)

                job.status = JobStatus.SUCCESS
                job.completed_at = datetime.utcnow()
                job.result_data = result
                db.add(job)
                db.commit()
                logger.info(f"TaskQueue: Job {job_id} completed successfully")
                # metrics: success
                try:
                    metrics.job_finish(source_name, "success", start_ts or time.time())
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"TaskQueue: Job {job_id} failed - {e}")
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                db.add(job)
                db.commit()
                # metrics: failed
                try:
                    metrics.job_finish(source_name, "failed", start_ts or time.time())
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"TaskQueue: Runner error for job {job_id} - {e}")
        finally:
            db.close()
