# TrustWise Orchestrator - Implementation Plan

## Overview

**Architectural Philosophy:** Build a production-grade, trust-based data orchestration system using **100% free, open-source software**. No vendor lock-in. Fully reproducible. Designed for reliability, not complexity.

---

## PHASE 0: Environment & Tooling Setup

**Goal:** Establish a clean, reproducible development environment.

**Rationale:** Proper tooling foundation prevents technical debt and ensures team reproducibility.

### Tools & Why
- **Python 3.10+** → Modern async support, type hints
- **VS Code** → Best-in-class Python debugging
- **venv** → Isolated environments, prevents dependency hell
- **Git** → Version control and audit trail

### Tasks

- [ ] **Install Python 3.10+**
  - Verify: `python --version`
  
- [ ] **Create virtual environment**
  ```bash
  python -m venv venv
  venv\Scripts\activate  # Windows
  # or source venv/bin/activate  # Linux/Mac
  ```

- [ ] **Install base dependencies**
  ```bash
  pip install fastapi uvicorn
  ```

- [ ] **Initialize Git repository**
  ```bash
  git init
  git config user.email "your-email@example.com"
  git config user.name "Your Name"
  ```

- [ ] **Create `.gitignore`**
  ```
  venv/
  __pycache__/
  *.pyc
  .env
  .vscode/settings.json
  node_modules/
  dist/
  build/
  *.egg-info/
  ```

- [ ] **Initial commit**
  ```bash
  git add -A
  git commit -m "Initial project setup"
  ```

✅ **Output:** Ready-to-develop environment

---

## PHASE 1: API Framework & Server

**Goal:** Establish a running, self-documenting API server.

**Rationale:** FastAPI provides async support, automatic OpenAPI docs, and validation out-of-the-box—critical for orchestrators handling concurrent requests.

### Tools & Why
- **FastAPI** (MIT License) → Async, fast, validated requests
- **Uvicorn** (BSD) → ASGI server, hot-reload support

### Tasks

- [ ] **Update `app/main.py`** with complete server setup
  ```python
  from fastapi import FastAPI, HTTPException
  from fastapi.responses import JSONResponse
  import logging

  logging.basicConfig(level=logging.INFO)
  logger = logging.getLogger(__name__)

  app = FastAPI(
      title="TrustWise Orchestrator",
      description="Trust-based data orchestration engine",
      version="0.1.0"
  )

  @app.get("/")
  def health_check():
      return {
          "status": "running",
          "service": "TrustWise Orchestrator",
          "version": "0.1.0"
      }

  @app.get("/ready")
  def readiness():
      return {"ready": True}

  if __name__ == "__main__":
      import uvicorn
      uvicorn.run(app, host="0.0.0.0", port=8000)
  ```

- [ ] **Test the server**
  ```bash
  uvicorn app.main:app --reload
  ```
  - Visit: http://localhost:8000
  - View API docs: http://localhost:8000/docs

- [ ] **Create startup/shutdown hooks** (for Phase 6 DB connections)
  ```python
  @app.on_event("startup")
  async def startup_event():
      logger.info("TrustWise starting...")

  @app.on_event("shutdown")
  async def shutdown_event():
      logger.info("TrustWise shutting down...")
  ```

✅ **Output:** Running, documented API server

---

## PHASE 2: Trusted Source Management

**Goal:** Establish a whitelist of trusted data sources with configurable trust scores.

**Rationale:** Security-first approach. Prevent scraping untrusted sources and LLM context pollution.

### Tools & Why
- **YAML** (human-readable, vs JSON)
- **PyYAML** (MIT) → Parse YAML safely
- **Pydantic** (MIT) → Validate source definitions

### Tasks

- [ ] **Install PyYAML**
  ```bash
  pip install pyyaml
  ```

