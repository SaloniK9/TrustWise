"""
Data validation and storage for extracted data.

Handles:
- Pydantic validation of extracted data
- Storage in ExtractedData table
- Data quality metrics
- Normalization and cleanup
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from uuid import uuid4

from app.database.models import ExtractedData, Job, JobStatus

logger = logging.getLogger(__name__)


class ExtractedDataSchema(BaseModel):
    """Schema for validated extracted data."""

    source: str = Field(..., description="Source name")
    data: Dict[str, Any] = Field(..., description="Extracted data")
    trust_score: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score 0-1",
    )
    extracted_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Extraction timestamp",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    @validator("trust_score")
    def validate_trust_score(cls, v):
        """Ensure trust score is valid."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("trust_score must be between 0 and 1")
        return v

    class Config:
        """Pydantic config."""
        from_attributes = True


class DataValidator:
    """Validator for extracted data."""

    def __init__(self, db: Session):
        """
        Initialize validator.

        Args:
            db: Database session
        """
        self.db = db

    def validate(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate extracted data.

        Args:
            data: Data to validate

        Returns:
            (is_valid, error_message)
        """
        try:
            # Must have required fields
            if "source" not in data:
                return False, "Missing 'source' field"

            if "data" not in data:
                return False, "Missing 'data' field"

            # Data must be dict or list
            item_data = data["data"]
            if not isinstance(item_data, (dict, list)):
                return False, "Data must be dict or list"

            # Trust score optional but must be valid
            if "trust_score" in data:
                trust_score = data["trust_score"]
                if not isinstance(trust_score, (int, float)):
                    return False, "trust_score must be numeric"
                if not 0.0 <= trust_score <= 1.0:
                    return False, "trust_score must be between 0 and 1"

            return True, None

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, str(e)

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize extracted data.

        Args:
            data: Raw data

        Returns:
            Normalized data
        """
        try:
            source = str(data.get("source", "unknown")).strip()
            item_data = data.get("data", {})
            trust_score = float(data.get("trust_score", 0.8))
            extracted_at = data.get("extracted_at") or datetime.utcnow()
            metadata = data.get("metadata", {})

            # Clean data
            if isinstance(item_data, dict):
                # Remove None values
                item_data = {k: v for k, v in item_data.items() if v is not None}
            elif isinstance(item_data, list):
                # Remove empty strings
                if all(isinstance(item, str) for item in item_data):
                    item_data = [item.strip() for item in item_data if item.strip()]

            return {
                "source": source,
                "data": item_data,
                "trust_score": min(max(trust_score, 0.0), 1.0),  # Clamp to 0-1
                "extracted_at": extracted_at,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Normalization error: {e}")
            return data

    def calculate_quality(self, data: Dict[str, Any]) -> float:
        """
        Calculate data quality score.

        Args:
            data: Data to analyze

        Returns:
            Quality score 0-1
        """
        score = 0.8  # Base score

        # Boost for trust score
        if "trust_score" in data:
            score = score * 0.5 + data["trust_score"] * 0.5

        # Reduce for sparse data
        item_data = data.get("data", {})
        if isinstance(item_data, dict):
            if len(item_data) < 2:
                score *= 0.8
        elif isinstance(item_data, list):
            if len(item_data) < 3:
                score *= 0.8

        # Reduce for missing metadata
        if not data.get("metadata"):
            score *= 0.95

        return max(min(score, 1.0), 0.0)


class DataStorage:
    """Storage handler for extracted data."""

    def __init__(self, db: Session):
        """
        Initialize storage.

        Args:
            db: Database session
        """
        self.db = db
        self.validator = DataValidator(db)

    async def store(
        self,
        job_id: str,
        extraction_result: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """
        Store extracted data.

        Args:
            job_id: Job UUID
            extraction_result: Result from extractor

        Returns:
            (success, error_message)
        """
        try:
            # Validate
            is_valid, error = self.validator.validate(extraction_result)
            if not is_valid:
                logger.error(f"Validation failed: {error}")
                return False, error

            # Normalize
            normalized = self.validator.normalize(extraction_result)

            # Calculate quality
            quality = self.validator.calculate_quality(normalized)

            # Create database record
            extracted_data = ExtractedData(
                id=uuid4(),
                job_id=job_id,
                source=normalized["source"],
                data=normalized["data"],
                extracted_at=normalized["extracted_at"],
                trust_score=normalized["trust_score"],
            )

            self.db.add(extracted_data)
            self.db.commit()

            logger.info(
                f"Stored data from {normalized['source']} "
                f"(quality: {quality:.2%}, trust: {normalized['trust_score']:.2%})"
            )
            return True, None

        except Exception as e:
            self.db.rollback()
            logger.error(f"Storage failed: {e}")
            return False, str(e)

    async def store_batch(
        self,
        job_id: str,
        results: List[Dict[str, Any]],
    ) -> tuple[int, List[str]]:
        """
        Store multiple extraction results.

        Args:
            job_id: Job UUID
            results: List of extraction results

        Returns:
            (stored_count, errors)
        """
        stored_count = 0
        errors = []

        for i, result in enumerate(results):
            success, error = await self.store(job_id, result)
            if success:
                stored_count += 1
            else:
                errors.append(f"Result {i}: {error}")

        logger.info(
            f"Stored {stored_count}/{len(results)} results "
            f"({100*stored_count//len(results)}% success)"
        )
        return stored_count, errors

    async def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None,
        result_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update job status after extraction.

        Args:
            job_id: Job UUID
            status: New status
            error_message: Optional error
            result_data: Optional result data

        Returns:
            True if update succeeded
        """
        try:
            job = self.db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return False

            job.status = status
            job.completed_at = datetime.utcnow()

            if error_message:
                job.error_message = error_message

            if result_data:
                job.result_data = result_data

            self.db.commit()
            logger.info(f"Updated job {job_id} to {status}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"Status update failed: {e}")
            return False
