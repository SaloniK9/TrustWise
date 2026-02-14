"""
Celery Tasks for TrustWise

Distributed extraction tasks that can be executed across multiple workers.

Tasks:
- extract_web: Parallel web scraping
- extract_research: Research API queries
- extract_vector: Vector database searches
- process_extraction: Orchestrate all extractors
- schedule_periodic_extraction: Recurring extractions
"""

import logging
from uuid import UUID
from celery import shared_task, Task
from app.celery_config import app
from app.database.database import SessionLocal
from app.database.models import Job, JobStatus
from app.extractors.engine import ExtractionEngine
from app.monitoring import metrics

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Success callback."""
        logger.info(f"Task {task_id} succeeded")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback."""
        logger.error(f"Task {task_id} failed: {exc}", exc_info=einfo)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Retry callback."""
        logger.warning(f"Task {task_id} retrying due to: {exc}")


@shared_task(bind=True, base=DatabaseTask)
def extract_web(self, job_id: str, query: str):
    """
    Extract data from web sources.
    
    Args:
        job_id: UUID of the job
        query: Search query
        
    Returns:
        Extraction result
    """
    logger.info(f"Starting web extraction for job {job_id}")
    db = SessionLocal()
    
    try:
        engine = ExtractionEngine(db)
        result = self.apply_async(
            extract_by_type.s("web", job_id, query),
            queue="extraction.web",
        ).get()
        return result
    except Exception as e:
        logger.error(f"Web extraction failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


@shared_task(bind=True, base=DatabaseTask)
def extract_research(self, job_id: str, query: str):
    """
    Extract data from research APIs.
    
    Args:
        job_id: UUID of the job
        query: Search query
        
    Returns:
        Extraction result
    """
    logger.info(f"Starting research extraction for job {job_id}")
    db = SessionLocal()
    
    try:
        engine = ExtractionEngine(db)
        result = self.apply_async(
            extract_by_type.s("research", job_id, query),
            queue="extraction.research",
        ).get()
        return result
    except Exception as e:
        logger.error(f"Research extraction failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


@shared_task(bind=True, base=DatabaseTask)
def extract_vector(self, job_id: str, query: str):
    """
    Extract data from vector databases.
    
    Args:
        job_id: UUID of the job
        query: Search query
        
    Returns:
        Extraction result
    """
    logger.info(f"Starting vector extraction for job {job_id}")
    db = SessionLocal()
    
    try:
        engine = ExtractionEngine(db)
        result = self.apply_async(
            extract_by_type.s("vector", job_id, query),
            queue="extraction.vector",
        ).get()
        return result
    except Exception as e:
        logger.error(f"Vector extraction failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


@shared_task(bind=True, base=DatabaseTask)
def extract_by_type(self, extractor_type: str, job_id: str, query: str):
    """
    Extract from specific extractor type.
    
    Args:
        extractor_type: Type of extractor (web, research, vector)
        job_id: UUID of the job
        query: Search query
        
    Returns:
        Extraction result
    """
    logger.info(f"Extracting from {extractor_type} for job {job_id}")
    db = SessionLocal()
    
    try:
        # Get job and update status
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return {"status": "failed", "error": "Job not found"}
        
        job.status = JobStatus.RUNNING
        db.commit()
        
        # Run extraction
        engine = ExtractionEngine(db)
        result = engine.extract_by_type(UUID(job_id), extractor_type, query)
        
        logger.info(f"Extraction complete for {extractor_type}: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()


@shared_task(bind=True, base=DatabaseTask)
def process_extraction(self, job_id: str, source_name: str, query: str = None):
    """
    Orchestrate all extractions for a job in parallel.
    
    This task distributes work across web, research, and vector extractors.
    
    Args:
        job_id: UUID of the job
        source_name: Name of data source
        query: Search query (defaults to source_name)
        
    Returns:
        Aggregated results from all extractors
    """
    logger.info(f"Starting parallel extraction for job {job_id}")
    
    query = query or source_name
    
    # Dispatch to all extractors in parallel
    group = app.group(
        extract_web.s(job_id, query),
        extract_research.s(job_id, query),
        extract_vector.s(job_id, query),
    )
    
    # Execute and collect results
    chord_callback = aggregate_results.s(job_id)
    result = app.chord(group)(chord_callback)
    
    logger.info(f"Extraction tasks dispatched for job {job_id}")
    return result.get()


@shared_task(bind=True, base=DatabaseTask)
def aggregate_results(self, results: list, job_id: str):
    """
    Aggregate results from all extractors.
    
    Args:
        results: List of extraction results
        job_id: UUID of the job
        
    Returns:
        Aggregated extraction result
    """
    logger.info(f"Aggregating results for job {job_id}")
    db = SessionLocal()
    
    try:
        # Update job status
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"status": "failed", "error": "Job not found"}
        
        # Count successes
        successful = sum(
            1 for r in results if isinstance(r, dict) and r.get("status") == "success"
        )
        total_extracted = sum(
            r.get("count", 0) for r in results if isinstance(r, dict)
        )
        
        if successful > 0:
            job.status = JobStatus.SUCCESS
            logger.info(f"Job {job_id} succeeded with {successful} sources")
        else:
            job.status = JobStatus.FAILED
            logger.error(f"Job {job_id} failed - no successful extractions")
        
        db.commit()
        
        metrics.job_finish(job.source_name, job.status.value, metrics.time.time())
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "successful_extractors": successful,
            "total_extracted": total_extracted,
            "results": results,
        }
    
    except Exception as e:
        logger.error(f"Aggregation failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


@shared_task(bind=True)
def schedule_periodic_extraction(self, source_name: str, query: str = None):
    """
    Scheduled task for periodic extractions.
    
    Called on a schedule (e.g., every hour) to extract from a specific source.
    
    Args:
        source_name: Name of source to extract from
        query: Search query (defaults to source_name)
        
    Returns:
        Scheduled extraction task
    """
    logger.info(f"Periodic extraction task triggered for {source_name}")
    
    from uuid import uuid4
    from datetime import datetime
    
    db = SessionLocal()
    
    try:
        # Create job record
        job = Job(
            source_name=source_name,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Start extraction
        logger.info(f"Created periodic extraction job {job.id}")
        
        result = process_extraction.delay(
            str(job.id),
            source_name,
            query or source_name,
        )
        
        return {"job_id": str(job.id), "task_id": result.id}
    
    except Exception as e:
        logger.error(f"Periodic extraction failed: {e}", exc_info=True)
        raise
    finally:
        db.close()


# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    "extract-research-hourly": {
        "task": "app.tasks.schedule_periodic_extraction",
        "schedule": 3600.0,  # Every hour
        "args": ("research", "machine learning"),
    },
    "extract-web-hourly": {
        "task": "app.tasks.schedule_periodic_extraction",
        "schedule": 3600.0,
        "args": ("web", None),
    },
    "extract-vector-disabled": {
        # Vector DB periodic extraction disabled by default
        # Enable if needed for specific use case
        "task": "app.tasks.schedule_periodic_extraction",
        "schedule": 7200.0,  # Every 2 hours
        "args": ("vector", None),
        "enabled": False,
    },
}