- [ ] **Create `config/trusted_sources.yaml`**
  ```yaml
  trusted_sources:
    
    # Government Sources
    government:
      - name: "PIB Government of India"
        domain: "pib.gov.in"
        category: "government"
        extraction_method: "scrape"
        trust_score: 0.96
        refresh_interval_hours: 12
        
      - name: "Press Information Bureau (English)"
        domain: "pib.org.in"
        category: "government"
        extraction_method: "scrape"
        trust_score: 0.95
        refresh_interval_hours: 12

    # Research & Academic
    academic:
      - name: "ArXiv"
        domain: "arxiv.org"
        category: "research"
        extraction_method: "api"
        trust_score: 0.97
        refresh_interval_hours: 24
        
      - name: "IEEE Xplore"
        domain: "ieeexplore.ieee.org"
        category: "research"
        extraction_method: "api"
        trust_score: 0.96
        refresh_interval_hours: 24

    # Official Standards
    standards:
      - name: "NIST"
        domain: "nist.gov"
        category: "standards"
        extraction_method: "scrape"
        trust_score: 0.99
        refresh_interval_hours: 24

  # Global extraction rules
  extraction_rules:
    default_timeout: 10  # seconds
    default_retries: 3
    user_agent: "TrustWise/1.0 (+https://github.com/yourrepo)"
  ```

- [ ] **Create `app/config/sources.py`** (Pydantic schemas)
  ```python
  from pydantic import BaseModel
  from typing import List, Optional
  import yaml

  class TrustedSource(BaseModel):
      name: str
      domain: str
      category: str
      extraction_method: str
      trust_score: float  # 0.0 to 1.0
      refresh_interval_hours: int
      
      def is_trusted(self, minimum_score: float = 0.8) -> bool:
          return self.trust_score >= minimum_score

  class SourcesConfig(BaseModel):
      trusted_sources: dict
      extraction_rules: dict

  def load_sources_config(path: str = "config/trusted_sources.yaml") -> SourcesConfig:
      with open(path) as f:
          data = yaml.safe_load(f)
      return SourcesConfig(**data)
  ```

- [ ] **Add source validation endpoint**
  ```python
  @app.get("/sources")
  def list_trusted_sources():
      config = load_sources_config()
      return {
          "total": sum(len(v) for v in config.trusted_sources.values()),
          "sources": config.trusted_sources
      }
  ```

- [ ] **Test loading sources**
  ```python
  config = load_sources_config()
  print(config.trusted_sources)
  ```

✅ **Output:** Whitelisted, validated trusted sources

---

## PHASE 3: Orchestrator Core

**Goal:** Build the central controller that manages job lifecycle and dispatch.

**Rationale:** The orchestrator is the "brain" — it decides what to do, when, and validates that the system is behaving correctly.

### Tools & Why
- **Pure Python** → No external dependencies needed
- **typing** (stdlib) → Type hints for clarity
- **logging** (stdlib) → Central observability

### Tasks

- [ ] **Create `app/orchestrator/models.py`** (Job models)
  ```python
  from enum import Enum
  from dataclasses import dataclass
  from datetime import datetime
  from typing import Dict, Any

  class JobStatus(str, Enum):
      CREATED = "created"
      QUEUED = "queued"
      RUNNING = "running"
      SUCCESS = "success"
      FAILED = "failed"

  @dataclass
  class Job:
      job_id: str
      status: JobStatus
      source_name: str
      created_at: datetime
      started_at: Optional[datetime] = None
      completed_at: Optional[datetime] = None
      result: Optional[Dict[str, Any]] = None
      error: Optional[str] = None
  ```

