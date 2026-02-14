# PHASE 5B: High Availability & Failover
## Production Ready - Distributed System Resilience

**Status:** PLANNING  
**Target Duration:** 2-3 weeks  
**Priority:** Critical for production deployment  
**Complexity:** High  
**Team Size:** 2-3 engineers  

---

## Table of Contents
1. [Objectives](#objectives)
2. [Architecture Overview](#architecture-overview)
3. [Task Breakdown](#task-breakdown)
4. [Redis Sentinel Setup](#redis-sentinel-setup)
5. [Database High Availability](#database-high-availability)
6. [Load Balancing](#load-balancing)
7. [Monitoring & Failover](#monitoring--failover)
8. [Implementation Checklist](#implementation-checklist)

---

## Objectives

### Primary Goals
1. **Single Point of Failure Elimination**: No service can bring down entire system
2. **Automatic Failover**: Replica promotion without manual intervention
3. **Zero-Downtime Deployment**: Rolling updates for services
4. **Data Durability**: Persist all critical state with backup strategy
5. **Monitoring & Alerting**: Real-time failover event detection and response

### Success Metrics
- RTO (Recovery Time Objective): < 30 seconds
- RPO (Recovery Point Objective): < 5 minutes
- 99.95% uptime target
- Automatic failover completion: < 2 minutes
- All monitoring alerts firing correctly

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer                            │
│              (NGinx/HAProxy, port 80/443)                   │
└──────┬──────────────────────────────────────┬────────────────┘
       │                                      │
       ▼                                      ▼
┌─────────────────────┐         ┌─────────────────────┐
│  FastAPI Instance 1 │         │  FastAPI Instance 2 │
│  (uvicorn:8000)     │         │  (uvicorn:8000)     │
└──────┬──────────────┘         └──────────┬──────────┘
       │                               │
       └───────────────┬───────────────┘
                       ▼
       ┌───────────────────────────┐
       │   Redis Sentinel (3x)     │
       │   Master: 26379           │
       │   Sentinel: 26380         │
       └───────────────────────────┘
               │          │
         ┌─────▼──────────▼──────┐
         │   Redis Master        │
         │   (port 6379)         │
         │   AOF + RDB backup    │
         └───────────┬───────────┘
                     │
           ┌─────────┴──────────┐
           ▼                    ▼
      ┌──────────┐         ┌──────────┐
      │ Replica1 │         │ Replica2 │
      │ (6379)   │         │ (6379)   │
      └──────────┘         └──────────┘
          │                    │
          └────────┬───────────┘
                   ▼
        PostgreSQL: Replication
        ├─ Primary instance
        ├─ Hot standby (streaming)
        └─ Backup standby

┌──────────────────────────────────────────────┐
│        Celery Worker Cluster (Scaled)        │
│  ├─ web workers (3 replicas)                │
│  ├─ research workers (3 replicas)           │
│  ├─ vector workers (3 replicas)             │
│  └─ Beat scheduler (2 for redundancy)       │
└──────────────────────────────────────────────┘
```

---

## Task Breakdown

### Phase 5B.1: Redis Sentinel Configuration
**Duration:** 2-3 days  
**Dependencies:** Phase 5A (Celery + Redis)  
**Deliverables:**
- Redis Sentinel cluster (3 instances)
- Automatic failover configuration
- Monitoring integration
- Updated docker-compose.yml with Sentinel

**Implementation Steps:**

1. **Create Redis Sentinel Configuration Files**
   - `config/redis/sentinel-1.conf`
   - `config/redis/sentinel-2.conf`
   - `config/redis/sentinel-3.conf`
   - Each Sentinel monitors Primary/Replicas
   - Quorum: 2 for failover decision

2. **Docker Compose Updates**
   - Add sentinel-1, sentinel-2, sentinel-3 services
   - Redis replicas (slave-1, slave-2)
   - Persistent volumes for AOF + RDB
   - Health checks for Sentinel status
   - Network configuration for Sentinel discovery

3. **Celery Configuration Updates**
   - Update broker_url for Sentinel mode: `sentinel://localhost:26379/0` with sentinel_kwargs
   - Configure Celery to auto-connect to Sentinel
   - Update connection pool settings for failover
   - Set connection timeout: 5s, retry: 3x

4. **Testing Failover Scenarios**
   - Test master failure → automatic replica promotion
   - Test Sentinel crash (still functional with 2 remaining)
   - Test network partition recovery
   - Verify Celery reconnects automatically
   - Monitor task execution during failover

### Phase 5B.2: PostgreSQL High Availability
**Duration:** 3-4 days  
**Dependencies:** Database models exist (Phase 1)  
**Deliverables:**
- PostgreSQL replication setup
- WAL archiving for point-in-time recovery
- Automated backup strategy
- Failover mechanism

**Implementation Steps:**

1. **PostgreSQL Streaming Replication Setup**
   - Primary: Listen for replication connections
   - Standby 1: Hot standby connected via streaming
   - Standby 2: Warm standby for backup
   - Recovery target: Timeline history + WAL archiving

2. **Configuration Files**
   - `postgresql.conf`:
     - max_wal_senders = 5
     - wal_keep_size = 1GB
     - archive_mode = on
     - archive_command = 's3://bucket/wal/%f'
     - shared_preload_libraries = 'pg_stat_statements'
   
   - `.pgpass` for replication user authentication
   - Replication slots for streaming

3. **Docker Updates**
   - Primary PostgreSQL service (read/write)
   - Standby services (read-only replicas)
   - Shared WAL archive volume (or S3/MinIO)
   - Health checks: psql connection + replication status

4. **Backup Strategy**
   - Daily full backup to persistent storage
   - Continuous WAL archiving to S3
   - Point-in-time recovery capability
   - Backup verification (restore test monthly)
   - Retention policy: 30 days backup history

5. **Automatic Failover Mechanism**
   - PostgreSQL automatic failover tool (pgautofailover or patroni)
   - OR: Manual failover script with health checks
   - Update FastAPI connection string on failover
   - Connection pool adjustment for new primary

### Phase 5B.3: Load Balancing & API Gateway
**Duration:** 2-3 days  
**Dependencies:** FastAPI instances operational  
**Deliverables:**
- Multi-instance FastAPI deployment
- Load balancer (HAProxy/NGinx)
- Health check configuration
- SSL/TLS termination

**Implementation Steps:**

1. **Load Balancer Setup (HAProxy)**
   - `config/haproxy.cfg`:
     - Frontend: Listen on 8080 (app traffic)
     - Backend: 2-3 FastAPI instances on 8000
     - Health check: GET /health every 5 seconds
     - Sticky sessions (if needed) via JSESSIONID
     - Keep-alive connection management
   - SSL termination at load balancer
   - Redirect HTTP → HTTPS
   - Rate limiting at balancer level

2. **Multiple FastAPI Instances**
   - Docker compose: 2-3 FastAPI service replicas
   - Each with independent database connection pool
   - Shared redis connection (through Sentinel)
   - Health endpoints: `/health`, `/ready`, `/live`

3. **Docker Compose Service Configuration**
   - FastAPI 1, 2, 3: Separate service definitions
   - All connected to same networks
   - HAProxy service routing traffic
   - Port mapping only on HAProxy (no direct app access)

4. **Health Check Mechanics**
   - Implement 3 health check endpoints:
     - `/health`: Overall system health
     - `/ready`: Ready to accept traffic
     - `/live`: Process alive (used by K8s)
   - HAProxy checks `/health` every 5s
   - Fall after 2 failures
   - Rise after 2 successes

### Phase 5B.4: Monitoring & Failover Automation
**Duration:** 2-3 days  
**Dependencies:** Phase 4 (Prometheus/Grafana)  
**Deliverables:**
- Failover event detection
- Automated alerting
- Operator runbook
- Dashboard updates

**Implementation Steps:**

1. **New Prometheus Metrics**
   - `redis_sentinel_masters` - Number of monitored masters
   - `redis_sentinel_slaves` - Replica count
   - `redis_master_failed_total` - Failover count
   - `pg_replication_slots` - Replication lag
   - `pg_wal_position` - WAL write position
   - `pg_standby_last_restore` - Last standby synchronization
   - `haproxy_backend_up` - Active backend servers
   - `haproxy_backend_sessions` - Load per server

2. **Alerting Rules**
   - Redis Master down → Critical alert
   - Sentinel quorum lost → Critical alert
   - PostgreSQL replication lag > 10MB → Warning
   - Master WAL position not advancing → Warning
   - Load balancer: All backends down → Critical
   - HAProxy: Backend response time > 5s → Warning

3. **Grafana Dashboard Additions**
   - Redis Sentinel status panel
   - PostgreSQL replication lag graph
   - Failover timeline visualization
   - Load balancer distribution chart
   - Recovery time metric

4. **Automated Failover Playbook**
   - Redis Sentinel handles its own failover
   - PostgreSQL: Use pg_auto_failover on standby promotion
   - Application: Monitor connection errors, auto-reconnect with exponential backoff
   - Alert operators for manual verification
   - Runbook: Manual promotion if auto-failover fails

---

## Redis Sentinel Setup

### File: `config/redis/sentinel-1.conf`
```ini
# Sentinel monitoring configuration
port 26379
dir /tmp

monitor mymaster 127.0.0.1 6379 2

# Failover timeout: 10 seconds
failover-timeout 10000

# Notification script (for alerting)
notification-script /app/scripts/notify-sentinel.sh

# Client reconfig script
client-reconfig-script /app/scripts/reconfig-sentinel.sh

# Logging
loglevel notice
logfile "/var/log/sentinel-1.log"

# Persistence
save 900 1
save 300 10
save 60 10000
```

### File: `config/redis/redis-replica.conf`
```ini
# Replica configuration
slaveof mymaster 6379  # OR use replicaof (newer Redis)
replica-priority 50

# Read-only mode
replica-read-only yes

# AOF
appendonly yes
appendfsync everysec

# Logging
loglevel notice
logfile "/var/log/redis-replica.log"
```

### Docker Compose Updates
```yaml
services:
  redis-master:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_master_data:/data
      - ./config/redis/redis-master.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 2s
      retries: 3

  redis-replica-1:
    image: redis:7-alpine
    ports:
      - "6380:6379"
    volumes:
      - redis_replica1_data:/data
      - ./config/redis/redis-replica.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    depends_on:
      - redis-master

  sentinel-1:
    image: redis:7-alpine
    ports:
      - "26379:26379"
    volumes:
      - ./config/redis/sentinel-1.conf:/etc/redis/sentinel.conf
    command: redis-sentinel /etc/redis/sentinel.conf
    depends_on:
      - redis-master

  sentinel-2:
    image: redis:7-alpine
    ports:
      - "26380:26379"
    volumes:
      - ./config/redis/sentinel-2.conf:/etc/redis/sentinel.conf
    command: redis-sentinel /etc/redis/sentinel.conf

  sentinel-3:
    image: redis:7-alpine
    ports:
      - "26381:26379"
    volumes:
      - ./config/redis/sentinel-3.conf:/etc/redis/sentinel.conf
    command: redis-sentinel /etc/redis/sentinel.conf

volumes:
  redis_master_data:
  redis_replica1_data:
```

---

## Database High Availability

### PostgreSQL Configuration for Replication

**Primary (`postgresql.conf`)**:
```ini
# Basic settings
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB

# Replication
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
wal_keep_size = 1GB
hot_standby = on

# Archive
archive_mode = on
archive_command = 'test ! -f /mnt/wal_archive/%f && cp %p /mnt/wal_archive/%f'

# Logging
log_replication_commands = on
log_connections = on
log_disconnections = on
```

**Standby (`recovery.conf`)**:
```ini
standby_mode = 'on'
primary_conninfo = 'host=postgres-primary port=5432 user=replication password=<password>'
recovery_target_timeline = 'latest'
```

### Backup Strategy

**Daily Backup Script** (`scripts/backup-postgres.sh`):
```bash
#!/bin/bash
BACKUP_DIR="/mnt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Full backup
pg_basebackup -h localhost -D $BACKUP_DIR/full_$DATE -Ft -z -P

# Verify backup
pg_basebackup -h localhost -D /tmp/verify_$DATE -Ft -z -P && rm -rf /tmp/verify_$DATE

# Upload to S3
aws s3 cp $BACKUP_DIR/full_$DATE s3://trustwise-backups/

# Retain 30 days
find $BACKUP_DIR -name "full_*" -mtime +30 -delete
```

---

## Load Balancing

### HAProxy Configuration (`config/haproxy.cfg`)

```ini
global
    maxconn 4096
    log stdout local0
    log stdout local1 notice
    chroot /var/lib/haproxy
    user haproxy
    group haproxy
    daemon

defaults
    log global
    mode http
    option httplog
    option denylogin
    option forwardfor except 127.0.0.0/8
    option http-keep-alive
    timeout connect 5000
    timeout client 50000
    timeout server 50000
    errorfile 400 /usr/local/etc/haproxy/errors/400.http

frontend main
    bind *:8080
    bind *:8443 ssl crt /etc/ssl/private/server.pem
    redirect scheme https code 301 if !{ ssl_fc }
    
    default_backend fastapi_backend
    
    # Logging
    log stdout local0 info

backend fastapi_backend
    balance roundrobin
    option httpchk GET /health
    
    server fastapi1 fastapi-1:8000 check inter 5s fall 2 rise 2
    server fastapi2 fastapi-2:8000 check inter 5s fall 2 rise 2
    server fastapi3 fastapi-3:8000 check inter 5s fall 2 rise 2
    
    # Session persistence (optional)
    # cookie SERVERID insert indirect nocache

listen stats
    bind *:8404
    mode http
    stats enable
    stats uri /stats
    stats refresh 30s
```

---

## Monitoring & Failover

### Prometheus Additions (`config/monitoring/prometheus.yml`)

```yaml
scrape_configs:
  - job_name: 'redis-sentinel'
    static_configs:
      - targets:
          - 'localhost:26379'
          - 'localhost:26380'
          - 'localhost:26381'

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-primary:9187']

  - job_name: 'haproxy'
    static_configs:
      - targets: ['haproxy:8404']

alert_rules:
  - alert: RedisMasterDown
    expr: redis_up == 0
    for: 1m
    annotations:
      summary: "Redis master is down"

  - alert: PostgresReplicationLag
    expr: pg_replication_slots_restart_lsn_bytes_lag > 10485760
    for: 5m
    annotations:
      summary: "PostgreSQL replication lag > 10MB"

  - alert: AllBackendsDown
    expr: count(up{job="fastapi"}) == 0
    for: 1m
    annotations:
      summary: "All FastAPI backends are down"
```

### Grafana Dashboard Updates

Add panels for:
- Redis Sentinel master/replica status
- PostgreSQL replication lag timeline
- HAProxy backend availability
- Failover event count
- Recovery time SLA tracking

---

## Implementation Checklist

### Week 1: Redis Sentinel
- [ ] Create sentinel config files (3 instances)
- [ ] Update docker-compose.yml with Redis replicas and Sentinels
- [ ] Build and test Sentinel cluster
- [ ] Update Celery config for Sentinel broker
- [ ] Test manual failover
- [ ] Test network partition recovery
- [ ] Document Sentinel recovery procedures
- [ ] Add Sentinel monitoring to Prometheus

### Week 2: PostgreSQL HA
- [ ] Configure primary PostgreSQL for replication
- [ ] Set up hot standby replica
- [ ] Configure WAL archiving
- [ ] Create automated backup script
- [ ] Test point-in-time recovery
- [ ] Set up replication lag monitoring
- [ ] Document failover procedures
- [ ] Plan and execute failover drill

### Week 3: Load Balancing & Monitoring
- [ ] Create HAProxy configuration
- [ ] Deploy multiple FastAPI instances
- [ ] Configure health check endpoints
- [ ] Test load distribution
- [ ] Add HA metrics to Prometheus
- [ ] Create failover alert rules
- [ ] Update Grafana dashboards
- [ ] Document operational runbook

### Validation Testing
- [ ] Redis master failure → Sentinel promotes replica
- [ ] Sentinel down → Cluster still operational with 2/3
- [ ] Database failover → Application reconnects
- [ ] All backends down → Alert and restore procedure
- [ ] Network partition → Recovery after healing
- [ ] Concurrent failures → Graceful degradation
- [ ] Performance under load → No SLA impact

---

## Success Criteria

✅ **Technical**
- 3-node Redis Sentinel cluster operational
- PostgreSQL streaming replication lag < 100ms
- Automatic failover completes in < 30 seconds
- All monitoring alerts fire correctly
- Load balancer health checks passing

✅ **Operational**
- Failover procedures documented and tested
- Team trained on HA operations
- Incident response plan in place
- Monitoring dashboards updated
- SLA targets met (99.95% uptime)

✅ **Safety**
- No data loss during failover
- Backup restoration verified
- Connection pooling handles failover
- No race conditions in failover logic

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Sentinel split-brain | 3-node quorum, proper configuration |
| Replication lag spikes | Monitor and alert on lag > 10MB |
| Backup corruption | Weekly restore verification |
| Load balancer SPOF | Eventually: Second load balancer in A/A mode |
| Connection pool exhaustion | Configure proper pool sizes |

---

## Next Steps After Phase 5B

1. **Phase 5C**: Kubernetes deployment (container orchestration)
2. **Phase 5D**: Production package (CI/CD automation)
3. **Phase 6**: Cloud provider integration (AWS/GCP/Azure)
4. **Phase 7**: Multi-region replication (disaster recovery)

---

**Document Version:** 1.0  
**Last Updated:** February 2026  
**Next Review:** After Phase 5B.1 completion
