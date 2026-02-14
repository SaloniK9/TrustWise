import logging
import asyncio
from typing import List, Dict, Any
from app.agents.db_agent import db_agent
from app.agents.vector_agent import vector_agent
from app.agents.web_agent import web_agent
from app.agents.research_agent import research_agent
from app.monitoring import metrics

logger = logging.getLogger(__name__)

AGENT_MAP = {
    "db_check": db_agent,
    "vector_check": vector_agent,
    "web_scrape_if_stale": web_agent,
    "research_lookup": research_agent
}

class Scheduler:
    """
    Dispatcher for parallel agent execution.
    
    Responsibility:
    - Map tasks to agent functions
    - Execute agents in parallel with timeout
    - Collect and return results
    """
    
    async def execute(
        self,
        tasks: List[Dict[str, Any]], 
        trusted_sources: Dict[str, Any],
        timeout_secs: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Execute all tasks in parallel with timeout.
        
        Args:
            tasks: List of task dicts with {"task_id", "agent", "timeout_ms"}
            trusted_sources: Config for agents
            timeout_secs: Overall timeout for all tasks
            
        Returns:
            List of results from all agents
        """
        logger.info(f"Scheduler: Dispatching {len(tasks)} tasks in parallel")
        # metrics: dispatched
        try:
            metrics.increment_tasks_dispatched(len(tasks))
        except Exception:
            pass
        
        # Create coroutines for all tasks
        coroutines = []
        for task in tasks:
            agent_name = task.get("agent")
            agent_fn = AGENT_MAP.get(agent_name)
            
            if not agent_fn:
                logger.warning(f"Unknown agent: {agent_name}")
                continue
            
            # Wrap with timeout per task
            task_timeout = task.get("timeout_ms", 10000) / 1000.0
            coroutine = asyncio.wait_for(
                agent_fn(trusted_sources),
                timeout=task_timeout
            )
            coroutines.append(coroutine)
        
        # Execute all in parallel with overall timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*coroutines, return_exceptions=True),
                timeout=timeout_secs
            )
            
            # Handle exceptions from gather
            clean_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Task {i} failed: {result}")
                    try:
                        metrics.increment_tasks_failed(1)
                    except Exception:
                        pass
                    clean_results.append({
                        "status": "failed",
                        "error": str(result),
                        "confidence": 0.0
                    })
                else:
                    clean_results.append(result)
            
            logger.info(f"Scheduler: Completed {len(clean_results)} tasks")
            return clean_results
            
        except asyncio.TimeoutError:
            logger.error(f"Scheduler: Overall timeout ({timeout_secs}s) exceeded")
            return []
        except Exception as e:
            logger.error(f"Scheduler: Execution failed - {e}")
            return []