- [ ] **Create `app/orchestrator/orchestrator.py`** (Main controller)
  ```python
  import logging
  import uuid
  from datetime import datetime
  from typing import Dict, Optional
  from app.orchestrator.models import Job, JobStatus

  logger = logging.getLogger(__name__)

  class Orchestrator:
      def __init__(self):
          self.jobs: Dict[str, Job] = {}
          logger.info("Orchestrator initialized")

      def create_job(self, source_name: str) -> Job:
          job = Job(
              job_id=str(uuid.uuid4()),
              status=JobStatus.CREATED,
              source_name=source_name,
              created_at=datetime.utcnow()
          )
          self.jobs[job.job_id] = job
          logger.info(f"Job created: {job.job_id} for source {source_name}")
          return job

      def start_job(self, job_id: str) -> None:
          job = self.jobs.get(job_id)
          if not job:
              raise ValueError(f"Job {job_id} not found")
          job.status = JobStatus.RUNNING
          job.started_at = datetime.utcnow()
          logger.info(f"Job started: {job_id}")

      def complete_job(self, job_id: str, result: Dict) -> None:
          job = self.jobs.get(job_id)
          if not job:
              raise ValueError(f"Job {job_id} not found")
          job.status = JobStatus.SUCCESS
          job.completed_at = datetime.utcnow()
          job.result = result
          logger.info(f"Job completed: {job_id}")

      def fail_job(self, job_id: str, error: str) -> None:
          job = self.jobs.get(job_id)
          if not job:
              raise ValueError(f"Job {job_id} not found")
          job.status = JobStatus.FAILED
          job.completed_at = datetime.utcnow()
          job.error = error
          logger.error(f"Job failed: {job_id} - {error}")

      def get_job(self, job_id: str) -> Optional[Job]:
          return self.jobs.get(job_id)

      def get_all_jobs(self) -> Dict[str, Job]:
          return self.jobs
  ```

- [ ] **Integrate into FastAPI** (`app/main.py`)
  ```python
  from app.orchestrator.orchestrator import Orchestrator

  orchestrator = Orchestrator()

  @app.post("/jobs")
  def create_extraction_job(source_name: str):
      job = orchestrator.create_job(source_name)
      return {
          "job_id": job.job_id,
          "status": job.status.value,
          "source": source_name
      }

  @app.get("/jobs/{job_id}")
  def get_job_status(job_id: str):
      job = orchestrator.get_job(job_id)
      if not job:
          raise HTTPException(status_code=404, detail="Job not found")
      return {
          "job_id": job.job_id,
          "status": job.status.value,
          "source": job.source_name,
          "result": job.result,
          "error": job.error
      }
  ```

✅ **Output:** Central orchestrator with job lifecycle management

---

## PHASE 4: Data Extraction

**Goal:** Safely extract data from trusted sources using multiple methods.

**Rationale:** Extraction is where most failures happen — timeouts, 429s, parse errors. Must be robust and logged.

### Tools & Why
- **Requests** (Apache 2.0) → HTTP client, battle-tested
- **BeautifulSoup4** (MIT) → HTML parsing, forgiving
- **httpx** (BSD) → Async HTTP, optional but better

### Tasks

- [ ] **Install extractors**
  ```bash
  pip install requests beautifulsoup4 httpx
  ```

- [ ] **Create `app/extractors/__init__.py`** (empty)

- [ ] **Create `app/extractors/web_scraper.py`**
  ```python
  import logging
  import requests
  from bs4 import BeautifulSoup
  from typing import Dict, Optional
  from datetime import datetime

  logger = logging.getLogger(__name__)

  class WebScraper:
      def __init__(self, timeout: int = 10, retries: int = 3):
          self.timeout = timeout
          self.retries = retries
          self.user_agent = "TrustWise/1.0 (+https://github.com/yourrepo)"

      def fetch(self, url: str) -> Optional[Dict]:
          """
          Safely fetch and parse HTML from a URL.
          
          Returns:
              {
                  "url": str,
                  "status_code": int,
                  "html": str,
                  "fetched_at": datetime,
                  "success": bool
              }
          """
          
          headers = {"User-Agent": self.user_agent}
          
          for attempt in range(self.retries):
              try:
                  logger.info(f"Fetching {url} (attempt {attempt + 1}/{self.retries})")
                  response = requests.get(
                      url,
                      headers=headers,
                      timeout=self.timeout,
                      allow_redirects=True
                  )
                  response.raise_for_status()
                  
                  logger.info(f"Successfully fetched {url}")
                  
                  return {
                      "url": url,
                      "status_code": response.status_code,
                      "html": response.text,
                      "fetched_at": datetime.utcnow().isoformat(),
                      "success": True
                  }
                  
              except requests.exceptions.Timeout:
                  logger.warning(f"Timeout on {url} (attempt {attempt + 1})")
              except requests.exceptions.HTTPError as e:
                  logger.error(f"HTTP Error {e.response.status_code} on {url}")
                  return {
                      "url": url,
                      "status_code": e.response.status_code,
                      "html": None,
                      "fetched_at": datetime.utcnow().isoformat(),
                      "success": False,
                      "error": str(e)
                  }
              except Exception as e:
                  logger.error(f"Error fetching {url}: {e}")
          
          return {
              "url": url,
              "html": None,
              "success": False,
              "error": "Max retries exceeded"
          }

      def extract_text(self, html: str) -> Optional[str]:
          """Strip HTML and return clean text."""
          try:
              soup = BeautifulSoup(html, "html.parser")
              
              # Remove script and style elements
              for script in soup(["script", "style"]):
                  script.decompose()
              
              text = soup.get_text(separator=" ")
              # Clean up whitespace
              text = " ".join(text.split())
              
              return text
          except Exception as e:
              logger.error(f"Error extracting text: {e}")
              return None
  ```

