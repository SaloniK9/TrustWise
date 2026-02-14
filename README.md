# TrustWise - Trustworthy Information Orchestration Engine

**Status:** ✅ DEPLOYMENT READY | Core Complete (Phases 0-5B) | Production Ready  
**Version:** 1.0.0 | **Last Updated:** February 14, 2026

A production-grade FastAPI-based orchestration system with distributed task processing, high availability, and intelligent multi-source data extraction.

## Overview

TrustWise is a distributed information orchestration platform with:

- **Multi-source extraction** from databases, vector stores, web APIs, and research repositories
- **Trust verification** with configurable confidence thresholds and trust scores
- **Distributed processing** via Celery task queues with specialized workers
- **High availability** through Redis Sentinel, PostgreSQL replication, and HAProxy load balancing
- **Real-time monitoring** with Prometheus, Grafana, and Flower dashboards
- **Async architecture** for high-throughput parallel execution

## Key Features

### � Production-Ready High Availability (Phase 5B)

- **Redis Sentinel** - 3-node cluster with automatic failover, quorum=2
- **PostgreSQL Replication** - Primary + 2 hot standby replicas with streaming replication
- **HAProxy Load Balancing** - 3 FastAPI instances with health checks and SSL termination
- **Zero downtime deployment** - Rolling updates and graceful restarts
- **RTO < 30 seconds** - Automatic failover for Redis and manual promotion for PostgreSQL

### ⚡ Distributed Task Processing (Phase 5A)

- **Celery workers** - Specialized queues for web, research, and vector extraction
- **Redis broker** - High-performance message queue with Sentinel support
- **Async job execution** - Non-blocking API with task status tracking
- **Beat scheduler** - Recurring job scheduling for periodic updates
- **Flower monitoring** - Real-time worker and task visualization

### 🔐 Trust-Based Architecture

- Configurable trust scores for databases, web sources, and APIs
- Confidence threshold enforcement (minimum 80% for acceptance)
- Automatic rejection of queries when no trusted sources validate
- Vector similarity search for semantic matching

### 🤖 Multi-Agent System

- **Vector Agent**: Retrieves similar answers from vector databases (Chroma/Pinecone/Weaviate)
- **Database Agent**: Queries internal PostgreSQL databases with ORM
- **Web Agent**: Async HTTP scraping with BeautifulSoup4 and rate limiting
- **Research Agent**: ArXiv API integration for academic papers

### 📊 Monitoring & Observability (Phase 4)

- **Prometheus** - Metrics collection for jobs, tasks, and system health
- **Grafana** - Real-time dashboards for performance visualization
- **Flower** - Celery worker and task monitoring
- **HAProxy Stats** - Load balancer statistics and backend health

## Quick Start

### Prerequisites

- **Docker & Docker Compose** installed
- **8GB+ RAM** recommended for full stack
- **Ports available:** 80, 443, 5432-5435, 6379-6381, 8000, 8404, 9090, 26379-26381

### 1. Start Services

```bash
# Clone repository
git clone <repo-url>
cd TrustWise

# Start all services (63 containers)
docker-compose up -d

# Wait for initialization (30-60 seconds)
docker-compose ps

# Check health
curl -k https://localhost/health
```

### 2. Verify Phase 5B

```bash
# Run automated verification
python verify_phase_5b.py

# Expected output: All tests pass ✅
```

### 3. Access Dashboards

- **API Docs:** http://localhost:8000/docs
- **HAProxy Stats:** http://localhost:8404/stats (admin:trustwise)
- **Flower (Celery):** http://localhost:5555
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3000 (admin:admin)

### 4. Create Your First Job

```bash
# Create a job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"source_name": "arxiv"}'

# Response: {"id": "...", "status": "pending", ...}

# Trigger extraction
curl -X POST http://localhost:8000/jobs/{job_id}/extract

# Check results
curl http://localhost:8000/jobs/{job_id}/extractions
```

---

## Architecture

### Deployment Topology (Phase 5B)

```
Internet
   │
   ▼
[HAProxy] ────────────────────── SSL Termination (443)
  (80/443/8404)                  Health Checks
   │                             Load Balancing
   ├─► [FastAPI-1:8000] ──┐
   ├─► [FastAPI-2:8000] ──┼─────► PostgreSQL Primary (5432)
   └─► [FastAPI-3:8000] ──┘         │
                │                   ├─► Standby-1 (5433)
                │                   └─► Standby-2 (5434)
                ▼
       [Redis Sentinel]
       (3 nodes: 26379/80/81)
              │
        ┌─────┼─────┐
        ▼     ▼     ▼
    [Master][Rep1][Rep2]
    (6379) (6380)(6381)
              │
              ▼
      [Celery Workers]
       web | research | vector
       beat | flower
```

