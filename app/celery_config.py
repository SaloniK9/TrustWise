"""
Celery Configuration for TrustWise

Distributed task queue for parallel job processing across multiple workers.
Enables horizontal scaling of extraction jobs.

Configuration:
- Broker: Redis (default localhost:6379)
- Backend: Redis
- Task serialization: JSON
- Task routing: By extraction type
- Retry policy: 3 attempts with exponential backoff
"""

import os
from kombu import Exchange, Queue
from celery import Celery

# Create Celery app
app = Celery("trustwise")

# Load config from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_BROKER = os.getenv("REDIS_BROKER", os.getenv("CELERY_BROKER_URL", REDIS_URL))
REDIS_BACKEND = os.getenv("REDIS_BACKEND", os.getenv("CELERY_RESULT_BACKEND", REDIS_URL))

REDIS_SENTINEL_HOSTS = os.getenv("REDIS_SENTINEL_HOSTS", "")
REDIS_SENTINEL_MASTER = os.getenv("REDIS_SENTINEL_MASTER", "mymaster")

sentinel_nodes = []
if REDIS_SENTINEL_HOSTS:
    for entry in REDIS_SENTINEL_HOSTS.split(","):
        host_port = entry.strip()
        if not host_port:
            continue
        if ":" in host_port:
            host, port_str = host_port.split(":", 1)
            sentinel_nodes.append((host.strip(), int(port_str)))
        else:
            sentinel_nodes.append((host_port, 26379))

CELERY_BROKER_URL = REDIS_BROKER
CELERY_RESULT_BACKEND = REDIS_BACKEND

if sentinel_nodes and not CELERY_BROKER_URL.startswith("sentinel://"):
    primary_host, primary_port = sentinel_nodes[0]
    CELERY_BROKER_URL = f"sentinel://{primary_host}:{primary_port}/0"

if sentinel_nodes and not CELERY_RESULT_BACKEND.startswith("sentinel://"):
    primary_host, primary_port = sentinel_nodes[0]
    CELERY_RESULT_BACKEND = f"sentinel://{primary_host}:{primary_port}/1"

# Configure Celery
app.conf.update(
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minute task timeout
    task_soft_time_limit=25 * 60,  # 25 minute soft timeout
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=1000,  # Recycle worker after 1000 tasks
)

if sentinel_nodes:
    app.conf.broker_transport_options = {
        "master_name": REDIS_SENTINEL_MASTER,
        "sentinels": sentinel_nodes,
    }
    app.conf.result_backend_transport_options = {
        "master_name": REDIS_SENTINEL_MASTER,
        "sentinels": sentinel_nodes,
    }

# Define task routing
default_exchange = Exchange("trustwise", type="direct")
default_queue = Queue(
    "default",
    exchange=default_exchange,
    routing_key="default",
)

extraction_exchange = Exchange("extraction", type="direct")
extraction_queues = {
    "web": Queue(
        "extraction.web",
        exchange=extraction_exchange,
        routing_key="extraction.web",
    ),
    "research": Queue(
        "extraction.research",
        exchange=extraction_exchange,
        routing_key="extraction.research",
    ),
    "vector": Queue(
        "extraction.vector",
        exchange=extraction_exchange,
        routing_key="extraction.vector",
    ),
}

app.conf.task_queues = (default_queue, *extraction_queues.values())
app.conf.task_default_queue = "default"
app.conf.task_default_exchange = "trustwise"
app.conf.task_default_routing_key = "default"

# Task routing map
app.conf.task_routes = {
    "app.tasks.extract_web": {"queue": "extraction.web", "routing_key": "extraction.web"},
    "app.tasks.extract_research": {
        "queue": "extraction.research",
        "routing_key": "extraction.research",
    },
    "app.tasks.extract_vector": {
        "queue": "extraction.vector",
        "routing_key": "extraction.vector",
    },
    "app.tasks.schedule_job": {"queue": "default"},
}

# Retry policy
app.conf.task_autoretry_for = (Exception,)
app.conf.task_max_retries = 3
app.conf.task_default_retry_delay = 60  # 1 minute

if __name__ == "__main__":
    app.start()