- [ ] **Create `app/extractors/api_client.py`**
  ```python
  import logging
  import requests
  import json
  from typing import Dict, Optional
  from datetime import datetime

  logger = logging.getLogger(__name__)

  class APIClient:
      def __init__(self, timeout: int = 10, retries: int = 3):
          self.timeout = timeout
          self.retries = retries

      def get(self, url: str, headers: Optional[Dict] = None) -> Optional[Dict]:
          """
          Make GET request to an API endpoint.
          
          Returns JSON response or error details.
          """
          
          for attempt in range(self.retries):
              try:
                  logger.info(f"API GET {url} (attempt {attempt + 1}/{self.retries})")
                  
                  response = requests.get(
                      url,
                      headers=headers or {},
                      timeout=self.timeout
                  )
                  response.raise_for_status()
                  
                  logger.info(f"API SUCCESS {url}")
                  
                  return {
                      "url": url,
                      "status_code": response.status_code,
                      "data": response.json(),
                      "fetched_at": datetime.utcnow().isoformat(),
                      "success": True
                  }
                  
              except requests.exceptions.JSONDecodeError:
                  logger.error(f"Invalid JSON response from {url}")
                  return {
                      "url": url,
                      "status_code": response.status_code,
                      "data": None,
                      "success": False,
                      "error": "Invalid JSON"
                  }
              except Exception as e:
                  logger.error(f"API Error {url}: {e}")
          
          return {
              "url": url,
              "data": None,
              "success": False,
              "error": "Max retries exceeded"
          }
  ```

✅ **Output:** Robust data extraction with retry logic and error handling

---

## PHASE 5: Data Cleaning & Validation

**Goal:** Transform raw data into trusted, structured format.

**Rationale:** Garbage in = garbage out. Validation before storage prevents database bloat and trust violations.

### Tools & Why
- **Pydantic** (MIT) → Type-safe data validation
- **re** (stdlib) → Text normalization

### Tasks

- [ ] **Create `app/processors/models.py`** (Output schemas)
  ```python
  from pydantic import BaseModel, Field
  from datetime import datetime
  from typing import Optional, List

  class CleanedContent(BaseModel):
      source_name: str
      source_domain: str
      title: Optional[str] = None
      content: str = Field(..., min_length=10, max_length=1000000)
      extracted_at: datetime
      cleaned_at: datetime
      trust_score: float = Field(..., ge=0.0, le=1.0)
      language: str = "en"
      metadata: Optional[dict] = None

  class ExtractionResult(BaseModel):
      job_id: str
      source_name: str
      status: str  # "success" or "failed"
      data: Optional[CleanedContent] = None
      error: Optional[str] = None
      timestamp: datetime
  ```

