"""
Extraction Engine - Orchestrates parallel extraction from multiple data sources.

Coordinates WebScraper, ResearchAPIClient, and VectorDatabase with:
- Parallel execution via asyncio.gather()
- Automatic fallback on individual failures
- Result aggregation and validation
- Job status updates
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.extractors.base import BaseExtractor
from app.extractors.web_scraper import WebScraper
from app.extractors.vector_db import VectorDatabase
from app.extractors.research_api import ResearchAPIClient
from app.extractors.data_storage import DataStorage, DataValidator
from app.database.models import Job, JobStatus
from app.monitoring import metrics

logger = logging.getLogger(__name__)


class ExtractionEngine:
    """
    Orchestrates parallel data extraction from multiple sources.
    
    Manages:
    - WebScraper (HTTP + BeautifulSoup)
    - ResearchAPIClient (ArXiv, IEEE)
    - VectorDatabase (Chroma, Pinecone, Weaviate)
    
    Features:
    - Parallel execution with asyncio.gather()
    - Per-extractor error handling (one failure doesn't block others)
    - Result aggregation
    - Data validation and storage
    - Health monitoring
    """
    
    # Default per-extractor timeouts (seconds)
    TIMEOUTS = {
        "web": 10.0,
        "research": 15.0,
        "vector": 5.0,
    }
    
    def __init__(self, db: Session):
        """Initialize extraction engine with database session."""
        self.db = db
        self.web_scraper = WebScraper()
        self.research_api = ResearchAPIClient()
        self.vector_db = VectorDatabase()
        self.validator = DataValidator()
        self.storage = DataStorage(db)
        logger.info("ExtractionEngine initialized")
    
    async def extract_from_all(
        self,
        job_id: UUID,
        source_name: str,
        query: str,
        parallel: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract data from all available sources.
        
        Args:
            job_id: UUID of the job
            source_name: Name of data source (for context)
            query: Search/extraction query
            parallel: Whether to run extractors in parallel (default: True)
            
        Returns:
            Aggregated extraction result with status and extracted data counts
        """
        logger.info(f"Starting extraction from all sources for job {job_id} (query: {query})")
        
        # Update job status to running
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.RUNNING
            self.db.commit()
        
        start_ts = metrics.job_start(source_name)
        results = {}
        
        try:
            if parallel:
                # Run all extractors in parallel
                results = await self._run_all_parallel(job_id, query)
            else:
                # Run extractors sequentially
                results = await self._run_all_sequential(job_id, query)
            
            # Aggregate results
            total_extracted = sum(r.get("count", 0) for r in results.values())
            success_count = sum(1 for r in results.values() if r.get("status") == "success")
            
            logger.info(
                f"Extraction complete for job {job_id}: "
                f"{success_count} sources succeeded, {total_extracted} items extracted"
            )
            
            # Update job status to success
            if job:
                job.status = JobStatus.SUCCESS
                self.db.commit()
            
            metrics.job_finish(source_name, "success", start_ts)
            
            return {
                "job_id": str(job_id),
                "status": "success",
                "sources_succeeded": success_count,
                "total_extracted": total_extracted,
                "results": results,
            }
        
        except Exception as e:
            logger.error(f"Extraction failed for job {job_id}: {e}", exc_info=True)
            
            # Update job status to failed
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                self.db.commit()
            
            metrics.job_finish(source_name, "failed", start_ts)
            
            return {
                "job_id": str(job_id),
                "status": "failed",
                "error": str(e),
                "results": results,
            }
    
    async def extract_by_type(
        self,
        job_id: UUID,
        extractor_type: str,
        query: str,
    ) -> Dict[str, Any]:
        """
        Extract from a specific extractor type.
        
        Args:
            job_id: UUID of the job
            extractor_type: Type of extractor (web, research, vector)
            query: Search/extraction query
            
        Returns:
            Extraction result with status and extracted data
        """
        logger.info(f"Starting extraction from {extractor_type} for job {job_id}")
        
        if extractor_type not in self.TIMEOUTS:
            return {
                "job_id": str(job_id),
                "status": "failed",
                "error": f"Unknown extractor type: {extractor_type}. "
                         f"Valid types: {list(self.TIMEOUTS.keys())}",
            }
        
        timeout = self.TIMEOUTS[extractor_type]
        
        try:
            result = await asyncio.wait_for(
                self._run_single_extractor(job_id, extractor_type, query),
                timeout=timeout,
            )
            logger.info(f"{extractor_type} extraction succeeded: {result.get('count', 0)} items")
            return result
        
        except asyncio.TimeoutError:
            error_msg = f"{extractor_type} extraction timed out after {timeout}s"
            logger.error(error_msg)
            return {
                "job_id": str(job_id),
                "extractor": extractor_type,
                "status": "timeout",
                "error": error_msg,
            }
        
        except Exception as e:
            logger.error(f"{extractor_type} extraction failed: {e}", exc_info=True)
            return {
                "job_id": str(job_id),
                "extractor": extractor_type,
                "status": "failed",
                "error": str(e),
            }
    
    async def _run_all_parallel(
        self,
        job_id: UUID,
        query: str,
    ) -> Dict[str, Any]:
        """Run all extractors in parallel."""
        tasks = {
            "web": asyncio.create_task(
                self._run_with_timeout(job_id, "web", query)
            ),
            "research": asyncio.create_task(
                self._run_with_timeout(job_id, "research", query)
            ),
            "vector": asyncio.create_task(
                self._run_with_timeout(job_id, "vector", query)
            ),
        }
        
        results = {}
        for extractor_type, task in tasks.items():
            try:
                results[extractor_type] = await task
            except Exception as e:
                logger.error(f"Task for {extractor_type} failed: {e}")
                results[extractor_type] = {
                    "status": "failed",
                    "error": str(e),
                    "count": 0,
                }
        
        return results
    
    async def _run_all_sequential(
        self,
        job_id: UUID,
        query: str,
    ) -> Dict[str, Any]:
        """Run all extractors sequentially."""
        results = {}
        for extractor_type in ["web", "research", "vector"]:
            try:
                results[extractor_type] = await self._run_with_timeout(
                    job_id, extractor_type, query
                )
            except Exception as e:
                logger.error(f"Sequential extraction for {extractor_type} failed: {e}")
                results[extractor_type] = {
                    "status": "failed",
                    "error": str(e),
                    "count": 0,
                }
        
        return results
    
    async def _run_with_timeout(
        self,
        job_id: UUID,
        extractor_type: str,
        query: str,
    ) -> Dict[str, Any]:
        """Run a single extractor with timeout."""
        timeout = self.TIMEOUTS.get(extractor_type, 10.0)
        
        try:
            result = await asyncio.wait_for(
                self._run_single_extractor(job_id, extractor_type, query),
                timeout=timeout,
            )
            return result
        except asyncio.TimeoutError:
            error_msg = f"{extractor_type} timed out after {timeout}s"
            logger.warning(error_msg)
            metrics.increment_tasks_failed()
            return {
                "extractor": extractor_type,
                "status": "timeout",
                "error": error_msg,
                "count": 0,
            }
    
    async def _run_single_extractor(
        self,
        job_id: UUID,
        extractor_type: str,
        query: str,
    ) -> Dict[str, Any]:
        """Run a single extractor and store results."""
        logger.debug(f"Running {extractor_type} extractor with query: {query}")
        
        try:
            # Select extractor
            if extractor_type == "web":
                extractor = self.web_scraper
            elif extractor_type == "research":
                extractor = self.research_api
            elif extractor_type == "vector":
                extractor = self.vector_db
            else:
                return {
                    "extractor": extractor_type,
                    "status": "failed",
                    "error": f"Unknown extractor: {extractor_type}",
                    "count": 0,
                }
            
            # Run extraction
            extraction_result = await extractor.extract(query)
            
            if not extraction_result.get("status") == "success":
                logger.warning(
                    f"{extractor_type} extraction returned non-success status: "
                    f"{extraction_result.get('status')}"
                )
                metrics.increment_tasks_failed()
                return {
                    "extractor": extractor_type,
                    "status": extraction_result.get("status", "failed"),
                    "error": extraction_result.get("error", "Unknown error"),
                    "count": 0,
                }
            
            # Validate extracted data
            data = extraction_result.get("data", [])
            validated_count = 0
            
            for item in data:
                try:
                    # Validate structure
                    validated_item = self.validator.validate(item)
                    
                    # Normalize data
                    normalized_item = self.validator.normalize(validated_item)
                    
                    # Store in database
                    await self.storage.store(
                        job_id=job_id,
                        source=extractor_type,
                        data=normalized_item,
                        trust_score=extraction_result.get("trust_score", 0.5),
                    )
                    
                    validated_count += 1
                
                except Exception as item_error:
                    logger.warning(f"Item validation failed for {extractor_type}: {item_error}")
                    continue
            
            metrics.increment_tasks_dispatched()
            
            logger.info(
                f"{extractor_type} extraction stored {validated_count}/{len(data)} items"
            )
            
            return {
                "extractor": extractor_type,
                "status": "success",
                "count": validated_count,
                "total_items": len(data),
                "trust_score": extraction_result.get("trust_score", 0.5),
            }
        
        except Exception as e:
            logger.error(f"Single extractor {extractor_type} failed: {e}", exc_info=True)
            metrics.increment_tasks_failed()
            return {
                "extractor": extractor_type,
                "status": "failed",
                "error": str(e),
                "count": 0,
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all extractors.
        
        Returns:
            Health status of each extractor
        """
        logger.debug("Running health check on all extractors")
        
        checks = {
            "web": asyncio.create_task(self.web_scraper.validate()),
            "research": asyncio.create_task(self.research_api.validate()),
            "vector": asyncio.create_task(self.vector_db.validate()),
        }
        
        results = {}
        for extractor_type, task in checks.items():
            try:
                is_healthy = await asyncio.wait_for(task, timeout=5.0)
                results[extractor_type] = {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "available": is_healthy,
                }
            except asyncio.TimeoutError:
                logger.warning(f"{extractor_type} health check timed out")
                results[extractor_type] = {
                    "status": "timeout",
                    "available": False,
                }
            except Exception as e:
                logger.warning(f"{extractor_type} health check failed: {e}")
                results[extractor_type] = {
                    "status": "error",
                    "available": False,
                    "error": str(e),
                }
        
        # Overall status
        available_count = sum(
            1 for r in results.values() if r.get("available", False)
        )
        overall_status = "healthy" if available_count >= 2 else "degraded"
        
        return {
            "status": overall_status,
            "extractors": results,
            "available_count": available_count,
            "total_count": len(results),
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources (close HTTP connections, etc)."""
        logger.info("Cleaning up extraction engine resources")
        try:
            await self.web_scraper.close()
        except Exception as e:
            logger.warning(f"Error closing web scraper: {e}")
        
        try:
            await self.research_api.close()
        except Exception as e:
            logger.warning(f"Error closing research API: {e}")
