"""
Base extractor class defining interface for all data extraction strategies.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """Abstract base class for all extractors."""

    def __init__(self, name: str, source_type: str):
        """
        Initialize extractor.

        Args:
            name: Extractor name
            source_type: Type of source (web, vector, research, database)
        """
        self.name = name
        self.source_type = source_type
        self.last_error: Optional[str] = None

    @abstractmethod
    async def extract(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """
        Extract data from source.

        Args:
            query: Search query or identifier
            filters: Optional filters for the query
            timeout: Request timeout in seconds

        Returns:
            Dictionary with:
                - 'data': Extracted data (list or dict)
                - 'status': 'success' or 'error'
                - 'source': Source name
                - 'extracted_at': Extraction timestamp
                - 'trust_score': 0-1 confidence value
                - 'error': Error message if status='error'
        """
        pass

    @abstractmethod
    async def validate(self) -> bool:
        """
        Validate extractor connectivity and configuration.

        Returns:
            True if extractor is ready, False otherwise
        """
        pass

    def _build_response(
        self,
        data: List[Dict[str, Any]],
        status: str = "success",
        trust_score: float = 0.8,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build standardized response dictionary.

        Args:
            data: Extracted data
            status: 'success' or 'error'
            trust_score: Confidence level 0-1
            error: Error message if failed

        Returns:
            Standardized response dict
        """
        response = {
            "data": data,
            "status": status,
            "source": self.name,
            "extracted_at": datetime.utcnow().isoformat(),
            "trust_score": trust_score,
        }
        if error:
            response["error"] = error
            self.last_error = error
        return response

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health status dict
        """
        is_valid = await self.validate()
        return {
            "source": self.name,
            "type": self.source_type,
            "status": "healthy" if is_valid else "unhealthy",
            "last_error": self.last_error,
        }
