# 📋 Quick Reference Checklist

**Print this out or bookmark for easy reference during Phase 0 implementation.**

---

## 🔴 Critical: Must Fix Before Code Runs

### Before Starting Anything
- [ ] Read `FEASIBILITY_SUMMARY.md` (5 min)
- [ ] Skim `PHASE_0_BLOCKERS.md` (10 min)
- [ ] Understand why current code is broken

### Phase 0A: Install Dependencies
- [ ] Activate virtual environment: `venv\Scripts\activate`
- [ ] Upgrade pip: `python -m pip install --upgrade pip`
- [ ] Install all dependencies: `pip install -r requirements.txt`
- [ ] Verify imports work:
  ```bash
  python -c "import fastapi, sqlalchemy, pydantic; print('OK')"
  ```
- [ ] ✅ All packages installed successfully

### Phase 0B: Fix Orchestrator Code
- [ ] Read current `app/orchestrator/orchestrator.py` (note: defined twice ❌)
- [ ] Replace with clean code from `PHASE_0_BLOCKERS.md` Phase 0B
- [ ] Remove duplicate `class Orchestrator:` definition
- [ ] Add proper error handling in `_load_config()`
- [ ] Make `handle_query()` async
- [ ] ✅ Single, clean Orchestrator

### Phase 0C: Fix Scheduler & Agents
- [ ] Update all agents to be `async def` functions:
  - [ ] `db_agent(trusted_sources) → async db_agent(trusted_sources)`
  - [ ] `vector_agent() → async vector_agent(trusted_sources)`
  - [ ] `web_agent(trusted_sources) → async web_agent(trusted_sources)`
  - [ ] `research_agent(trusted_sources) → async research_agent(trusted_sources)`
- [ ] Add try/except to each agent
- [ ] Add logging to each agent
- [ ] Update Scheduler to use `asyncio.gather()`
- [ ] Update Scheduler to use `asyncio.wait_for()` for timeouts
- [ ] ✅ Agents are async with error handling

### Phase 0D: Add Logging & Environment Config
- [ ] Create `app/logging_config.py` (code in PHASE_0_BLOCKERS.md)
- [ ] Create `app/config.py` with Pydantic settings
- [ ] Create `.env` file with environment variables
- [ ] Create `config/` directory for data files
- [ ] Update `app/main.py` to use `setup_logging()`
- [ ] Update `app/main.py` to use `settings` object
- [ ] Replace all `print()` with `logger.xxx()`
- [ ] ✅ Centralized logging to file

### Phase 0E: Docker & PostgreSQL
- [ ] Create `docker-compose.yml` (code in PHASE_0_BLOCKERS.md)
- [ ] Start services: `docker-compose up -d`
- [ ] Verify running: `docker-compose ps`
- [ ] Update `.env`: `DATABASE_URL=postgresql://trustwise:trustwise@localhost:5432/trustwise_dev`
- [ ] ✅ PostgreSQL running locally

### Phase 0F: Test Everything
- [ ] Create `config/trusted_sources.json` (example in PHASE_0_BLOCKERS.md)
- [ ] Start server: `uvicorn app.main:app --reload`
- [ ] Test health check: `curl http://localhost:8000/`
- [ ] Check logs: `tail -f logs/trustwise.log`
- [ ] Verify no errors in startup
- [ ] Stop server: `Ctrl+C`
- [ ] ✅ Code runs without errors

---

## 🟡 Important: Scalability Hardening

### After Phase 0 Basics Work

- [ ] Add rate limiting to `app/main.py`:
  ```python
  from slowapi import Limiter
  from slowapi.util import get_remote_address
  
  limiter = Limiter(key_func=get_remote_address)
  
  @app.post("/jobs")
  @limiter.limit("100/minute")
  def create_job(...):
  ```