- [ ] **Create `app/processors/cleaner.py`**
  ```python
  import re
  import logging
  from typing import Optional
  from datetime import datetime

  logger = logging.getLogger(__name__)

  class DataCleaner:
      @staticmethod
      def normalize_whitespace(text: str) -> str:
          """Collapse multiple spaces, tabs, newlines."""
          return re.sub(r'\s+', ' ', text).strip()

      @staticmethod
      def remove_html_entities(text: str) -> str:
          """Convert HTML entities to regular text."""
          replacements = {
              '&nbsp;': ' ',
              '&lt;': '<',
              '&gt;': '>',
              '&amp;': '&',
              '&quot;': '"',
              '&#39;': "'"
          }
          for entity, char in replacements.items():
              text = text.replace(entity, char)
          return text

      @staticmethod
      def clean_urls(text: str) -> str:
          """Remove or normalize URLs."""
          return re.sub(r'https?://\S+', '[URL]', text)

      @staticmethod
      def clean_emails(text: str) -> str:
          """Remove email addresses."""
          return re.sub(r'\S+@\S+', '[EMAIL]', text)

      @classmethod
      def clean(cls, text: str) -> str:
          """Apply all cleaning steps."""
          logger.debug("Starting data cleaning...")
          text = cls.remove_html_entities(text)
          text = cls.clean_urls(text)
          text = cls.clean_emails(text)
          text = cls.normalize_whitespace(text)
          logger.debug("Cleaning complete")
          return text

      @staticmethod
      def validate_content(text: str, min_length: int = 10, max_length: int = 1000000) -> bool:
          """Check if content meets quality threshold."""
          if not text or len(text) < min_length:
              logger.warning(f"Content too short: {len(text)} chars")
              return False
          if len(text) > max_length:
              logger.warning(f"Content too long: {len(text)} chars")
              return False
          return True
  ```

✅ **Output:** Validated, structured data ready for storage

---

## PHASE 6: Data Storage (Persistence)

**Goal:** Persist extracted data with metadata and indexing.

**Rationale:** Storage is where we build the "memory" of the system — critical for scaling and replay.

### Tools & Why
- **SQLite** (stdlib) → Development, single-file, zero setup
- **PostgreSQL** (open source) → Production, scalable, JSONB support
- **SQLAlchemy** (MIT) → ORM, database-agnostic

### Tasks

- [ ] **Install SQLAlchemy**
  ```bash
  pip install sqlalchemy psycopg2-binary  # psycopg2 for PostgreSQL
  ```

- [ ] **Create `app/db/models.py`** (Database schemas)
  ```python
  from sqlalchemy import Column, String, Float, DateTime, Integer, Text, JSON, create_engine
  from sqlalchemy.ext.declarative import declarative_base
  from datetime import datetime

  Base = declarative_base()

  class Source(Base):
      __tablename__ = "sources"
      
      id = Column(Integer, primary_key=True)
      name = Column(String(255), unique=True, nullable=False)
      domain = Column(String(255), nullable=False)
      category = Column(String(50), nullable=False)
      trust_score = Column(Float, nullable=False)
      last_fetched = Column(DateTime, nullable=True)
      
  class ExtractedData(Base):
      __tablename__ = "extracted_data"
      
      id = Column(Integer, primary_key=True)
      source_id = Column(Integer, nullable=False)
      job_id = Column(String(36), unique=True, nullable=False)
      title = Column(String(500), nullable=True)
      content = Column(Text, nullable=False)
      extracted_at = Column(DateTime, nullable=False)
      cleaned_at = Column(DateTime, nullable=False)
      trust_score = Column(Float, nullable=False)
      language = Column(String(10), default="en")
      metadata = Column(JSON, nullable=True)
      created_at = Column(DateTime, default=datetime.utcnow)
      
      __table_args__ = (
          # Index for queries by source
          # Index for queries by extraction date
      )

  class Job(Base):
      __tablename__ = "jobs"
      
      id = Column(String(36), primary_key=True)
      source_id = Column(Integer, nullable=False)
      status = Column(String(20), nullable=False)
      created_at = Column(DateTime, nullable=False)
      started_at = Column(DateTime, nullable=True)
      completed_at = Column(DateTime, nullable=True)
      error = Column(Text, nullable=True)
  ```