### Technology Stack

**Core:**

- Python 3.11+, FastAPI, SQLAlchemy, Pydantic

**Data Storage:**

- PostgreSQL 15 (Primary + 2 Standby replicas)
- Redis 7 (Master + 2 Replicas + 3 Sentinels)

**Task Processing:**

- Celery, APScheduler

**Monitoring:**

- Prometheus, Grafana, Flower

**HA & Load Balancing:**

- HAProxy, Redis Sentinel, PostgreSQL Streaming Replication

**Deployment:**

- Docker, Docker Compose, Kubernetes (planned)

---

## API Endpoints

### Health & Status

- `GET /` - Basic health check
- `GET /health` - Health check for load balancers
- `GET /ready` - Readiness probe (with DB check)
- `GET /live` - Liveness probe

### Job Management

- `POST /jobs` - Create new job (rate limit: 100/min)
- `GET /jobs` - List jobs with pagination
- `GET /jobs/{job_id}` - Get job details
- `POST /jobs/{job_id}/extract` - Trigger synchronous extraction
- `GET /jobs/{job_id}/extractions` - Get extraction results
- `POST /jobs/{job_id}/schedule` - Schedule recurring job

### Celery Async Processing

- `POST /api/v1/jobs/{job_id}/extract/async` - Async extraction via Celery
- `GET /api/v1/tasks/{task_id}/status` - Get task status
- `POST /api/v1/jobs/{job_id}/extract/by-type/async` - Type-specific extraction
- `GET /api/v1/workers/stats` - Celery worker statistics

### Extractors

- `GET /extractors/health` - Health check for all extractors
- `POST /extractors/{type}/search` - Direct search (web/research/vector)

### Monitoring

- `GET /metrics` - Prometheus metrics
- `GET /docs` - OpenAPI/Swagger UI

---

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Redis (direct or Sentinel)
REDIS_BROKER=sentinel://sentinel-1:26379/0
REDIS_BACKEND=sentinel://sentinel-1:26379/1
REDIS_SENTINEL_HOSTS=sentinel-1:26379,sentinel-2:26379,sentinel-3:26379
REDIS_SENTINEL_MASTER=mymaster

# Application
LOG_LEVEL=INFO
DEBUG=false
```

### Trusted Sources

Edit `config/trusted_sources.json`:

```json
{
  "databases": [{ "name": "postgres", "type": "sql", "trust_score": 0.95 }],
  "web_sources": [
    { "name": "arxiv", "domain": "arxiv.org", "trust_score": 0.97 }
  ],
  "apis": [
    {
      "name": "worldbank",
      "base_url": "api.worldbank.org",
      "trust_score": 0.94
    }
  ]
}
```

---

## Monitoring & Operations

### Health Checks

```bash
# Application health
curl -k https://localhost/health

# HAProxy stats
curl http://localhost:8404/stats

# Celery workers (Flower)
curl http://localhost:5555
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f fastapi
docker-compose logs -f celery-worker-web
docker-compose logs -f sentinel-1
docker-compose logs -f postgres-primary
```

### Database Operations

```bash
# Connect to primary
docker exec -it trustwise-postgres-primary psql -U trustwise -d trustwise_dev

# Check replication
SELECT * FROM pg_stat_replication;

# View jobs
SELECT id, source_name, status, created_at FROM jobs LIMIT 10;
```

### Failover Testing

```bash
# Test Redis failover
docker stop trustwise-redis-master
# Watch Sentinel promote replica: docker logs -f trustwise-sentinel-1

# Test load balancer
docker stop trustwise-fastapi-2
# Check HAProxy stats: http://localhost:8404/stats
# API should still work via other instances
```

---

## Performance & Scalability

### Current Capacity (Phase 5B)

- **API Throughput:** 1000+ req/sec (3 FastAPI instances)
- **Concurrent Jobs:** 100+ via Celery workers
- **Failover Time:** < 30 seconds (Redis Sentinel)
- **Uptime Target:** 99.95%

### Scaling

**Horizontal Scaling:**

```bash
# Add FastAPI instances (update docker-compose.yml and haproxy.cfg)
docker-compose up -d --scale fastapi=5