- [ ] Add database connection pooling to `config.py`:
  ```python
  DATABASE_ENGINE_KWARGS = {
      "pool_size": 20,
      "max_overflow": 40,
      "pool_recycle": 3600,
  }
  ```

- [ ] Update task timeouts in `app/orchestrator/chunker.py`:
  ```python
  # Instead of hardcoded 100ms:
  TIMEOUT_BY_SOURCE_TYPE = {
      "web_scrape": 10000,    # 10 seconds
      "db_check": 5000,       # 5 seconds
      "vector_check": 3000,   # 3 seconds
      "research_lookup": 15000  # 15 seconds
  }
  ```

- [ ] Add retry logic with backoff to extractors:
  ```python
  from tenacity import retry, wait_exponential, stop_after_attempt
  
  @retry(
      wait=wait_exponential(multiplier=1, min=2, max=10),
      stop=stop_after_attempt(3)
  )
  async def fetch(self, url: str):
      ...
  ```

---

## 📝 Files to Modify/Create

### Modify These Files
- [ ] `app/main.py` - Add logging & config
- [ ] `app/orchestrator/orchestrator.py` - Remove duplication
- [ ] `app/orchestrator/scheduler.py` - Add async/await
- [ ] `app/agents/db_agent.py` - Make async
- [ ] `app/agents/vector_agent.py` - Make async
- [ ] `app/agents/web_agent.py` - Make async
- [ ] `app/agents/research_agent.py` - Make async
- [ ] `requirements.txt` - ✅ DONE

### Create These Files
- [ ] `app/config.py` - Environment settings
- [ ] `app/logging_config.py` - Logging setup
- [ ] `.env` - Environment variables
- [ ] `docker-compose.yml` - Database container
- [ ] `config/trusted_sources.json` - Source whitelist

### Keep These As-Is (For Now)
- [ ] `README.md` - Already updated
- [ ] `prompts.json` - Works as-is
- [ ] `app/__init__.py` - Works as-is

---

## 🧪 Testing Checklist

### Code Runs
- [ ] No `ModuleNotFoundError`
- [ ] No `ImportError`
- [ ] No syntax errors
- [ ] Server starts without errors

### Server Works
- [ ] `curl http://localhost:8000/` returns 200
- [ ] `curl http://localhost:8000/ready` returns {"ready": true}
- [ ] Health check endpoint responds in milliseconds

### Logging Works
- [ ] `logs/trustwise.log` file created
- [ ] Server startup logged
- [ ] Request logs appear
- [ ] Can search logs for specific requests

### Database Works
- [ ] PostgreSQL container running
- [ ] Can connect from Python
- [ ] Tables can be created

### Async Works
- [ ] Multiple concurrent requests don't block
- [ ] Agents run in parallel
- [ ] No timeouts under 10 seconds

---

## 🚨 Common Errors & Fixes

### Error: `ModuleNotFoundError: No module named 'sqlalchemy'`
**Fix:** Run `pip install -r requirements.txt`

### Error: `Orchestrator is not defined`
**Fix:** Check `orchestrator.py` for duplicate class definitions

### Error: `TypeError: vector_agent() takes 0 positional arguments but 1 was given`
**Fix:** Change `def vector_agent():` to `async def vector_agent(trusted_sources):`

### Error: `FileNotFoundError: trusted_sources.json`
**Fix:** Create `config/trusted_sources.json` file

### Error: `Connection to postgres failed`
**Fix:** Run `docker-compose up -d` to start database

### Error: `SyntaxError in agent file`
**Fix:** Check for missing `:` or `async` keyword

### Error: `Port 8000 already in use`
**Fix:** Kill old process: `fuser -k 8000/tcp` or use different port

---

## 📊 Progress Tracking

### Week 1: Phase 0
- [ ] Day 1: Phase 0A-0B (dependencies + orchestrator)
- [ ] Day 2: Phase 0C (scheduler + agents)
- [ ] Day 3: Phase 0D (logging + config)
- [ ] Day 4: Phase 0E (docker + database)
- [ ] Day 5: Phase 0F (test + verify)
- [ ] Days 6-7: Buffer + adjustments