- [ ] **Create `app/db/database.py`** (Connection manager)
  ```python
  import logging
  import os
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from app.db.models import Base

  logger = logging.getLogger(__name__)

  # Development: SQLite
  DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trustwise.db")

  # Production example (uncomment):
  # DATABASE_URL = "postgresql://user:password@localhost:5432/trustwise"

  engine = create_engine(
      DATABASE_URL,
      echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
  )
  SessionLocal = sessionmaker(bind=engine)

  def init_db():
      """Create all tables."""
      Base.metadata.create_all(bind=engine)
      logger.info("Database initialized")

  def get_session():
      """Dependency injection for FastAPI."""
      session = SessionLocal()
      try:
          yield session
      finally:
          session.close()
  ```

- [ ] **Create `app/db/repository.py`** (CRUD operations)
  ```python
  import logging
  from sqlalchemy.orm import Session
  from app.db.models import ExtractedData, Source, Job

  logger = logging.getLogger(__name__)

  class DataRepository:
      @staticmethod
      def save_data(session: Session, **kwargs) -> ExtractedData:
          """Save cleaned data to database."""
          data = ExtractedData(**kwargs)
          session.add(data)
          session.commit()
          session.refresh(data)
          logger.info(f"Data saved: {data.job_id}")
          return data

      @staticmethod
      def get_by_job(session: Session, job_id: str) -> ExtractedData:
          return session.query(ExtractedData).filter_by(job_id=job_id).first()

      @staticmethod
      def get_by_source(session: Session, source_id: int, limit: int = 100):
          return session.query(ExtractedData).filter_by(source_id=source_id).limit(limit).all()
  ```

✅ **Output:** Persistent storage with database abstraction

---

## PHASE 7: Automatic Scheduling

**Goal:** Refresh data at defined intervals from trusted sources.

**Rationale:** Users need fresh data without manual intervention.

### Tools & Why
- **APScheduler** (MIT) → Background job scheduler

### Tasks

- [ ] **Install APScheduler**
  ```bash
  pip install apscheduler
  ```

- [ ] **Create `app/scheduler/background_jobs.py`**
  ```python
  import logging
  from apscheduler.schedulers.background import BackgroundScheduler
  from apscheduler.triggers.interval import IntervalTrigger
  from app.orchestrator.orchestrator import Orchestrator

  logger = logging.getLogger(__name__)

  scheduler = BackgroundScheduler()
  orchestrator = None  # Will be set from main.py

  def fetch_source_job(source_name: str):
      """Scheduled job to fetch data from a source."""
      logger.info(f"Scheduled job: fetching {source_name}")
      job = orchestrator.create_job(source_name)
      # Placeholder: dispatch to actual extraction
      orchestrator.start_job(job.job_id)

  def schedule_sources(sources: list):
      """Create scheduling jobs for all sources."""
      for source in sources:
          hours = source.get("refresh_interval_hours", 12)
          
          scheduler.add_job(
              fetch_source_job,
              IntervalTrigger(hours=hours),
              args=[source["name"]],
              name=f"fetch_{source['name']}"
          )
          logger.info(f"Scheduled {source['name']} every {hours} hours")

  def start():
      if not scheduler.running:
          scheduler.start()
          logger.info("Background scheduler started")

  def stop():
      scheduler.shutdown()
      logger.info("Background scheduler stopped")
  ```

- [ ] **Integrate into FastAPI startup** (`app/main.py`)
  ```python
  from app.scheduler import background_jobs

  @app.on_event("startup")
  async def startup_event():
      logger.info("TrustWise starting...")
      background_jobs.orchestrator = orchestrator
      background_jobs.start()

  @app.on_event("shutdown")
  async def shutdown_event():
      logger.info("TrustWise shutting down...")
      background_jobs.stop()
  ```

✅ **Output:** Automated data refresh on schedule

---

## PHASE 8: API Access & Security

**Goal:** Protect against unauthorized access and abuse.

**Rationale:** Data is a liability. Must control who accesses what.

### Tools & Why
- **FastAPI Security** (built-in)
- **python-jose** (MIT) → JWT tokens
- **passlib** (BSD) → Password hashing

### Tasks

- [ ] **Install auth libraries**
  ```bash
  pip install python-jose passlib python-multipart
  ```

