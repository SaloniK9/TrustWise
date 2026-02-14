# TrustWise - Quick Reference Card

**Phase 5B Complete** ✅ | Production Ready | Last Updated: Feb 14, 2026

---

## 🚀 Quick Start (30 seconds)

```bash
# Start all services
docker-compose up -d

# Verify deployment
python verify_phase_5b.py

# Access API
curl -k https://localhost/health
```

---

## 📊 Service URLs

| Service             | URL                         | Credentials     |
| ------------------- | --------------------------- | --------------- |
| API (Load Balanced) | https://localhost           | -               |
| API Direct          | http://localhost:8000       | -               |
| API Docs            | http://localhost:8000/docs  | -               |
| HAProxy Stats       | http://localhost:8404/stats | admin:trustwise |
| Flower (Celery)     | http://localhost:5555       | -               |
| Prometheus          | http://localhost:9090       | -               |
| Grafana             | http://localhost:3000       | admin:admin     |

---

## 🏗️ Architecture at a Glance

```
[HAProxy:80/443] → [FastAPI-1/2/3:8000] → [Redis Sentinel] → [Celery Workers]
                                         ↘ [PostgreSQL Primary + 2 Standby]
```

**Services:**

- **3** FastAPI instances (load balanced)
- **3** Redis Sentinel nodes + 1 master + 2 replicas
- **1** PostgreSQL primary + 2 standby replicas
- **5** Celery workers (web, research, vector, beat, flower)

---

## 🔧 Essential Commands

### Status Checks

```bash
# All containers
docker-compose ps

# Health checks
curl -k https://localhost/health               # API via HAProxy
curl http://localhost:8000/health              # API direct
curl http://localhost:8404/stats               # HAProxy stats
curl http://localhost:5555                     # Flower

# Redis Sentinel
docker exec trustwise-sentinel-1 redis-cli -p 26379 sentinel masters

# PostgreSQL replication
docker exec trustwise-postgres-primary psql -U trustwise -c \
  "SELECT * FROM pg_stat_replication;"
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f [service-name]

# Common services:
# - fastapi, fastapi-2, fastapi-3
# - redis-master, redis-replica-1, redis-replica-2
# - sentinel-1, sentinel-2, sentinel-3
# - postgres-primary, postgres-standby-1, postgres-standby-2
# - celery-worker-web, celery-worker-research, celery-worker-vector
# - celery-beat, celery-flower
# - haproxy
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart [service-name]

# Rolling restart (zero downtime)
docker-compose restart fastapi
docker-compose restart fastapi-2
docker-compose restart fastapi-3
```

---

## 🧪 Testing

### Create Job

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"source_name": "arxiv"}'

# Response: {"id": "...", "status": "pending", ...}
```

### Trigger Extraction

```bash
curl -X POST http://localhost:8000/jobs/{job_id}/extract
```

### Check Results

```bash
curl http://localhost:8000/jobs/{job_id}/extractions
```

### Async Extraction (Celery)

```bash
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/extract/async
# Response: {"task_id": "..."}

# Check task status
curl http://localhost:8000/api/v1/tasks/{task_id}/status
```

---

## 🔥 Failover Testing

### Redis

```bash
# Stop master
docker stop trustwise-redis-master

# Watch Sentinel promote replica
docker logs -f trustwise-sentinel-1

# Restart original (becomes replica)
docker start trustwise-redis-master
```

### Load Balancer

```bash
# Stop one FastAPI instance
docker stop trustwise-fastapi-2

# API still works (via other instances)
curl -k https://localhost/health

