# Phase 4 — Operational Runbook

**Date:** February 12, 2026  
**Status:** ✅ Phase 4 Monitoring Stack Deployed

## Overview

Phase 4 provides production-grade monitoring, alerting, and operational readiness for TrustWise. This runbook documents:
- Monitoring stack deployment (Prometheus, Grafana, Alertmanager)
- Key metrics and alerts
- Troubleshooting common issues
- Operational tasks

## Deployment

### Start Monitoring Stack

```bash
# Start all services including monitoring
docker-compose up -d

# Verify all services are running
docker-compose ps

# Expected output:
# CONTAINER ID  IMAGE                           STATUS
# postgres      postgres:15-alpine              Up (healthy)
# pgadmin       dpage/pgadmin4:latest           Up
# prometheus    prom/prometheus:latest          Up
# grafana       grafana/grafana:latest          Up
# alertmanager  prom/alertmanager:latest        Up
```

### Access Monitoring Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Prometheus** | http://localhost:9090 | (none) |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Alertmanager** | http://localhost:9093 | (none) |
| **App Metrics** | http://localhost:8000/metrics | (none) |

## Metrics & Dashboards

### Key Metrics

**Job Metrics:**
- `trustwise_jobs_running` — Current number of jobs executing
- `trustwise_jobs_started_total` — Total jobs started (per source)
- `trustwise_jobs_completed_total` — Total jobs completed (per source, per status)
- `trustwise_job_duration_seconds` — Histogram of job execution time

**Task Metrics:**
- `trustwise_tasks_dispatched_total` — Total tasks sent to agents
- `trustwise_tasks_failed_total` — Total task failures

### Grafana Dashboard

1. Navigate to http://localhost:3000 (admin / admin)
2. Click **Home** → **Dashboards** → **TrustWise - Jobs & Scheduler**
3. Monitor 3 key panels:
   - Jobs Running (gauge)
   - Job Duration p95 (histogram)
   - Tasks Dispatched vs Failed (rate)

## Alerts

### Alert Rules

Located in `config/monitoring/prometheus_rules.yml`:

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| `JobFailureRateHigh` | >20% jobs failed in 5m | Warning | Review failed jobs in app logs |
| `JobBacklogHigh` | >100 jobs running | Warning | Scale workers or investigate bottleneck |
| `SchedulerIdle` | No tasks dispatched in 10m | Critical | Restart scheduler/app |
| `TasksFailing` | >5 task failures in 5m | Warning | Check agent health / logs |

### Alert Notifications

Alerts are sent to Alertmanager (http://localhost:9093). Currently configured for local webhooks.

To enable Slack/PagerDuty/Email, update `config/monitoring/alertmanager.yml`:

```yaml
receivers:
  - name: 'critical'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#ops'
        title: 'TrustWise Alert'
```

## Health Checks

### Readiness Probe

```bash
curl http://localhost:8000/ready
# Returns 200 if DB is connected, 503 otherwise
```

**Use for:** Pre-traffic check before routing requests (Kubernetes, load balancers)

### Liveness Probe

```bash
curl http://localhost:8000/live
# Returns 200 if scheduler is running, 503 otherwise
```

**Use for:** Container restart trigger if scheduler dies

### Metrics Endpoint

```bash
curl http://localhost:8000/metrics
# Returns Prometheus format metrics
```

## Troubleshooting

### Issue: "Scheduler is down" alert fires

**Cause:** Task dispatcher hasn't sent any tasks in 10 minutes (app idle)

**Resolution:**
1. Check if jobs exist: `curl http://localhost:8000/jobs?limit=1`
2. If no jobs, create one: `curl -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d '{"source_name":"arxiv"}'`
3. If scheduler stuck, restart: `docker-compose restart` (or rely on liveness probe)

### Issue: High job failure rate

**Cause:** One or more extractors failing (web scraper, research API, vector DB)

**Resolution:**
1. Check extractor health: `curl http://localhost:8000/extractors/health`
2. View failed jobs: `curl http://localhost:8000/jobs?status=failed&limit=10`
3. Check app logs: `docker-compose logs trustwise-app | grep ERROR`
4. Common causes:
   - Network/firewall blocking scraper
   - Research API rate limits exceeded
   - Vector DB connection lost
   - Database disk full

### Issue: Prometheus not collecting metrics

**Cause:** App metrics endpoint down or misconfigured

**Resolution:**
1. Test metrics endpoint: `curl http://localhost:8000/metrics`
2. Check Prometheus targets: http://localhost:9090/targets
3. If target is "down", verify app is running: `docker-compose ps`
4. Check Prometheus logs: `docker-compose logs prometheus`

### Issue: Grafana dashboard has no data

**Cause:** Prometheus not scraping data yet (or dashboard misconfigured)

**Resolution:**
1. Wait 30+ seconds for first scrape (scrape_interval: 10s in prometheus.yml)
2. Go to Prometheus UI (http://localhost:9090) and execute a query: `trustwise_jobs_running`
3. If query returns no results, check app metrics endpoint is responsive
4. If data exists in Prometheus, re-import Grafana dashboard from `config/monitoring/grafana_dashboard.json`

## Maintenance Tasks

### Daily
- Monitor alerts in Alertmanager (http://localhost:9093)
- Spot-check Grafana dashboard for anomalies

### Weekly
- Review failed jobs report: `SELECT COUNT(*) FROM job WHERE status='failed' AND created_at > NOW() - interval '7 days';`
- Check if any sources are consistently failing and triage

### Monthly
- Prune old jobs and extracted_data (keep last 90 days):
  ```sql
  DELETE FROM extracted_data WHERE extracted_at < NOW() - interval '90 days';
  DELETE FROM job WHERE created_at < NOW() - interval '90 days' AND status IN ('success', 'failed');
  ```
- Review alert rules in `config/monitoring/prometheus_rules.yml` and adjust thresholds if needed

## Scaling (Phase 5+)

For higher throughput, consider:

1. **Celery + Redis workers** — Run multiple worker processes
2. **Kubernetes** — Deploy with Helm, add HPA (Horizontal Pod Autoscaling)
3. **Alert routing** — Send critical alerts to PagerDuty for on-call rotation
4. **Backup** — Use `pg_dump` for PostgreSQL backups, Prometheus snapshots for metrics archive

---

**Status:** Phase 4 complete. Ready for Phase 5 (Scaling).