- [ ] **Create `app/auth/security.py`**
  ```python
  import logging
  from datetime import datetime, timedelta
  from typing import Optional
  from jose import JWTError, jwt
  from passlib.context import CryptContext

  logger = logging.getLogger(__name__)

  SECRET_KEY = "your-secret-key-change-in-production"  # Use env var
  ALGORITHM = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES = 30

  pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

  def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
      to_encode = data.copy()
      if expires_delta:
          expire = datetime.utcnow() + expires_delta
      else:
          expire = datetime.utcnow() + timedelta(minutes=15)
      to_encode.update({"exp": expire})
      encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
      return encoded_jwt

  def verify_token(token: str):
      try:
          payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
          user_id = payload.get("sub")
          if user_id is None:
              return None
          return user_id
      except JWTError:
          logger.error("Invalid token")
          return None
  ```

- [ ] **Create protected endpoints** (`app/main.py`)
  ```python
  from fastapi import Depends, HTTPException, status
  from fastapi.security import HTTPBearer, HTTPAuthCredentials

  security = HTTPBearer()

  async def get_current_user(credentials: HTTPAuthCredentials = Depends(security)):
      token = credentials.credentials
      user_id = verify_token(token)
      if not user_id:
          raise HTTPException(
              status_code=status.HTTP_401_UNAUTHORIZED,
              detail="Invalid authentication credentials"
          )
      return user_id

  @app.get("/data/{job_id}")
  async def get_data(job_id: str, current_user: str = Depends(get_current_user)):
      # Only authenticated users can access
      return orchestrator.get_job(job_id)
  ```

✅ **Output:** Authenticated API access

---

## PHASE 9: Monitoring & Observability

**Goal:** Understand system behavior, detect failures early.

**Rationale:** "What gets measured gets managed." Central logging is critical for debugging.

### Tools & Why
- **logging** (stdlib) → Centralized logs
- **Prometheus** (optional, open source) → Metrics 

### Tasks

- [ ] **Create `app/logging/setup.py`**
  ```python
  import logging
  import logging.handlers
  import os
  from datetime import datetime

  def setup_logging():
      """Configure centralized logging."""
      
      log_dir = "logs"
      os.makedirs(log_dir, exist_ok=True)
      
      log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
      
      # File handler
      file_handler = logging.handlers.RotatingFileHandler(
          f"{log_dir}/trustwise.log",
          maxBytes=10_000_000,  # 10MB
          backupCount=5
      )
      file_handler.setFormatter(logging.Formatter(log_format))
      
      # Console handler
      console_handler = logging.StreamHandler()
      console_handler.setFormatter(logging.Formatter(log_format))
      
      # Root logger
      root_logger = logging.getLogger()
      root_logger.setLevel(logging.INFO)
      root_logger.addHandler(file_handler)
      root_logger.addHandler(console_handler)
  ```

- [ ] **Use in `app/main.py`**
  ```python
  from app.logging.setup import setup_logging

  setup_logging()
  logger = logging.getLogger(__name__)
  ```

- [ ] **Add metrics endpoint** (optional)
  ```python
  @app.get("/metrics")
  def get_metrics():
      return {
          "total_jobs": len(orchestrator.get_all_jobs()),
          "total_sources": 0,  # Query DB
          "timestamp": datetime.utcnow().isoformat()
      }
  ```

✅ **Output:** Transparent system observability

---

## PHASE 10: Containerization (Optional)

**Goal:** Package for deployment without dependency Hell.

**Rationale:** "Works on my machine" → Works everywhere.

### Tools & Why
- **Docker** (open source engine)
- **docker-compose** (orchestration)

### Tasks

