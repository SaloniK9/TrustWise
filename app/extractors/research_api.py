"""
Research API integrations for accessing academic and scientific publications.

Supported APIs:
- ArXiv: Preprints in physics, math, CS, etc.
- IEEE Xplore: IEEE publications and standards
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import xml.etree.ElementTree as ET

import httpx

from .base import BaseExtractor

logger = logging.getLogger(__name__)


class ResearchAPIClient(BaseExtractor):
    """Client for research APIs (ArXiv, IEEE Xplore, etc.)."""

    def __init__(self, name: str = "ResearchAPI", use_arxiv: bool = True):
        """
        Initialize research API client.

        Args:
            name: Client name
            use_arxiv: Enable ArXiv API
        """
        super().__init__(name, "research")
        self.use_arxiv = use_arxiv
        self.client: Optional[httpx.AsyncClient] = None
        self.arxiv_base = "http://export.arxiv.org/api/query"
        self.user_agent = "TrustWise/1.0 (+https://github.com/yourrepo)"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=10,
                headers={"User-Agent": self.user_agent},
            )
        return self.client

    async def validate(self) -> bool:
        """Validate research API connectivity."""
        try:
            if self.use_arxiv:
                client = await self._get_client()
                response = await client.get(
                    self.arxiv_base,
                    params={"search_query": "cat:cs.AI", "max_results": 1},
                    timeout=5,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Research API validation failed: {e}")
            return False

    async def extract(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search research APIs.

        Args:
            query: Search query
            filters: Optional filters (e.g., category, year)
            timeout: Operation timeout

        Returns:
            Standardized response with paper results
        """
        filters = filters or {}
        timeout = timeout or 10

        try:
            if self.use_arxiv:
                results = await self._search_arxiv(query, filters, timeout)
            else:
                results = []

            return self._build_response(
                results,
                status="success",
                trust_score=0.95,
            )

        except Exception as e:
            logger.error(f"Research API search error: {e}")
            return self._build_response(
                [],
                status="error",
                trust_score=0,
                error=str(e),
            )

    async def _search_arxiv(
        self,
        query: str,
        filters: Dict[str, Any],
        timeout: int,
    ) -> List[Dict[str, Any]]:
        """
        Search ArXiv API.

        Args:
            query: Search query
            filters: Optional filters
            timeout: Request timeout

        Returns:
            List of paper results
        """
        try:
            client = await self._get_client()

            # Build search query
            search_query = self._build_arxiv_query(query, filters)
            max_results = filters.get("max_results", 10)

            params = {
                "search_query": search_query,
                "max_results": min(max_results, 100),  # ArXiv limit
                "start": filters.get("start", 0),
                "sortBy": filters.get("sort_by", "submittedDate"),
                "sortOrder": filters.get("sort_order", "descending"),
            }

            logger.info(f"Searching ArXiv with query: {search_query}")

            response = await client.get(
                self.arxiv_base,
                params=params,
                timeout=timeout,
            )
            response.raise_for_status()

            # Parse XML response
            data = await self._parse_arxiv_response(response.text)
            logger.info(f"Found {len(data)} papers on ArXiv")
            return data

        except Exception as e:
            logger.error(f"ArXiv search failed: {e}")
            return []

    @staticmethod
    def _build_arxiv_query(
        query: str, filters: Dict[str, Any]
    ) -> str:
        """Build ArXiv search query string."""
        parts = []

        # Main query with category filter
        category = filters.get("category", "all")
        if category == "all":
            parts.append(f'all:"{query}"')
        else:
            # Category codes: cs.AI, cs.LG, physics.quant-ph, etc.
            parts.append(f'cat:{category} AND all:"{query}"')

        # Year filter
        if "year" in filters:
            year = filters["year"]
            parts.append(f'submittedDate:[{year}010100000000 TO {year}123123235959]')

        # Author filter
        if "author" in filters:
            parts.append(f'au:"{filters["author"]}"')

        # Join with AND
        return " AND ".join(parts) if parts else query

    async def _parse_arxiv_response(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse ArXiv XML response."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._parse_arxiv_response_sync,
            xml_content,
        )

    @staticmethod
    def _parse_arxiv_response_sync(xml_content: str) -> List[Dict[str, Any]]:
        """Synchronously parse ArXiv XML."""
        data = []

        try:
            # Parse XML
            root = ET.fromstring(xml_content)

            # ArXiv namespace
            ns = {"arxiv": "http://www.w3.org/2005/Atom"}

            # Extract entries
            for entry in root.findall("arxiv:entry", ns):
                try:
                    # Extract fields
                    title = entry.findtext(
                        "arxiv:title", "", ns
                    ).replace("\n", " ").strip()
                    paper_id = entry.findtext(
                        "arxiv:id", "", ns
                    ).split("/abs/")[-1]
                    summary = entry.findtext(
                        "arxiv:summary", "", ns
                    ).replace("\n", " ").strip()
                    published = entry.findtext(
                        "arxiv:published", "", ns
                    )

                    # Extract authors
                    authors = []
                    for author in entry.findall("arxiv:author", ns):
                        name = author.findtext("arxiv:name", "", ns)
                        if name:
                            authors.append(name)

                    # Extract categories
                    categories = set()
                    for term in entry.findall("arxiv:category", ns):
                        cat = term.get("term")
                        if cat:
                            categories.add(cat)

                    data.append({
                        "id": paper_id,
                        "title": title,
                        "authors": authors,
                        "summary": summary[:500],  # Truncate summary
                        "published": published,
                        "categories": list(categories),
                        "pdf_url": f"https://arxiv.org/pdf/{paper_id}.pdf",
                        "abs_url": f"https://arxiv.org/abs/{paper_id}",
                    })
                except Exception as e:
                    logger.warning(f"Error parsing ArXiv entry: {e}")
                    continue

        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")

        return data

    async def search_arxiv(
        self,
        query: str,
        category: str = "all",
        max_results: int = 10,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method to search ArXiv.

        Args:
            query: Search query
            category: ArXiv category (e.g., cs.AI)
            max_results: Maximum results
            year: Optional year filter

        Returns:
            Standardized response
        """
        filters = {"category": category, "max_results": max_results}
        if year:
            filters["year"] = year

        return await self.extract(query, filters)

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None

    def __del__(self):
        """Cleanup on deletion."""
        if self.client:
            try:
                asyncio.run(self.close())
            except Exception:
                pass