### Week 2: Phase 1-2
- [ ] Add database models
- [ ] Add job persistence
- [ ] API endpoints work
- [ ] Full integration test

### Weeks 3-4: Phase 3+
- [ ] Real data extraction
- [ ] Scheduling works
- [ ] Production features

---

## 🎯 Success Criteria

When Phase 0 is **DONE** (not just running, but DONE):

✅ Code runs without errors  
✅ Handles 10+ concurrent requests  
✅ Jobs stored in database (not memory)  
✅ All errors logged to file  
✅ PostgreSQL verified working  
✅ Orchestrator clean (no duplication)  
✅ All agents async  
✅ Configuration from environment  

Only then should you move to Phase 1.

---

## 📞 Getting Help

### For Code Questions
1. Check `PHASE_0_BLOCKERS.md` for exact code
2. Compare your file to the provided version
3. Look for error traceback in `logs/trustwise.log`

### For Architecture Questions
1. Check `ARCHITECTURE_DIAGRAMS.md` for visual flow
2. Review `FEASIBILITY_SCALABILITY_REPORT.md` for detailed analysis
3. Look at the Before/After comparison

### For Integration Issues
1. Check `docker-compose logs postgres` for database errors
2. Check `logs/trustwise.log` for application errors
3. Run `pip freeze` to verify dependency versions

---

## 📚 Key Resources

**Documentation Created:**
1. `README.md` - Project overview
2. `FEASIBILITY_SUMMARY.md` - Executive summary (START HERE)
3. `FEASIBILITY_SCALABILITY_REPORT.md` - Detailed analysis
4. `PHASE_0_BLOCKERS.md` - Step-by-step fixes with code
5. `ARCHITECTURE_DIAGRAMS.md` - Visual before/after
6. `IMPLEMENTATION_PLAN.md` - Full 10-phase roadmap
7. `QUICK_REFERENCE.md` - This file

**Reading Order:**
1. This file (5 min) - Overview of what to do
2. `PHASE_0_BLOCKERS.md` (30 min) - Detailed steps
3. Code provided in Phase 0B-F - Implementation

---

## ✅ Phase 0 Completion Checklist

When you can check ALL of these, Phase 0 is complete:

- [ ] `pip install -r requirements.txt` runs without errors
- [ ] `python -c "import fastapi; import sqlalchemy; import pydantic"` works
- [ ] `app/orchestrator/orchestrator.py` contains only ONE class definition
- [ ] All agents are defined as `async def` functions
- [ ] Scheduler uses `asyncio.gather()` for parallel execution
- [ ] All `print()` statements replaced with `logger.xxx()`
- [ ] `.env` file created with DATABASE_URL
- [ ] `app/config.py` file created and imported
- [ ] `app/logging_config.py` file created and imported
- [ ] `docker-compose.yml` file created
- [ ] `docker-compose up -d` runs without errors
- [ ] `docker-compose ps` shows postgres running
- [ ] `config/trusted_sources.json` file created
- [ ] `logs/` directory created with `trustwise.log`
- [ ] `uvicorn app.main:app --reload` starts without errors
- [ ] `curl http://localhost:8000/` returns 200 OK
- [ ] `curl http://localhost:8000/ready` returns {"ready": true}
- [ ] Logs appear in `logs/trustwise.log`
- [ ] PostgreSQL connection works (can verify in logs)
- [ ] No errors in logs related to missing dependencies
- [ ] No errors in logs related to imports
- [ ] No errors in logs related to configuration

**Once all 21 items are checked:** Phase 0 is complete. Move to Phase 1.

---

## 🟢 Phase 1: API & Job Persistence