# Add Celery workers
docker-compose up -d --scale celery-worker-web=5
```

**Vertical Scaling:**

- Increase container memory/CPU limits
- Tune PostgreSQL shared_buffers and work_mem
- Increase Redis maxmemory

---

## Troubleshooting

### Issue: Services won't start

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]
```

### Issue: Redis Sentinel not promoting

```bash
# Check Sentinel status
docker exec trustwise-sentinel-1 redis-cli -p 26379 sentinel masters

# Verify quorum
docker exec trustwise-sentinel-1 redis-cli -p 26379 info sentinel

# Check network connectivity
docker exec trustwise-sentinel-1 ping redis-master
```

### Issue: PostgreSQL replication lag

```bash
# Check replication status
docker exec trustwise-postgres-primary psql -U trustwise -c \
  "SELECT write_lag, flush_lag, replay_lag FROM pg_stat_replication;"

# Increase wal_keep_size and max_wal_senders
```

### Issue: HAProxy backends down

```bash
# Check backend health
curl http://localhost:8404/stats

# Test FastAPI directly
curl http://localhost:8000/health

# Verify HAProxy config
docker exec trustwise-haproxy haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg
```

---

## Documentation

**Essential Docs:**

- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Complete project overview
- [PHASE_5B_COMPLETE.md](PHASE_5B_COMPLETE.md) - Phase 5B completion report
- [PHASE_5B_IMPLEMENTATION_RUNBOOK.md](PHASE_5B_IMPLEMENTATION_RUNBOOK.md) - Deployment guide
- [PHASES_AND_TODOS.md](PHASES_AND_TODOS.md) - Detailed phase breakdown

**Architecture:**

- [ARCHITECTURE_DIAGRAMS.md](ARCHITECTURE_DIAGRAMS.md) - System diagrams
- [PHASE_5B_HIGH_AVAILABILITY.md](PHASE_5B_HIGH_AVAILABILITY.md) - HA design

**Operations:**

- [PHASE_4_OPERATIONAL_RUNBOOK.md](PHASE_4_OPERATIONAL_RUNBOOK.md) - Monitoring guide
- [verify_phase_5b.py](verify_phase_5b.py) - Automated verification script

---

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Import verification
python test_imports.py

# System verification (Phase 0-4)
python verify_system.py

# Phase 5B verification (requires Docker)
python verify_phase_5b.py
```

### Code Structure

```
TrustWise/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── schemas.py           # Pydantic models
│   ├── tasks.py             # Celery tasks
│   ├── celery_config.py     # Celery configuration
│   ├── celery_routes.py     # Celery API routes
│   ├── agents/              # Data extraction agents
│   ├── database/            # SQLAlchemy models
│   ├── extractors/          # Extraction engine
│   ├── orchestrator/        # Task orchestration
│   └── monitoring/          # Prometheus metrics
├── config/                  # Configuration files
│   ├── redis/               # Redis & Sentinel configs
│   ├── postgresql/          # PostgreSQL configs
│   ├── haproxy/             # HAProxy config
│   └── monitoring/          # Prometheus/Grafana configs
├── k8s/                     # Kubernetes manifests (Phase 5C)
└── scripts/                 # Utility scripts
```

---

## Roadmap

### ✅ Completed Phases

- **Phase 0:** Critical blockers & async foundation
- **Phase 1:** API & job persistence
- **Phase 2:** Data extraction (web/research/vector)
- **Phase 3:** Task queue & scheduling
- **Phase 4:** Monitoring (Prometheus/Grafana)
- **Phase 5A:** Celery distributed processing
- **Phase 5B:** High availability (Redis Sentinel, PostgreSQL replication, HAProxy)

### 🚧 Upcoming Phases

- **Phase 5C:** Kubernetes deployment (4-5 days)
  - K8s manifests, HPA, Ingress, StatefulSets
- **Phase 5D:** Production package (2-3 days)
  - CI/CD, automated deployment, backup strategies

---

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guide
- Add type hints to all functions
- Update documentation for API changes
- Ensure all tests pass before submitting

---

## License

[Add license information]

---

## Support

For issues, questions, or feature requests:

- **Documentation:** See [PROJECT_STATUS.md](PROJECT_STATUS.md)
- **Verification:** Run `python verify_phase_5b.py`
- **Logs:** Check `docker-compose logs [service-name]`

---

**Current Status:** Phase 5B Complete ✅ | Production Ready  
**Version:** 0.1.0 | **Last Updated:** February 14, 2026

## Support

For issues, questions, or contributions, please open an issue in the repository.
