# PHASE 5B IMPLEMENTATION RUNBOOK
## High Availability & Failover - Step-by-Step Deployment Guide

**Status:** Ready for Implementation  
**Estimated Duration:** 2-3 weeks  
**Team Size:** 2-3 engineers  
**Difficulty:** High  

---

## Table of Contents

1. [Pre-Implementation Checklist](#pre-implementation-checklist)
2. [Phase 5B.1: Redis Sentinel Setup](#phase-5b1-redis-sentinel-setup)
3. [Phase 5B.2: PostgreSQL Replication](#phase-5b2-postgresql-replication)
4. [Phase 5B.3: Load Balancer (HAProxy)](#phase-5b3-load-balancer)
5. [Phase 5B.4: Monitoring & Failover](#phase-5b4-monitoring--failover)
6. [Testing & Validation](#testing--validation)
7. [Operational Procedures](#operational-procedures)

---

## Pre-Implementation Checklist

Before starting Phase 5B, ensure:

- [ ] Phase 5A is deployed and stable in staging
- [ ] Load test completed (100+ concurrent jobs)
- [ ] Team trained on distributed system concepts
- [ ] Backup of current data taken
- [ ] Rollback plan documented and tested
- [ ] Monitoring infrastructure ready (Prometheus, Grafana, Alertmanager)
- [ ] All configuration files in place (see: `config/redis`, `config/postgresql`, `config/haproxy`)
- [ ] Docker images built for Redis Sentinel, PostgreSQL replicas, HAProxy
- [ ] Network and storage infrastructure verified

---

## PHASE 5B.1: Redis Sentinel Setup

### Objectives
- Deploy 3-node Sentinel cluster
- Configure Redis master/replica replication
- Test automatic failover
- Integrate with Celery

### Implementation Steps

#### Step 1: Start Redis Master
```bash
docker-compose up -d redis-master
docker-compose logs redis-master

# Verify master is running
docker exec trustwise-redis-master redis-cli ping
# Expected: PONG
```

#### Step 2: Start Redis Replicas
```bash
docker-compose up -d redis-replica-1 redis-replica-2

# Verify replicas are running
docker exec trustwise-redis-replica-1 redis-cli -p 6379 ping
docker exec trustwise-redis-replica-2 redis-cli -p 6379 ping

# Check replication status
docker exec trustwise-redis-master redis-cli INFO replication
# Expected: role:master, connected_slaves:2
```

#### Step 3: Start Sentinel Instances
```bash
docker-compose up -d sentinel-1 sentinel-2 sentinel-3

# Verify Sentinels are running
docker exec trustwise-sentinel-1 redis-cli -p 26379 ping

# Check Sentinel status
docker exec trustwise-sentinel-1 redis-cli -p 26379 sentinel masters
# Expected: Lists 'mymaster' with status 'ok'

# Check replica information
docker exec trustwise-sentinel-1 redis-cli -p 26379 sentinel slaves mymaster
```

#### Step 4: Verify Replication
```bash
# Set a key on master
docker exec trustwise-redis-master redis-cli SET test_key "Hello Sentinel"

# Read from replica (read-only)
docker exec trustwise-redis-replica-1 redis-cli GET test_key
# Expected: "Hello Sentinel"
```

#### Step 5: Test Manual Failover
```bash
# Stop master
docker stop trustwise-redis-master

# Wait 5-10 seconds for Sentinel to detect failure
sleep 10

# Check which replica was promoted
docker exec trustwise-sentinel-1 redis-cli -p 26379 sentinel masters
# Expected: Sentinel shows new master (was replica)

# Connect to promoted replica and verify it's master
docker exec trustwise-redis-replica-1 redis-cli INFO replication
# Expected: role:master (not slave)

# Restart original master as replica
docker start trustwise-redis-master
sleep 5
docker exec trustwise-redis-master redis-cli INFO replication
# Expected: role:slave, master_host: new_master_ip
```

#### Step 6: Update Celery Configuration
```python
# In app/celery_config.py, update Sentinel connection:

from redis.sentinel import Sentinel

sentinel = Sentinel([
    ('sentinel-1', 26379),
    ('sentinel-2', 26380),
    ('sentinel-3', 26381),
])

app.conf.broker_url = 'sentinel://localhost:26379/0'
app.conf.broker_transport_options = {
    'master_name': 'mymaster',
    'sentinel_kwargs': {'password': None},
}
```

#### Step 7: Verify Celery Works with Sentinel
```bash
# Restart Celery workers
docker-compose restart celery-worker-web celery-worker-research celery-worker-vector

# Test task submission
curl -X POST http://localhost:8000/api/v1/jobs/{job_id}/extract/async

# Monitor with Flower
# Should see tasks being processed: http://localhost:5555
```

### Troubleshooting

| Issue | Symptom | Resolution |
|-------|---------|-----------|
| Sentinel won't connect | "Connection refused" | Check Sentinel config, port binding, network |
| Master not syncing | Replica shows `offset:0` | Check replication user credentials, firewall rules |
| Failover doesn't happen | Sentinel masters shows master down but no promotion | Verify quorum=2, sentinel running on 2+ nodes |
| Celery can't find broker | Celery workers crash | Check Sentinel service names in docker-compose, environment vars |

---

## PHASE 5B.2: PostgreSQL Replication

### Objectives
- Setup streaming replication
- Configure hot standby replicas
- Test point-in-time recovery
- Verify data consistency

### Implementation Steps

#### Step 1: Create Replication User
```bash
# Connect to primary
docker exec trustwise-postgres-primary psql -U trustwise -d trustwise_dev -c "
CREATE ROLE replication WITH REPLICATION LOGIN PASSWORD 'replication_password';
"

# Verify
docker exec trustwise-postgres-primary psql -U trustwise -d trustwise_dev -c "
SELECT * FROM pg_user WHERE useraname='replication';
"
```

#### Step 2: Start PostgreSQL Primary
```bash
docker-compose up -d postgres-primary

# Verify primary is running
docker exec trustwise-postgres-primary pg_isready
# Expected: accepting connections
```

#### Step 3: Create Base Backup for Standby
```bash
# Create backup directory
mkdir -p /var/lib/pg_backup

# Create backup as replication user
docker exec trustwise-postgres-primary pg_basebackup \
  -h localhost \
  -U replication \
  -D /var/lib/postgresql/data \
  -v -P \
  -W  # Prompt for password

# This creates the base for standby
```

#### Step 4: Start PostgreSQL Standby Replicas
```bash
docker-compose up -d postgres-standby-1 postgres-standby-2

# Watch logs for streaming replication
docker-compose logs postgres-standby-1

# Verify read-only mode
docker exec trustwise-postgres-standby-1 psql -U trustwise -d trustwise_dev -c "
CREATE TABLE test (id INT);
"
# Expected: ERROR - "server closed the connection unexpectedly"
# This is expected - standby is read-only
```

#### Step 5: Verify Replication Status
```bash
# On primary, check replicas
docker exec trustwise-postgres-primary psql -U trustwise -d trustwise_dev -c "
SELECT slot_name, pg_wal_lsn_diff(slot_restart_lsn, '0/0') AS restart_lsn FROM pg_replication_slots;
"

# Check replica lag (should be < 100MB)
docker exec trustwise-postgres-primary psql -U trustwise -d trustwise_dev -c "
SELECT client_addr, state, sync_state, write_lag, flush_lag, replay_lag FROM pg_stat_replication;
"
```

#### Step 6: Test Data Consistency
```bash
# Insert data on primary
docker exec trustwise-postgres-primary psql -U trustwise -d trustwise_dev -c "
INSERT INTO jobs (id, source_name, status) VALUES ('test-id', 'test-source', 'pending');
"

# Query standby (read-only)
docker exec trustwise-postgres-standby-1 psql -U trustwise -d trustwise_dev -c "
SELECT * FROM jobs WHERE id='test-id';
"
# Expected: Same data visible (eventual consistency)
```

#### Step 7: Configure Backup Strategy
```bash
# Create backup script
cat > scripts/backup-postgres.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/mnt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Full backup
docker exec trustwise-postgres-primary pg_basebackup \
  -h localhost \
  -U replication \
  -D "$BACKUP_DIR/full_$DATE" \
  -v -P \
  -W

# Upload to S3 (optional)
# aws s3 cp "$BACKUP_DIR/full_$DATE" s3://trustwise-backups/ --recursive

# Cleanup old backups
find "$BACKUP_DIR" -name "full_*" -mtime +30 -exec rm -rf {} \;
EOF

# Schedule daily
# 0 2 * * * /app/scripts/backup-postgres.sh
```

### Troubleshooting

| Issue | Symptom | Resolution |
|-------|---------|-----------|
| Replica won't sync | "Streaming replication timeout" | Check network, replication user password, pg_hba.conf |
| Replication lag increasing | `replay_lag` keeps growing | Increase `wal_buffers`, check I/O performance |
| Standby won't start | "FATAL: database files are incompatible" | Delete standby DATA directory, restart replication from scratch |
| Data not visible on standby | Query returns no results | Standby lags behind primary; wait a few seconds and retry |

---

## PHASE 5B.3: Load Balancer (HAProxy)

### Objectives
- Deploy HAProxy load balancer
- Configure health checks
- Route traffic to FastAPI instances
- Test failover behavior

### Implementation Steps

#### Step 1: Create SSL Certificate
```bash
# For development (self-signed)
mkdir -p config/ssl
openssl req -x509 -newkey rsa:4096 \
  -keyout config/ssl/key.pem \
  -out config/ssl/cert.pem \
  -days 365 -nodes \
  -subj "/CN=localhost"

# Combine into server.pem
cat config/ssl/cert.pem config/ssl/key.pem > config/ssl/server.pem

# For production, use Let's Encrypt
# certbot certonly --webroot -w /var/www/letsencrypt -d api.trustwise.com
```

#### Step 2: Start FastAPI Instances
```bash
# Start main FastAPI and create replicas
docker-compose up -d fastapi

# If scaling manually (create fastapi-2, fastapi-3):
# docker-compose run -d -p 8001:8000 fastapi
# docker-compose run -d -p 8002:8000 fastapi

# Or edit docker-compose to add services:
# fastapi-2:
#   ...same as fastapi but container_name: trustwise-fastapi-2
```

#### Step 3: Start HAProxy
```bash
docker-compose up -d haproxy

# Check HAProxy logs
docker-compose logs haproxy

# Verify it's listening
docker exec trustwise-haproxy netstat -tlnp
# Expected: Listening on :80, :443, :8404
```

#### Step 4: Test Health Checks
```bash
# Access HAProxy stats page
curl http://localhost:8404/stats

# In browser: http://localhost:8404/stats
# You should see:
# - FastAPI backends (UP/DOWN)
# - Connection counts
# - Health check status
```

#### Step 5: Route Traffic Through Load Balancer
```bash
# Test HTTP → HTTPS redirect
curl -v http://localhost/health
# Expected: 301 redirect to https://

# Test HTTPS to FastAPI
curl --insecure https://localhost/health
# Expected: 200 OK from FastAPI

# Test API endpoint
curl --insecure -X POST https://localhost/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"source_name": "test"}'
```

#### Step 6: Test Server Removal (Graceful Degradation)
```bash
# Stop one FastAPI instance
docker stop trustwise-fastapi-2

# Wait for health check to fail (should be ~10 seconds)
sleep 15

# Verify HAProxy shows it DOWN in stats
curl http://localhost:8404/stats | grep fastapi2

# Verify further requests still work (go to healthier backend)
curl --insecure https://localhost/health  # Should still work

# Restart it
docker start trustwise-fastapi-2
```

### Troubleshooting

| Issue | Symptom | Resolution |
|-------|---------|-----------|
| 503 Service Unavailable | All backends marked DOWN | Check health endpoint `/health`, verify FastAPI running |
| SSL error | "certificate verify failed" | Use `--insecure` for self-signed, or load real cert |
| Slow response | Requests take 5+ seconds | Check backend CPU/memory, increase worker concurrency |
| Sticky sessions failing | Session lost when hitting different backend | Implement shared session store (Redis) in FastAPI |

---

## PHASE 5B.4: Monitoring & Failover

### Objectives
- Add HA metrics to Prometheus
- Create alerting rules
- Setup failover automation
- Document operational procedures

### Implementation Steps

#### Step 1: Add HA Metrics to Prometheus
```yaml
# config/monitoring/prometheus.yml
scrape_configs:
  - job_name: 'redis-sentinel'
    static_configs:
      - targets:
          - 'localhost:26379'
          - 'localhost:26380'
          - 'localhost:26381'
    metrics_path: '/metrics'

  - job_name: 'postgres'
    static_configs:
      - targets:
          - 'localhost:5432'
    # Requires postgres_exporter

  - job_name: 'haproxy'
    static_configs:
      - targets:
          - 'localhost:8404'
    metrics_path: '/stats;csv'
```

#### Step 2: Create Alert Rules
```yaml
# config/monitoring/alert_rules_ha.yml
groups:
  - name: redis_sentinel_alerts
    interval: 30s
    rules:
      - alert: RedisMasterDown
        expr: redis_up == 0
        for: 1m
        annotations:
          summary: "Redis master is down"
          runbook: "Check redis-master container"

      - alert: SentinelQuorumLost
        expr: count(up{job="redis-sentinel"}) < 2
        for: 1m
        annotations:
          summary: "Lost Sentinel quorum"

  - name: postgres_replication_alerts
    interval: 30s
    rules:
      - alert: PostgreSReplicationLag
        expr: pg_replication_lag > 10485760  # 10MB
        for: 5m
        annotations:
          summary: "PostgreSQL replication lag > 10MB"

      - alert: PostgreSStandbyDown
        expr: count(pg_replicas_active) < 1
        for: 5m
        annotations:
          summary: "No active PostgreSQL replicas"

  - name: haproxy_alerts
    interval: 30s
    rules:
      - alert: HAProxyBackendDown
        expr: haproxy_frontend_current_sessions == 0 and haproxy_backend_up == 0
        for: 2m
        annotations:
          summary: "All HAProxy backends are down"
```

#### Step 3: Create Grafana Dashboards
```bash
# Import JSON dashboard
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @config/monitoring/ha_dashboard.json
```

#### Step 4: Setup Automated Failover
```bash
# For Redis Sentinel: Automatic (no action needed)

# For PostgreSQL: Manual failover script
cat > scripts/pg-failover.sh << 'EOF'
#!/bin/bash
# Promote standby-1 to primary

STANDBY_CONTAINER="trustwise-postgres-standby-1"

echo "Promoting $STANDBY_CONTAINER to primary..."

# Promote standby
docker exec $STANDBY_CONTAINER pg_ctl promote -D /var/lib/postgresql/data

echo "Waiting for promotion to complete..."
sleep 10

# Verify promotion
docker exec $STANDBY_CONTAINER psql -U trustwise -d trustwise_dev -c "SELECT version();"

echo "Standby promoted. Update application connection string to:"
echo "postgresql://trustwise:password@postgres-standby-1:5432/trustwise_db"
EOF

chmod +x scripts/pg-failover.sh
```

#### Step 5: Create Runbook
```bash
# Document in PHASE_5B_OPERATIONAL_RUNBOOK.md what to do if:
# - Redis master fails → Sentinel auto-promotes replica
# - PostgreSQL master fails → Manually run pg-failover.sh
# - HAProxy fails → Access backend directly via port forwarding
# - All backends down → Restart FastAPI, reconfigure load balancer
```

### Troubleshooting

| Issue | Symptom | Resolution |
|-------|---------|-----------|
| Alerts not firing | Prometheus scrape fails | Check exporter installed, port accessible |
| Failover alert but no action | Alerts fire but nothing happens | Setup alertmanager webhooks or PagerDuty |
| False positives | Too many alerts | Tune thresholds, increase `for` duration |

---

## Testing & Validation

### Checklist
- [ ] Redis Sentinel failover test
- [ ] PostgreSQL replica promotion test
- [ ] HAProxy backend removal + recovery
- [ ] Load test (100+ concurrent jobs)
- [ ] Chaos engineering (random component failures)
- [ ] Backup restoration test
- [ ] Network partition recovery

### Load Testing
```bash
# Use Apache Bench or similar
ab -n 1000 -c 100 http://localhost:8000/health

# Or custom script
for i in {1..100}; do
  curl -X POST http://localhost:8000/api/v1/jobs \
    -H "Content-Type: application/json" \
    -d '{"source_name": "load-test-'$i'"}' &
done
wait
```

---

## Operational Procedures

### Daily Operations
```
8:00 AM  - Check monitoring dashboards
10:00 AM - Review error logs
2:00 PM  - Backup verification
5:00 PM  - Health check summary
```

### Weekly Maintenance
```
Monday 9 AM   - Test failover procedures
Tuesday 3 PM  - Backup restoration test
Friday 4 PM   - Capacity planning review
```

### Incident Response
- **Master Down:** Sentinel auto-promotes replica (automatic)
- **Multiple Failures:** Scale back, isolate issue, restore from backup
- **Data Loss:** Restore from backup, point-in-time recovery

---

## Success Criteria

✅ All components deploy successfully  
✅ Failover completes in < 30 seconds  
✅ Zero data loss during failover  
✅ 99.95% uptime SLA achieved  
✅ Monitoring alerts functional  
✅ Operational runbook complete  

---

**Phase 5B Implementation Runbook Complete**  
**Next: Execute implementation steps in sequence**  
**Timeline: 2-3 weeks**
