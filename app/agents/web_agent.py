
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def web_agent(trusted_sources: dict) -> dict:
    """Scrape data from trusted web sources."""
    try:
        logger.info("web_agent: Fetching from web sources...")
        
        allowed_domains = {
            src["domain"]: src["trust_score"]
            for src in trusted_sources.get("web_sources", [])
        }
        
        fetched_domain = "arxiv.org"
        
        if fetched_domain not in allowed_domains:
            logger.warning(f"web_agent: Domain {fetched_domain} not whitelisted")
            return {
                "source": fetched_domain,
                "status": "blocked",
                "data": None,
                "confidence": 0.0,
                "error": "Untrusted domain"
            }
        
        result = {
            "source": fetched_domain,
            "status": "success",
            "data": "Validated data from ArXiv",
            "confidence": allowed_domains[fetched_domain],
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        logger.info("web_agent: Completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"web_agent: Failed - {e}")
        return {
            "source": "web",
            "status": "failed",
            "error": str(e),
            "confidence": 0.0
        }
