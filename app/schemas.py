"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Job Status Responses
class JobResponse(BaseModel):
    """Minimal job response (for creation and listing)."""

    id: UUID
    source_name: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ExtractedDataResponse(BaseModel):
    """Response model for extracted data."""

    id: UUID
    source: str
    data: dict
    extracted_at: datetime
    trust_score: float

    class Config:
        from_attributes = True


class JobDetailResponse(BaseModel):
    """Complete job response with extracted data."""

    id: UUID
    source_name: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    data: List[ExtractedDataResponse] = []

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Paginated job list response."""

    total: int
    items: List[JobResponse]
    skip: int
    limit: int


# Job Request Models
class JobCreateRequest(BaseModel):
    """Request model for creating a new job."""

    source_name: str = Field(
        ..., description="Name of the source to query", min_length=1, max_length=255
    )
    priority: int = Field(default=0, description="Job priority (0=normal, higher=more urgent)")
    notify_url: Optional[str] = Field(
        default=None, description="Optional webhook URL for job status notifications"
    )


# Database Health Response
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    database: Optional[str] = None


# Error Response
class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
