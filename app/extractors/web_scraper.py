"""
Web scraper implementation using httpx and BeautifulSoup4.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib

import httpx
from bs4 import BeautifulSoup

from .base import BaseExtractor

logger = logging.getLogger(__name__)

# URL cache to avoid duplicate scrapes
_url_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600


class WebScraper(BaseExtractor):
    """Web scraper using httpx and BeautifulSoup4."""

    def __init__(
        self,
        name: str = "WebScraper",
        timeout: int = 10,
        max_retries: int = 3,
        user_agent: Optional[str] = None,
    ):
        """
        Initialize web scraper.

        Args:
            name: Scraper name
            timeout: Default request timeout
            max_retries: Maximum retry attempts
            user_agent: Custom User-Agent header
        """
        super().__init__(name, "web")
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = (
            user_agent or "TrustWise/1.0 (+https://github.com/yourrepo)"
        )
        self.client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self.client

    async def validate(self) -> bool:
        """Validate scraper by testing connectivity."""
        try:
            client = await self._get_client()
            response = await client.head("https://httpbin.org/get", timeout=5)
            return response.status_code < 400
        except Exception as e:
            logger.error(f"Web scraper validation failed: {e}")
            return False

    async def extract(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Extract data by scraping a URL.

        Args:
            query: URL to scrape
            filters: Optional filters for parsing
            timeout: Request timeout

        Returns:
            Standardized response with extracted data
        """
        timeout = timeout or self.timeout
        filters = filters or {}

        # Check cache
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in _url_cache:
            cached = _url_cache[cache_key]
            age = (datetime.utcnow() - cached["cached_at"]).total_seconds()
            if age < CACHE_TTL_SECONDS:
                logger.info(f"Cache hit for {query}")
                cached["data"]["_cached"] = True
                return cached["response"]

        try:
            # Fetch with retries
            html = await self._fetch_with_retry(query, timeout)
            if not html:
                return self._build_response(
                    [],
                    status="error",
                    trust_score=0,
                    error="Failed to fetch URL after retries",
                )

            # Parse HTML
            data = await self._parse_html(html, filters)

            # Cache result
            response = self._build_response(
                data, status="success", trust_score=0.85
            )
            _url_cache[cache_key] = {
                "cached_at": datetime.utcnow(),
                "response": response,
            }

            logger.info(f"Successfully extracted {len(data)} items from {query}")
            return response

        except asyncio.TimeoutError:
            return self._build_response(
                [],
                status="error",
                trust_score=0,
                error=f"Request timeout after {timeout}s",
            )
        except Exception as e:
            logger.error(f"Extraction error for {query}: {e}")
            return self._build_response(
                [],
                status="error",
                trust_score=0,
                error=str(e),
            )

    async def _fetch_with_retry(
        self, url: str, timeout: int
    ) -> Optional[str]:
        """
        Fetch URL with exponential backoff retry logic.

        Args:
            url: URL to fetch
            timeout: Request timeout

        Returns:
            HTML content or None if all retries fail
        """
        client = await self._get_client()
        backoff = 1

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching {url} (attempt {attempt + 1})")
                response = await client.get(url, timeout=timeout)
                response.raise_for_status()
                return response.text

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # Rate limited
                    wait_time = backoff * 2
                    logger.warning(
                        f"Rate limited. Waiting {wait_time}s before retry..."
                    )
                    await asyncio.sleep(wait_time)
                    backoff *= 2
                elif e.response.status_code >= 500:  # Server error
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(f"HTTP error {e.response.status_code}")
                    return None

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(f"Connection error after retries: {e}")
                    raise

        return None

    async def _parse_html(
        self, html: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Parse HTML content.

        Args:
            html: HTML content
            filters: Optional CSS selectors

        Returns:
            List of extracted data items
        """
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._parse_html_sync, html, filters)

    @staticmethod
    def _parse_html_sync(
        html: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Synchronous HTML parsing."""
        soup = BeautifulSoup(html, "html.parser")
        data = []

        # Basic extraction: get all paragraphs and headings
        selector = filters.get("selector", "p, h1, h2, h3, h4, h5, h6")
        elements = soup.select(selector)

        for elem in elements:
            text = elem.get_text(strip=True)
            if text:
                data.append({
                    "type": elem.name,
                    "text": text,
                    "length": len(text),
                })

        return data[:100]  # Limit to 100 items

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
