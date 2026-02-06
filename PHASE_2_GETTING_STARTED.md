# Phase 2 Getting Started Guide - Data Extraction

**Date:** February 6, 2026  
**Phase:** 2 - Data Extraction  
**Status:** ✅ Implementation Complete, Ready for Testing

---

## Quick Start

### 1. Install Dependencies

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
# or source venv/bin/activate  # Linux/Mac

# Install Phase 2 dependencies
pip install -r requirements.txt

# Or install specific packages
pip install sentence-transformers chromadb
```

### 2. Start PostgreSQL

```bash
# Start Docker containers (PostgreSQL + PGAdmin)
docker-compose up -d

# Verify database is ready
docker ps  # Should see postgres and pgadmin containers
```

### 3. Run Migrations

```bash
# Apply database migrations
alembic upgrade head

# Verify tables created
python -c "from app.database.database import engine; from app.database.models import Base; Base.metadata.tables.keys()"
```

### 4. Start the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Access API

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/
- **Readiness:** http://localhost:8000/ready

---

## Testing Phase 2 Features

### Test 1: Create a Job

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"source_name": "research"}'

# Response:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "source_name": "research",
#   "status": "pending",
#   "created_at": "2026-02-06T12:34:56.789Z"
# }

# Save job ID for next tests
export JOB_ID="550e8400-e29b-41d4-a716-446655440000"
```

### Test 2: Check Extractor Health

```bash
curl http://localhost:8000/extractors/health

# Response should show status of each extractor:
# {
#   "timestamp": "2026-02-06T12:34:56.789Z",
#   "extractors": {
#     "web": {"source": "web", "type": "web", "status": "healthy"},
#     "research": {"source": "research", "type": "research", "status": "healthy"},
#     "vector": {"source": "vector", "type": "vector", "status": "..."}
#   }
# }
```

### Test 3: Perform Direct Extractor Search

```bash
# Test web scraper (scrape example site)
curl -X POST http://localhost:8000/extractors/web/search \
  -H "Content-Type: application/json" \
  -d '{"query": "https://httpbin.org/html"}'

# Test research API (search ArXiv)
curl -X POST http://localhost:8000/extractors/research/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning trustworthiness"}'

# Test vector DB (if configured)
curl -X POST http://localhost:8000/extractors/vector/search \
  -H "Content-Type: application/json" \
  -d '{"query": "semantic similarity search"}'
```

### Test 4: Trigger Extraction for Job

```bash
# Extract from all sources (parallel)
curl -X POST http://localhost:8000/jobs/$JOB_ID/extract \
  -H "Content-Type: application/json" \
  -d '{"query": "artificial intelligence ethics"}'

# Or extract from specific source
curl -X POST http://localhost:8000/jobs/$JOB_ID/extract \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "extractor_type": "research"}'

# Response:
# {
#   "job_id": "550e8400-...",
#   "success_count": 2,
#   "error_count": 1,
#   "extractions": [
#     {
#       "source": "web",
#       "status": "success",
#       "data": [...],
#       "trust_score": 0.85
#     },
#     {
#       "source": "research",
#       "status": "success",
#       "data": [...],
#       "trust_score": 0.95
#     }
#   ]
# }
```

### Test 5: Retrieve Extracted Data

```bash
# Get all extracted data for job
curl "http://localhost:8000/jobs/$JOB_ID/extractions"

# Get with pagination
curl "http://localhost:8000/jobs/$JOB_ID/extractions?skip=0&limit=10"

# Filter by source
curl "http://localhost:8000/jobs/$JOB_ID/extractions?source=research"

# Response:
# {
#   "job_id": "550e8400-...",
#   "total": 25,
#   "items": [
#     {
#       "id": "abc-123",
#       "source": "research",
#       "data": {...},
#       "extracted_at": "2026-02-06T12:34:56.789Z",
#       "trust_score": 0.95
#     },
#     ...
#   ],
#   "skip": 0,
#   "limit": 10
# }
```

### Test 6: Get Job Details with All Data

