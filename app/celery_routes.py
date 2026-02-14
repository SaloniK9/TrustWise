"""
Celery Task Integration for FastAPI

This module shows how to integrate Celery with FastAPI endpoints
for asynchronous job processing.

Methods to dispatch tasks to Celery workers for parallel processing.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Job, JobStatus
from app.tasks import process_extraction, extract_by_type
from datetime import datetime

router = APIRouter(prefix="/api/v1", tags=["celery"])


@router.post("/jobs/{job_id}/extract/async")
async def start_extraction_async(
    job_id: UUID,
    query: str = "",
    db: Session = Depends(get_db),
):
    """
    Start async extraction using Celery workers.
    
    Returns immediately with task ID instead of waiting for completion.
    
    Args:
        job_id: UUID of the job
        query: Search query
        db: Database session
        
    Returns:
        Task ID for monitoring progress
    """
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    try:
        # Start async extraction task
        query = query or job.source_name
        task = process_extraction.delay(
            str(job_id),
            job.source_name,
            query,
        )
        
        return {
            "job_id": str(job_id),
            "task_id": task.id,
            "status": "processing",
            "message": "Extraction started asynchronously. Check status with task ID.",
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Get status of a Celery task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Task state, result, and progress
    """
    from app.celery_config import app
    
    try:
        task = app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": task.status,
            "result": task.result if task.successful() else None,
            "error": str(task.info) if task.failed() else None,
            "progress": task.info if isinstance(task.info, dict) else {},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/extract/by-type/async")
async def start_extraction_by_type_async(
    job_id: UUID,
    extractor_type: str,
    query: str = "",
    db: Session = Depends(get_db),
):
    """
    Start async extraction from specific extractor using Celery.
    
    Args:
        job_id: UUID of the job
        extractor_type: Type of extractor (web, research, vector)
        query: Search query
        db: Database session
        
    Returns:
        Task ID for monitoring
    """
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    if extractor_type not in ["web", "research", "vector"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid extractor type. Must be: web, research, or vector",
        )
    
    try:
        query = query or job.source_name
        
        # Route to appropriate extractor queue
        if extractor_type == "web":
            task = extract_by_type.apply_async(
                args=(extractor_type, str(job_id), query),
                queue="extraction.web",
            )
        elif extractor_type == "research":
            task = extract_by_type.apply_async(
                args=(extractor_type, str(job_id), query),
                queue="extraction.research",
            )
        else:  # vector
            task = extract_by_type.apply_async(
                args=(extractor_type, str(job_id), query),
                queue="extraction.vector",
            )
        
        return {
            "job_id": str(job_id),
            "extractor": extractor_type,
            "task_id": task.id,
            "status": "queued",
            "message": f"Extraction queued on {extractor_type} worker",
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workers/stats")
async def get_worker_stats():
    """
    Get statistics from all active workers.
    
    Returns:
        Worker names, task counts, and status
    """
    from app.celery_config import app
    
    try:
        inspector = app.control.inspect()
        
        active_tasks = inspector.active()
        registered_tasks = inspector.registered()
        stats = inspector.stats()
        
        return {
            "active_workers": len(stats or {}),
            "active_tasks": sum(
                len(tasks) for tasks in (active_tasks or {}).values()
            ),
            "workers": {
                name: {
                    "status": "active",
                    "active_tasks": len(active_tasks.get(name, [])),
                    "registered_tasks": len(registered_tasks.get(name, [])),
                    "pool": stats.get(name, {}).get("pool", {}),
                }
                for name in (stats or {}).keys()
            },
        }
    
    except Exception as e:
        return {"error": str(e), "message": "Could not retrieve worker stats"}


@router.post("/workers/reload-tasks")
async def reload_worker_tasks():
    """
    Signal all workers to reload task definitions.
    
    Useful after deploying code changes.
    
    Returns:
        Confirmation of reload signal
    """
    from app.celery_config import app
    
    try:
        app.control.pool_restart()
        return {"status": "success", "message": "Worker pool restart signal sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/purge/{queue}")
async def purge_queue(queue: str):
    """
    Purge all tasks from a queue.
    
    WARNING: This will discard all pending tasks in the queue.
    
    Args:
        queue: Queue name (extraction.web, extraction.research, extraction.vector, default)
        
    Returns:
        Confirmation and task count
    """
    from app.celery_config import app
    
    valid_queues = ["extraction.web", "extraction.research", "extraction.vector", "default"]
    if queue not in valid_queues:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid queue. Must be one of: {valid_queues}",
        )
    
    try:
        # Get task count before purge
        inspector = app.control.inspect()
        active = inspector.active()
        
        task_count = sum(
            len(tasks) for tasks in (active or {}).values()
        )
        
        # Purge queue
        from kombu import Connection
        
        with Connection(app.connection()) as conn:
            conn.default_channel.queue_purge(queue)
        
        return {
            "status": "success",
            "queue": queue,
            "tasks_purged": task_count,
            "message": f"Purged {task_count} tasks from queue {queue}",
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