# Restart
docker start trustwise-fastapi-2
```

---

## 📁 Key Files

### Configuration

- `docker-compose.yml` - Full stack
- `config/redis/sentinel-1.conf` - Sentinel config
- `config/postgresql/postgresql-primary.conf` - Primary DB
- `config/haproxy/haproxy.cfg` - Load balancer
- `config/ssl/server.pem` - SSL certificate

### Application

- `app/main.py` - FastAPI app
- `app/celery_config.py` - Celery with Sentinel
- `app/tasks.py` - Celery tasks

### Documentation

- `README.md` - Main docs
- `PROJECT_STATUS.md` - Complete overview
- `PHASE_5B_COMPLETE.md` - Phase 5B details
- `PHASES_AND_TODOS.md` - Roadmap

### Scripts

- `verify_phase_5b.py` - Automated verification
- `scripts/generate_ssl_cert.sh` - SSL cert generation

---

## 🚨 Troubleshooting

### Containers won't start

```bash
docker-compose ps                    # Check status
docker-compose logs [service]        # Check logs
docker-compose restart [service]     # Restart service
```

### Sentinel not monitoring

```bash
# Check Sentinel status
docker exec trustwise-sentinel-1 redis-cli -p 26379 sentinel masters

# Verify master is running
docker exec trustwise-redis-master redis-cli ping

# Check network
docker exec trustwise-sentinel-1 ping redis-master
```

### HAProxy backends down

```bash
# Check stats
curl http://localhost:8404/stats

# Test FastAPI directly
curl http://localhost:8000/health

# Verify config
docker exec trustwise-haproxy haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg
```

### PostgreSQL replication lag

```bash
# Check replication status
docker exec trustwise-postgres-primary psql -U trustwise -c \
  "SELECT write_lag, flush_lag, replay_lag FROM pg_stat_replication;"

# Check standby status
docker exec trustwise-postgres-standby-1 pg_isready
```

---

## 📈 Monitoring Metrics

### Key Prometheus Metrics

```
# Jobs
trustwise_jobs_started_total
trustwise_jobs_completed_total
trustwise_jobs_running

# Tasks
trustwise_tasks_dispatched_total
trustwise_tasks_failed_total

# Job duration
trustwise_job_duration_seconds
```

### Access Prometheus

```bash
# Metrics endpoint
curl http://localhost:9090/metrics

# Query example
http://localhost:9090/graph?g0.expr=rate(trustwise_jobs_started_total[5m])
```

---

## 🛠️ Environment Variables

```bash
# Database
DATABASE_URL=postgresql://trustwise:trustwise@postgres-primary:5432/trustwise_dev

# Redis (Sentinel)
REDIS_BROKER=sentinel://sentinel-1:26379/0
REDIS_BACKEND=sentinel://sentinel-1:26379/1
REDIS_SENTINEL_HOSTS=sentinel-1:26379,sentinel-2:26379,sentinel-3:26379
REDIS_SENTINEL_MASTER=mymaster

# Application
LOG_LEVEL=INFO
DEBUG=false
```

---

## 📊 Performance Targets

- **API Throughput:** 1000+ req/sec
- **Concurrent Jobs:** 100+
- **Failover Time:** < 30 seconds
- **Uptime:** 99.95%

---

## 🔜 Next Phase: 5C (Kubernetes)

**Coming Next:**

- K8s manifests
- HorizontalPodAutoscaler
- Ingress controller
- StatefulSets
- PersistentVolumes

**Duration:** 4-5 days

---

## 📚 Documentation Index

**Start Here:**

1. `README.md` - Overview & quick start
2. `PROJECT_STATUS.md` - Complete status
3. `PHASE_5B_COMPLETE.md` - Phase 5B details

**Operations:**

- `PHASE_5B_IMPLEMENTATION_RUNBOOK.md` - Deployment guide
- `PHASE_4_OPERATIONAL_RUNBOOK.md` - Monitoring guide

**Architecture:**

- `ARCHITECTURE_DIAGRAMS.md` - System diagrams
- `PHASE_5B_HIGH_AVAILABILITY.md` - HA design

**Roadmap:**

- `PHASES_AND_TODOS.md` - Detailed phases

---

## 🎯 Status Summary

✅ **Phase 5B COMPLETE**

- High Availability: ✅
- Load Balancing: ✅
- Redis Sentinel: ✅
- PostgreSQL Replication: ✅
- SSL/TLS: ✅
- Monitoring: ✅
- Documentation: ✅

**Ready for:** Production deployment testing

---

**Quick Reference v1.0** | Feb 14, 2026
