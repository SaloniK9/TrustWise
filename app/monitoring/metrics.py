import time
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Job-level metrics
jobs_started = Counter(
    "trustwise_jobs_started_total",
    "Total number of jobs started",
    ["source"],
)

jobs_completed = Counter(
    "trustwise_jobs_completed_total",
    "Total number of jobs completed",
    ["source", "status"],
)

jobs_running = Gauge("trustwise_jobs_running", "Number of jobs currently running")

job_duration_seconds = Histogram(
    "trustwise_job_duration_seconds",
    "Job execution duration in seconds",
    ["source"],
)

# Scheduler/task-level metrics
tasks_dispatched = Counter("trustwise_tasks_dispatched_total", "Number of tasks dispatched")
tasks_failed = Counter("trustwise_tasks_failed_total", "Number of dispatched tasks that failed")


def job_start(source: str) -> float:
    """Mark job start and return start timestamp."""
    try:
        jobs_running.inc()
        jobs_started.labels(source=source).inc()
    except Exception:
        pass
    return time.time()


def job_finish(source: str, status: str, start_ts: float) -> None:
    """Mark job completion and observe duration."""
    try:
        jobs_running.dec()
        jobs_completed.labels(source=source, status=status).inc()
        job_duration_seconds.labels(source=source).observe(max(0.0, time.time() - start_ts))
    except Exception:
        pass


def increment_tasks_dispatched(n: int = 1) -> None:
    try:
        tasks_dispatched.inc(n)
    except Exception:
        pass


def increment_tasks_failed(n: int = 1) -> None:
    try:
        tasks_failed.inc(n)
    except Exception:
        pass


def metrics_as_response() -> (bytes, str):
    """Return (body, content_type) for the Prometheus /metrics response."""
    return generate_latest(), CONTENT_TYPE_LATEST
