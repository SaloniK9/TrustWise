import logging
import json
from pathlib import Path
from typing import Dict, Optional
from app.orchestrator.planner import Planner
from app.orchestrator.chunker import Chunker
from app.orchestrator.scheduler import Scheduler
from app.orchestrator.trust_engine import TrustEngine

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Central orchestrator that manages query execution.
    
    Architecture:
    1. Planner:      Creates execution plan from strategy
    2. Chunker:      Breaks plan into parallel tasks
    3. Scheduler:    Dispatches tasks to agents
    4. TrustEngine:  Verifies & aggregates results
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize orchestrator.
        
        Args:
            config_path: Path to trusted_sources.json
        """
        logger.info("Initializing Orchestrator...")
        
        self.planner = Planner()
        self.chunker = Chunker()
        self.scheduler = Scheduler()
        self.trust_engine = TrustEngine()
        
        # Load trusted sources config
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "trusted_sources.json"
        else:
            config_path = Path(config_path)
        
        self.trusted_sources = self._load_config(config_path)
        logger.info(f"Loaded {len(self.trusted_sources.get('web_sources', []))} trusted sources")
    
    def _load_config(self, path: Path) -> Dict:
        """Load trusted sources configuration safely."""
        try:
            if not path.exists():
                logger.error(f"Config file not found: {path}")
                raise FileNotFoundError(f"Config file not found: {path}")
            
            with open(path, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Loaded config from {path}")
            return config
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config: {e}")
            raise
    
    async def handle_query(self, query: str) -> Dict:
        """Process a query through the full pipeline."""
        logger.info(f"Processing query: {query[:50]}...")
        
        try:
            plan = self.planner.create_plan(query)
            logger.debug(f"Created plan with {len(plan)} steps")
            
            tasks = self.chunker.chunk(plan)
            logger.debug(f"Chunked into {len(tasks)} tasks")
            
            results = await self.scheduler.execute(tasks, self.trusted_sources)
            logger.debug(f"Got {len(results)} results from agents")
            
            verified = self.trust_engine.verify(results)
            logger.info(f"Verified {len(verified)} trusted results")
            
            return verified
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            raise