- [ ] **Create `Dockerfile`**
  ```dockerfile
  FROM python:3.10-slim

  WORKDIR /app

  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt

  COPY . .

  EXPOSE 8000

  CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

- [ ] **Create `docker-compose.yml`**
  ```yaml
  version: '3.8'

  services:
    trustwise:
      build: .
      ports:
        - "8000:8000"
      environment:
        - DATABASE_URL=sqlite:///./trustwise.db
        - LOG_LEVEL=INFO
      volumes:
        - ./logs:/app/logs
        - ./data:/app/data

    # Optional: PostgreSQL for production
    # postgres:
    #   image: postgres:15
    #   environment:
    #     POSTGRES_DB: trustwise
    #     POSTGRES_PASSWORD: secret
    #   volumes:
    #     - postgres_data:/var/lib/postgresql/data

  # volumes:
  #   postgres_data:
  ```

- [ ] **Build & run**
  ```bash
  docker build -t trustwise:latest .
  docker run -p 8000:8000 trustwise:latest
  ```

✅ **Output:** Production-ready container image

---

## Complete Stack Summary

| **Layer**       | **Tool**              | **License** | **Status**     |
|-----------------|----------------------|-------------|----------------|
| **API**         | FastAPI               | MIT         | ✅ PHASE 1    |
| **Server**      | Uvicorn               | BSD         | ✅ PHASE 1    |
| **Orchestrator**| Python                | PSF         | ✅ PHASE 3    |
| **Scraping**    | Requests + BeautifulSoup | Apache 2 + MIT | ✅ PHASE 4 |
| **Validation**  | Pydantic              | MIT         | ✅ PHASE 5    |
| **ORM**         | SQLAlchemy            | MIT         | ✅ PHASE 6    |
| **Database**    | SQLite / PostgreSQL   | PD + OSS    | ✅ PHASE 6    |
| **Scheduler**   | APScheduler           | MIT         | ✅ PHASE 7    |
| **Auth**        | python-jose           | MIT         | ⏳ PHASE 8    |
| **Logging**     | stdlib logging        | PSF         | ✅ PHASE 9    |
| **Container**   | Docker                | Apache 2    | ⏳ PHASE 10   |
| **Editor**      | VS Code               | MIT         | ✅ READY      |

---

## Key Principles

### 1. **Trust-First Design**
- Every piece of data is validated against a whitelist
- Minimum confidence scores enforced
- Failures default to "reject" not "accept"

### 2. **Zero Vendor Lock-In**
- All tools are open-source
- All data is portable (SQL dumps, JSON exports)
- Can switch databases, servers, containers at any time

### 3. **Observability > Silence**
- Log everything
- Make metrics visible
- The system should never be a black box

### 4. **Fail Safe**
- If no trusted sources, fail hard (don't hallucinate)
- Retries with backoff for transient failures
- Clear error messages for debugging

### 5. **Incremental Complexity**
- Start with Phase 1 (API works)
- Add storage (Phase 6) only when needed
- Add auth (Phase 8) when users arrive
- Add persistence (Phase 7) for reliability

---

## Next Steps (Choose One)

### Option 1: **Start Code Implementation**
Begin with PHASE 1 and PHASE 2 immediately.

### Option 2: **Architecture Diagram**
Generate a Mermaid diagram showing:
- Data flow
- Agent interactions
- Trust verification pipeline

### Option 3: **Dependency Tree**
Generate `requirements.txt` with pinned versions and explanations.

### Option 4: **Git Structure**
Create git branch strategy:
- `main` → production-ready
- `develop` → testing ground
- `feature/*` → individual work

---

## Questions to Clarify Before Implementation

1. **Data sources:** Specific websites/APIs to add beyond the examples?
2. **Scaling:** Will you need PostgreSQL from day one, or SQLite initially?
3. **Authentication:** API key, JWT, OAuth—what's your preference?
4. **Real-time vs. periodic:** Need instant extraction or scheduled batches?
5. **Deployment target:** Docker locally, Then cloud (Azure/AWS/GCP)?

---

## Reality Check

✅ **You CAN build a production-grade orchestrator with free tools.**

The limiting factor is NOT software—it's:
- Clear thinking about requirements
- Disciplined code structure
- Consistent monitoring
- Honest error handling

You're already doing the hard part: **thinking systematically**.

---

## Reference Commands

```bash
# Virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload

# Run tests (Phase later)
pytest tests/

# Database setup
python -c "from app.db.database import init_db; init_db()"

# Docker
docker build -t trustwise:latest .
docker run -p 8000:8000 trustwise:latest

# Logs
tail -f logs/trustwise.log
```

---

**Document Version:** 1.0  
**Last Updated:** February 6, 2026  
**Status:** Ready for Implementation
