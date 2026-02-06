"""
Data extraction module for TrustWise.

Provides multiple extraction strategies:
- Web scraping with BeautifulSoup4
- Vector database integration
- Research API access (ArXiv, IEEE Xplore)
- Database queries
"""

from .web_scraper import WebScraper
from .vector_db import VectorDatabase
from .research_api import ResearchAPIClient
from .base import BaseExtractor

__all__ = [
    "WebScraper",
    "VectorDatabase",
    "ResearchAPIClient",
    "BaseExtractor",
]