### Phase 1A: Database Models
- [ ] Create `app/database/` directory structure
- [ ] Create `app/database/__init__.py` with exports
- [ ] Create `app/database/models.py` with SQLAlchemy ORM:
  - [ ] `Job` model with UUID, status enum, timestamps
  - [ ] `ExtractedData` model with foreign key to Job
  - [ ] `Source` model for tracking data sources
  - [ ] All indexes and relationships defined
- [ ] Verify models have proper type hints
- [ ] ✅ ORM models complete

### Phase 1B: Database Connection
- [ ] Create `app/database/database.py` with:
  - [ ] Engine creation with connection pooling
  - [ ] SessionLocal factory
  - [ ] get_db() FastAPI dependency
  - [ ] Event listeners for monitoring
- [ ] Test database URL in `.env`
- [ ] ✅ Database connection ready

### Phase 1C: Alembic Migrations
- [ ] Run `alembic init migrations`
- [ ] Update `alembic.ini` with DATABASE_URL
- [ ] Update `migrations/env.py` to import models
- [ ] Create `migrations/versions/001_initial_schema.py` with:
  - [ ] Job table with all fields
  - [ ] ExtractedData table with foreign key
  - [ ] Source table with unique constraint
  - [ ] All indexes defined
- [ ] Test migration: `alembic upgrade head` (after starting postgres)
- [ ] ✅ Migration system ready

### Phase 1D: API Schemas
- [ ] Create `app/schemas.py` with Pydantic models:
  - [ ] `JobCreateRequest` (source_name, priority, notify_url)
  - [ ] `JobResponse` (id, source_name, status, created_at)
  - [ ] `JobDetailResponse` (all fields + extracted_data)
  - [ ] `JobListResponse` (total, items, skip, limit)
  - [ ] `ExtractedDataResponse` (id, source, data, trust_score)
  - [ ] `HealthResponse` (status, service, version, database)
- [ ] All models use `from_attributes = True`
- [ ] ✅ Request/response models defined

### Phase 1E: API Endpoints
- [x] Update `app/main.py` with:
  - [x] Database imports
  - [x] Rate limiter setup (slowapi)
  - [x] Startup event to create tables
  - [x] POST /jobs (create job, rate limit 100/min)
  - [x] GET /jobs/{job_id} (get job details, rate limit 1000/min)
  - [x] GET /jobs (list jobs with pagination, rate limit 1000/min)
  - [x] Updated GET / (health check with database status)
  - [x] GET /ready (readiness probe)
  - [x] Exception handlers (400, 404, 429, 500)
- [x] All endpoints have proper error handling
- [x] All endpoints are logged
- [x] ✅ All endpoints implemented with rate limiting

### Phase 1F: Testing
- [ ] Start PostgreSQL: `docker-compose up -d`
- [ ] Install database: `pip install -r requirements.txt`
- [ ] Run migrations: `alembic upgrade head`
- [ ] Start server: `uvicorn app.main:app --reload`
- [ ] Test endpoints:
  - [ ] `curl http://localhost:8000/` returns health status
  - [ ] `curl http://localhost:8000/docs` shows API documentation
  - [ ] POST job: `curl -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d '{"source_name": "pib"}'`
  - [ ] GET jobs: `curl http://localhost:8000/jobs`
  - [ ] Get one job: `curl http://localhost:8000/jobs/{job_id}`
  - [ ] Rate limit test: Send 101+ requests, get 429
- [ ] Verify jobs in database: `psql -U trustwise -d trustwise_dev -c "SELECT * FROM job;"`
- [ ] ✅ All endpoints working

**Once all Phase 1 items are checked:** Phase 1 is complete. Move to Phase 2.

---

**Last Updated:** February 6, 2026  
**Difficulty Phase 0:** Medium (follow step-by-step)  
**Difficulty Phase 1:** Medium (database + API integration)  
**Time Required Phase 0:** 5-8 hours  
**Time Required Phase 1:** 3-5 hours  
**Success Rate:** 95%+ if following the exact steps