```bash
# Get full job with all associated extracted data
curl "http://localhost:8000/jobs/$JOB_ID"

# Response includes:
# {
#   "id": "550e8400-...",
#   "source_name": "research",
#   "status": "success",
#   "created_at": "2026-02-06T12:34:56.789Z",
#   "started_at": "2026-02-06T12:34:56.789Z",
#   "completed_at": "2026-02-06T12:34:58.789Z",
#   "data": [
#     {
#       "id": "abc-123",
#       "source": "research",
#       "data": {...},
#       "extracted_at": "2026-02-06T12:34:56.789Z",
#       "trust_score": 0.95
#     },
#     ...
#   ]
# }
```

---

## API Endpoint Reference

### Extraction Endpoints (New in Phase 2)

| Method | Endpoint | Rate Limit | Purpose |
|--------|----------|----------|---------|
| POST | `/jobs/{job_id}/extract` | 50/min | Trigger data extraction |
| GET | `/jobs/{job_id}/extractions` | 500/min | Retrieve extracted data |
| GET | `/extractors/health` | 100/min | Check extractor status |
| POST | `/extractors/{type}/search` | 200/min | Direct extractor search |

### Extractor Types

| Type | Extractor | Purpose | Speed |
|------|-----------|---------|-------|
| `web` | WebScraper | Scrape HTML pages | 2-5s |
| `research` | ResearchAPI | Search academic papers (ArXiv) | 3-8s |
| `vector` | VectorDatabase | Semantic similarity search | 1-3s |

### Query Parameters

**POST /jobs/{job_id}/extract:**
- `query` (string, optional): Search query (defaults to job source_name)
- `extractor_type` (string, optional): Specific extractor type (web, research, vector)

**GET /jobs/{job_id}/extractions:**
- `source` (string, optional): Filter by source (web, research, vector)
- `skip` (int, optional): Pagination offset (default: 0)
- `limit` (int, optional): Results per page (default: 20, max: 100)

**POST /extractors/{extractor_type}/search:**
- `query` (string, required): Search query
- `filters` (object, optional): Extractor-specific filters

---

## Python Integration Examples

### Example 1: Basic Extraction

```python
import asyncio
import httpx
from uuid import UUID

async def extract_data():
    # 1. Create job
    async with httpx.AsyncClient() as client:
        job_resp = await client.post(
            "http://localhost:8000/jobs",
            json={"source_name": "research"}
        )
        job_id = job_resp.json()["id"]
        print(f"Created job: {job_id}")
        
        # 2. Trigger extraction
        extract_resp = await client.post(
            f"http://localhost:8000/jobs/{job_id}/extract",
            json={"query": "machine learning"}
        )
        result = extract_resp.json()
        print(f"Extraction result: {result}")
        
        # 3. Get extracted data
        data_resp = await client.get(
            f"http://localhost:8000/jobs/{job_id}/extractions"
        )
        data = data_resp.json()
        print(f"Found {data['total']} extracted items")

asyncio.run(extract_data())
```

### Example 2: Using ExtractionEngine Directly

```python
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.extractors.engine import ExtractionEngine
from uuid import uuid4

async def direct_extraction():
    db = SessionLocal()
    engine = ExtractionEngine(db)
    
    # Extract from all sources
    result = await engine.extract_from_all(
        job_id=uuid4(),
        source_name="research",
        query="artificial intelligence ethics"
    )
    
    print(f"Success: {result['success_count']}")
    print(f"Errors: {result['error_count']}")
    
    # Check health
    health = await engine.health_check()
    print(f"Extractor health: {health}")
    
    await engine.cleanup()

import asyncio
asyncio.run(direct_extraction())
```

### Example 3: Research API Direct Usage

```python
from app.extractors.research_api import ResearchAPIClient
import asyncio

async def search_arxiv():
    client = ResearchAPIClient()
    
    # Search with filters
    result = await client.search_arxiv(
        query="quantum computing",
        category="quant-ph",
        max_results=20,
        year=2025
    )
    
    print(f"Found {len(result['data'])} papers")
    for paper in result['data'][:3]:
        print(f"- {paper['title']}")
        print(f"  Authors: {', '.join(paper['authors'][:3])}")
        print(f"  Published: {paper['published']}")
    
    await client.close()

asyncio.run(search_arxiv())
```

### Example 4: Web Scraper Direct Usage

