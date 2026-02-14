import logging
from datetime import datetime
from uuid import UUID
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.task_queue import TaskQueue
from app.database.database import get_db, engine, SessionLocal
from app.database.models import Base, Job, ExtractedData, JobStatus
from app.schemas import (
    JobCreateRequest,
    JobResponse,
    JobDetailResponse,
    JobListResponse,
    HealthResponse,
    ScheduleRequest,
    ErrorResponse,
)
from app.extractors.engine import ExtractionEngine
from app.monitoring import metrics

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="TrustWise Orchestrator",
    description="Trust-based data orchestration engine",
    version="0.1.0"
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Initialize orchestrator
orchestrator = Orchestrator()

# Initialize Phase 3 task queue
task_queue = TaskQueue()

# Initialize extraction engine (Phase 2)
extraction_engine = None


async def get_extraction_engine(db: Session = Depends(get_db)) -> ExtractionEngine:
    """Get or create extraction engine."""
    global extraction_engine
    if extraction_engine is None:
        extraction_engine = ExtractionEngine(db)
    return extraction_engine


# ============================================================================
# Event Handlers
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("TrustWise starting up...")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}", exc_info=True)
        raise
    # Start task queue scheduler
    try:
        task_queue.start()
    except Exception as e:
        logger.error(f"Failed to start task queue: {e}")

    # Phase 3: create a persistent job record for each trusted source and schedule recurring runs
    try:
        db = SessionLocal()
        # Default recurring interval: 24 hours (in seconds)
        default_interval = 24 * 60 * 60

        # Get per-source intervals if provided in config
        source_intervals = orchestrator.get_sources_with_intervals()

        # Build set of all source names (to ensure we create jobs for sources
        # even if no interval was specified)
        for name in orchestrator.get_source_names():
            # ensure a job record exists for the source
            existing = db.query(Job).filter(Job.source_name == name).first()
            if not existing:
                j = Job(source_name=name, status=JobStatus.PENDING)
                db.add(j)
                db.commit()
                db.refresh(j)
                job_id = str(j.id)
            else:
                job_id = str(existing.id)

            interval = source_intervals.get(name, default_interval)

            # schedule a recurring extraction job (replace existing schedule if present)
            task_queue.schedule_job(job_id, interval_seconds=interval, metadata={"source": name})

        db.close()
        logger.info("Phase 3: Scheduled recurring jobs for trusted sources")
    except Exception as e:
        logger.error(f"Phase 3 scheduling failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("TrustWise shutting down...")
    try:
        task_queue.shutdown()
    except Exception:
        pass


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded."""
    logger.warning(f"Rate limit exceeded: {request.client.host}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please retry after some time."}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )




# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return HealthResponse(
        status="running",
        service="TrustWise Orchestrator",
        version="0.1.0",
        database="connected"
    )


@app.get("/ready", response_model=HealthResponse)
async def readiness(db: Session = Depends(get_db)):
    """Readiness check endpoint with database verification."""
    logger.debug("Readiness check requested")
    try:
        # Test database connection
        db.execute("SELECT 1")
        database_status = "connected"
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        database_status = "disconnected"
        raise HTTPException(status_code=503, detail="Database unavailable")
    
    return HealthResponse(
        status="ready",
        service="TrustWise Orchestrator",
        version="0.1.0",
        database=database_status
    )


@app.get("/live", response_model=HealthResponse)
async def liveness():
    """Liveness probe for Kubernetes/container orchestration.
    
    Returns 200 if app is running, 503 if scheduler is down.
    """
    logger.debug("Liveness check requested")
    
    # Check if scheduler is still running
    if not task_queue.started:
        raise HTTPException(status_code=503, detail="Scheduler not running")
    
    return HealthResponse(
        status="live",
        service="TrustWise Orchestrator",
        version="0.1.0",
        database="n/a"
    )


# ============================================================================
# Job Management Endpoints
# ============================================================================

@app.post("/jobs", response_model=JobResponse, status_code=201)
@limiter.limit("100/minute")
async def create_job(
    request: Request,
    job_request: JobCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new job for data extraction.
    
    Args:
        request: FastAPI request object (for rate limiting)
        job_request: Job creation request
        db: Database session
        
    Returns:
        JobResponse: Created job with ID and status
        
    Raises:
        HTTPException: If source is invalid
    """
    logger.info(f"Creating job for source: {job_request.source_name}")
    
    # Validate source exists
    valid_sources = orchestrator.get_source_names()
    if job_request.source_name not in valid_sources:
        logger.warning(f"Invalid source requested: {job_request.source_name}")
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source: {job_request.source_name}. Available sources: {sorted(list(valid_sources))}"
        )
    
    try:
        # Create job record
        job = Job(
            source_name=job_request.source_name,
            status=JobStatus.PENDING,
            created_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(f"Job created successfully: {job.id}")
        
        return JobResponse(
            id=job.id,
            source_name=job.source_name,
            status=job.status.value,
            created_at=job.created_at
        )
    except Exception as e:
        logger.error(f"Failed to create job: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create job"
        )


@app.get("/jobs/{job_id}", response_model=JobDetailResponse)
@limiter.limit("1000/minute")
async def get_job(
    request: Request,
    job_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get job status and extracted data.
    
    Args:
        job_id: UUID of the job
        db: Database session
        
    Returns:
        JobDetailResponse: Complete job details with extracted data
        
    Raises:
        HTTPException: If job not found
    """
    logger.debug(f"Retrieving job: {job_id}")
    
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        
        if not job:
            logger.warning(f"Job not found: {job_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Get associated extracted data
        extracted_data = db.query(ExtractedData).filter(
            ExtractedData.job_id == job_id
        ).all()
        
        return JobDetailResponse(
            id=job.id,
            source_name=job.source_name,
            status=job.status.value,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            data=[
                {
                    "id": d.id,
                    "source": d.source,
                    "data": d.data,
                    "extracted_at": d.extracted_at,
                    "trust_score": d.trust_score
                }
                for d in extracted_data
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error retrieving job"
        )


@app.get("/jobs", response_model=JobListResponse)
@limiter.limit("1000/minute")
async def list_jobs(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List jobs with optional filtering and pagination.
    
    Args:
        request: FastAPI request object (for rate limiting)
        skip: Number of jobs to skip (for pagination)
        limit: Maximum number of jobs to return (max 100)
        status: Filter by job status (pending, running, success, failed)
        source: Filter by source name
        db: Database session
        
    Returns:
        JobListResponse: List of jobs with pagination info
    """
    logger.debug(f"Listing jobs - skip={skip}, limit={limit}, status={status}, source={source}")
    
    # Validate and normalize limit
    limit = min(limit, 100)  # Max 100 per query
    skip = max(skip, 0)
    
    try:
        query = db.query(Job)
        
        # Apply filters
        filters = []
        if status:
            try:
                job_status = JobStatus(status)
                filters.append(Job.status == job_status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}. Valid values: {[s.value for s in JobStatus]}"
                )
        
        if source:
            filters.append(Job.source_name == source)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # Get total count
        total = query.count()
        
        # Get items with pagination
        items = query.order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
        
        return JobListResponse(
            total=total,
            items=[
                JobResponse(
                    id=job.id,
                    source_name=job.source_name,
                    status=job.status.value,
                    created_at=job.created_at
                )
                for job in items
            ],
            skip=skip,
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error listing jobs"
        )


# ============================================================================
# PHASE 2: Data Extraction Endpoints
# ============================================================================

@app.post("/jobs/{job_id}/extract")
@limiter.limit("50/minute")
async def start_extraction(
    request: Request,
    job_id: UUID,
    query: str = "",
    extractor_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Start data extraction for a job.
    
    Supports multiple extractors:
    - web: Web scraping
    - research: Research API (ArXiv, IEEE)
    - vector: Vector database semantic search
    - None: All extractors (parallel)
    
    Args:
        request: FastAPI request
        job_id: Job UUID
        query: Search query (optional, uses source name if not provided)
        extractor_type: Type of extractor to use (web, research, vector, or None for all)
        db: Database session
        
    Returns:
        Extraction result
    """
    logger.info(f"Starting extraction for job {job_id} (query: {query})")
    
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    try:
        engine = ExtractionEngine(db)
        
        if extractor_type:
            # Run specific extractor
            result = await engine.extract_by_type(
                job_id,
                extractor_type,
                query or job.source_name,
            )
        else:
            # Run all extractors
            result = await engine.extract_from_all(
                job_id,
                job.source_name,
                query or job.source_name,
            )
        
        return result
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/{job_id}/schedule")
@limiter.limit("50/minute")
async def schedule_job_endpoint(
    request: Request,
    job_id: UUID,
    schedule: ScheduleRequest,
    db: Session = Depends(get_db),
):
    """Schedule a job to run at a given time or interval.

    Provides a lightweight scheduler interface for Phase 3.
    """
    logger.info(f"Scheduling job {job_id} - run_at={schedule.run_at} interval={schedule.interval_seconds}")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    try:
        task_queue.schedule_job(
            str(job_id), run_at=schedule.run_at, interval_seconds=schedule.interval_seconds, metadata=schedule.metadata
        )
        return {"job_id": str(job_id), "scheduled": True}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to schedule job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to schedule job")


@app.get("/jobs/{job_id}/extractions")
@limiter.limit("500/minute")
async def get_extractions(
    request: Request,
    job_id: UUID,
    source: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """
    Get extracted data for a job.
    
    Args:
        request: FastAPI request
        job_id: Job UUID
        source: Filter by source (optional)
        skip: Pagination offset
        limit: Results limit
        db: Database session
        
    Returns:
        List of extracted data entries
    """
    logger.debug(f"Retrieving extractions for job {job_id}")
    
    try:
        query = db.query(ExtractedData).filter(ExtractedData.job_id == job_id)
        
        if source:
            query = query.filter(ExtractedData.source == source)
        
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        
        return {
            "job_id": str(job_id),
            "total": total,
            "items": [
                {
                    "id": str(item.id),
                    "source": item.source,
                    "data": item.data,
                    "extracted_at": item.extracted_at.isoformat(),
                    "trust_score": item.trust_score,
                }
                for item in items
            ],
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error retrieving extractions: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving extractions")


@app.get("/extractors/health")
@limiter.limit("100/minute")
async def extractor_health(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Check health of all extractors.
    
    Returns:
        Health status of each extractor
    """
    logger.debug("Extractor health check requested")
    
    try:
        engine = ExtractionEngine(db)
        health = await engine.health_check()
        return health
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint exposed for scraping."""
    try:
        body, content_type = metrics.metrics_as_response()
        return Response(content=body, media_type=content_type)
    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@app.post("/extractors/{extractor_type}/search")
@limiter.limit("200/minute")
async def search_extractor(
    request: Request,
    extractor_type: str,
    query: str,
    db: Session = Depends(get_db),
):
    """
    Direct search on a specific extractor.
    
    Useful for testing or direct queries without creating a job.
    
    Args:
        request: FastAPI request
        extractor_type: web, research, or vector
        query: Search query
        db: Database session
        
    Returns:
        Extraction result
    """
    logger.info(f"Direct search on {extractor_type}: {query}")
    
    try:
        from uuid import uuid4
        engine = ExtractionEngine(db)
        result = await engine.extract_by_type(
            uuid4(),
            extractor_type,
            query,
            {},
        )
        return result
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting TrustWise v0.1.0")
    uvicorn.run(app, host="0.0.0.0", port=8000)