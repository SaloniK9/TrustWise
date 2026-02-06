"""SQLAlchemy ORM models for TrustWise application."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    DateTime,
    JSON,
    Float,
    Boolean,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SourceType(str, Enum):
    """Source type enumeration."""

    DATABASE = "database"
    VECTOR = "vector"
    WEB = "web"
    RESEARCH = "research"


class Job(Base):
    """Job model for tracking orchestration jobs."""

    __tablename__ = "job"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name = Column(String(255), nullable=False, index=True)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String(1000), nullable=True)
    result_data = Column(JSON, nullable=True)

    # Relationships
    extracted_data = relationship(
        "ExtractedData", back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_job_status_created", "status", "created_at"),
        Index("ix_job_source_created", "source_name", "created_at"),
    )


class ExtractedData(Base):
    """Model for data extracted during job execution."""

    __tablename__ = "extracted_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True), ForeignKey("job.id"), nullable=False, index=True
    )
    source = Column(String(255), nullable=False)
    data = Column(JSON, nullable=False)
    extracted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    trust_score = Column(Float, nullable=False, default=0.0)

    # Relationships
    job = relationship("Job", back_populates="extracted_data")

    __table_args__ = (
        Index("ix_extracted_data_job_created", "job_id", "extracted_at"),
        Index("ix_extracted_data_source", "source"),
    )


class Source(Base):
    """Model for data sources."""

    __tablename__ = "source"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    type = Column(SQLEnum(SourceType), nullable=False)
    trust_score = Column(Float, nullable=False, default=0.5)
    enabled = Column(Boolean, nullable=False, default=True)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
