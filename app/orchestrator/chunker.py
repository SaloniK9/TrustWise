import uuid
import logging

logger = logging.getLogger(__name__)

# Realistic timeouts per agent type (milliseconds)
TIMEOUT_BY_AGENT = {
    "db_check": 5000,              # 5 seconds for database
    "vector_check": 3000,          # 3 seconds for vector search
    "web_scrape_if_stale": 10000,  # 10 seconds for web scraping
    "research_lookup": 15000       # 15 seconds for research
}

class Chunker:
    """Break execution plan into parallel tasks."""
    
    def chunk(self, plan_steps: list) -> list:
        """Convert plan steps into executable tasks."""
        tasks = []
        for step in plan_steps:
            timeout_ms = TIMEOUT_BY_AGENT.get(step, 10000)
            task = {
                "task_id": str(uuid.uuid4()),
                "agent": step,
                "timeout_ms": timeout_ms
            }
            tasks.append(task)
            logger.debug(f"Created task {task['task_id']} for {step} ({timeout_ms}ms timeout)")
        
        logger.info(f"Chunked {len(plan_steps)} steps into {len(tasks)} tasks")
        return tasks