```python
from app.extractors.web_scraper import WebScraper
import asyncio

async def scrape_website():
    scraper = WebScraper(timeout=10, max_retries=3)
    
    # Scrape website
    result = await scraper.extract(
        query="https://example.com",
        filters={"selector": "h1, h2, h3, p"}
    )
    
    print(f"Status: {result['status']}")
    print(f"Items extracted: {len(result['data'])}")
    print(f"Trust score: {result['trust_score']}")
    
    if result['status'] == 'success':
        for item in result['data'][:5]:
            print(f"- {item['type']}: {item['text'][:100]}...")
    
    await scraper.close()

asyncio.run(scrape_website())
```

---

## Configuration

### Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/trustwise

# Vector DB selection
VECTOR_DB_BACKEND=chroma  # or pinecone, weaviate

# Pinecone (if using cloud)
PINECONE_API_KEY=your-api-key
PINECONE_ENVIRONMENT=us-west1-gcp

# Extraction timeouts
WEB_SCRAPER_TIMEOUT=10
RESEARCH_API_TIMEOUT=10
VECTOR_DB_TIMEOUT=10

# Logging
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Tuning for Performance

**For low-latency fresh data:**
```python
# In engine.py
timeout = 5  # Faster timeouts
max_retries = 1  # Fail fast
CACHE_TTL_SECONDS = 300  # Short cache
```

**For high-reliability bulk extraction:**
```python
# In engine.py
timeout = 15  # Allow more time
max_retries = 3  # Generous retries
CACHE_TTL_SECONDS = 3600  # Cache longer
```

---

## Troubleshooting

### Issue: "Connection refused" on extraction

**Cause:** Extractor can't reach source  
**Solution:**
```bash
# Test network connectivity
curl https://httpbin.org/get  # For web
curl http://export.arxiv.org/api/query  # For research

# Check firewall/proxy settings in .env
```

### Issue: Vector DB not connecting

**Cause:** Chroma/Pinecone client not initialized  
**Solution:**
```bash
# For local Chroma: It initializes automatically
# For Pinecone: Set PINECONE_API_KEY in .env
# For Weaviate: Ensure WEAVIATE_URL is correct

# Test connection
curl http://localhost:8000/extractors/health
```

### Issue: Slow extraction (>10s)

**Cause:** Network latency or large result sets  
**Solution:**
```python
# Reduce result limit in engine.py
max_results = 20  # Instead of 100

# Increase timeout
timeout = 15  # Instead of 10

# Use vector DB (faster than web/research)
extractor_type = "vector"
```

### Issue: Rate limit errors (429)

**Cause:** Too many requests or hitting API limits  
**Solution:**
```bash
# Check endpoint rate limits: 50-500/min
# Spread requests over time or use caching

# For ArXiv: Max 3 requests/second (handled by library)
# For web: Max 10 connections per pool

# Increase cache TTL
CACHE_TTL_SECONDS=7200  # 2 hours
```

### Issue: Database connection errors

**Cause:** PostgreSQL not running  
**Solution:**
```bash
# Start containers
docker-compose up -d

# Verify running
docker-compose ps

# Check logs
docker-compose logs postgres

# Reset if needed
docker-compose down -v
docker-compose up -d
```

---

## Monitoring

### Check Extractor Health

```bash
curl http://localhost:8000/extractors/health | python -m json.tool
```

### View Job Progress

```bash
# Get job status
curl http://localhost:8000/jobs/{job_id}

# Get extraction count
curl http://localhost:8000/jobs/{job_id}/extractions?limit=1 | python -m json.tool | grep total
```

### View Logs

```bash
# Application logs
tail -f app.log

# Docker PostgreSQL logs
docker-compose logs -f postgres

# All logs
docker-compose logs -f
```

---

## Next Steps

1. **Test all extractors** with the examples above
2. **Verify database** has extracted data: `SELECT * FROM extracted_data;`
3. **Monitor performance** with `/extractors/health` endpoint
4. **Configure your backend** (Chroma/Pinecone/Weaviate)
5. **Proceed to Phase 3** once extraction is working reliably

---

## Phase 3 Preparation

Phase 3 will add:
- Background job queue (Celery/APScheduler)
- Periodic extraction scheduling
- Job dependency handling
- Task result caching

**Estimated Timeline:** 5-7 days after Phase 2 completion

---

**Status:** ✅ Ready for Testing

Start with the Quick Start section and run through the tests to verify Phase 2 is working correctly.
