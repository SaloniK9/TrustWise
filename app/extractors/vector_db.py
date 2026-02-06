"""
Vector database integration for semantic search.

Supports multiple backends:
- Chroma (local, Python)
- Pinecone (cloud-hosted, API)
- Weaviate (self-hosted or cloud)

Uses sentence-transformers for embeddings.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import os

from .base import BaseExtractor

logger = logging.getLogger(__name__)


class VectorDatabase(BaseExtractor):
    """Vector database integration for semantic search."""

    def __init__(
        self,
        name: str = "VectorDB",
        backend: str = "chroma",
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize vector database.

        Args:
            name: Database name
            backend: Backend type (chroma, pinecone, weaviate)
            embedding_model: Model for embeddings
        """
        super().__init__(name, "vector")
        self.backend = backend.lower()
        self.embedding_model = embedding_model
        self.db = None
        self.embeddings = None

    async def _initialize(self):
        """Initialize vector database backend."""
        if self.backend == "chroma":
            await self._init_chroma()
        elif self.backend == "pinecone":
            await self._init_pinecone()
        elif self.backend == "weaviate":
            await self._init_weaviate()
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    async def _init_chroma(self):
        """Initialize Chroma (local embedding DB)."""
        try:
            import chromadb
            # Import embeddings in async context
            from sentence_transformers import SentenceTransformer

            loop = asyncio.get_event_loop()
            self.embeddings = await loop.run_in_executor(
                None,
                SentenceTransformer,
                self.embedding_model,
            )

            # Chroma client (local)
            self.db = chromadb.Client()
            logger.info(f"Chroma initialized with model {self.embedding_model}")
        except ImportError:
            logger.error("Chroma or sentence-transformers not installed")
            raise

    async def _init_pinecone(self):
        """Initialize Pinecone (cloud vector DB)."""
        try:
            import pinecone
            from sentence_transformers import SentenceTransformer

            api_key = os.getenv("PINECONE_API_KEY")
            environment = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")

            if not api_key:
                raise ValueError("PINECONE_API_KEY not set")

            loop = asyncio.get_event_loop()
            self.embeddings = await loop.run_in_executor(
                None,
                SentenceTransformer,
                self.embedding_model,
            )

            pinecone.init(api_key=api_key, environment=environment)
            self.db = pinecone.Index("trustwise-index")
            logger.info("Pinecone initialized")
        except ImportError:
            logger.error("Pinecone or sentence-transformers not installed")
            raise

    async def _init_weaviate(self):
        """Initialize Weaviate vector search."""
        try:
            import weaviate
            from sentence_transformers import SentenceTransformer

            weaviate_url = os.getenv("WEAVIATE_URL", "http://localhost:8080")

            loop = asyncio.get_event_loop()
            self.embeddings = await loop.run_in_executor(
                None,
                SentenceTransformer,
                self.embedding_model,
            )

            self.db = weaviate.Client(weaviate_url)
            logger.info(f"Weaviate initialized at {weaviate_url}")
        except ImportError:
            logger.error("Weaviate or sentence-transformers not installed")
            raise

    async def validate(self) -> bool:
        """Validate vector database connectivity."""
        try:
            if not self.db:
                await self._initialize()
            return self.db is not None
        except Exception as e:
            logger.error(f"Vector DB validation failed: {e}")
            return False

    async def extract(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search vector database with semantic search.

        Args:
            query: Search query text
            filters: Optional metadata filters
            timeout: Operation timeout

        Returns:
            Standardized response with search results
        """
        filters = filters or {}

        try:
            if not self.db:
                await self._initialize()

            # Generate query embedding
            loop = asyncio.get_event_loop()
            query_embedding = await loop.run_in_executor(
                None,
                lambda: self.embeddings.encode(query),
            )

            # Search based on backend
            if self.backend == "chroma":
                results = await self._search_chroma(query_embedding, filters)
            elif self.backend == "pinecone":
                results = await self._search_pinecone(query_embedding, filters)
            elif self.backend == "weaviate":
                results = await self._search_weaviate(query, filters)
            else:
                results = []

            return self._build_response(
                results,
                status="success",
                trust_score=0.9,
            )

        except Exception as e:
            logger.error(f"Vector DB search error: {e}")
            return self._build_response(
                [],
                status="error",
                trust_score=0,
                error=str(e),
            )

    async def _search_chroma(
        self,
        embedding: List[float],
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Search Chroma database."""
        try:
            collection = self.db.get_or_create_collection(
                name="trustwise-data"
            )
            results = collection.query(
                query_embeddings=[embedding],
                n_results=10,
                where=filters if filters else None,
            )

            # Format results
            data = []
            if results and results["documents"]:
                for doc, distance in zip(
                    results["documents"][0], results["distances"][0]
                ):
                    data.append({
                        "text": doc,
                        "similarity": 1 - distance,  # Convert distance to similarity
                    })
            return data
        except Exception as e:
            logger.error(f"Chroma search failed: {e}")
            return []

    async def _search_pinecone(
        self,
        embedding: List[float],
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Search Pinecone database."""
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.db.query(
                    vector=embedding,
                    top_k=10,
                    filter=filters if filters else None,
                    include_metadata=True,
                ),
            )

            # Format results
            data = []
            for match in results.get("matches", []):
                data.append({
                    "id": match.get("id"),
                    "text": match.get("metadata", {}).get("text", ""),
                    "similarity": match.get("score"),
                })
            return data
        except Exception as e:
            logger.error(f"Pinecone search failed: {e}")
            return []

    async def _search_weaviate(
        self,
        query: str,
        filters: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Search Weaviate database."""
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.db.query.get(
                    "Document",
                    ["text", "source", "_additional {certainty}"],
                ).with_text_filter(
                    query
                ).with_limit(10).do(),
            )

            # Format results
            data = []
            for obj in results.get("data", {}).get("Get", {}).get("Document", []):
                data.append({
                    "text": obj.get("text"),
                    "source": obj.get("source"),
                    "certainty": obj.get("_additional", {}).get("certainty"),
                })
            return data
        except Exception as e:
            logger.error(f"Weaviate search failed: {e}")
            return []

    async def index(
        self,
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Index texts in vector database.

        Args:
            texts: List of texts to index
            metadata: Optional metadata for each text

        Returns:
            True if indexing succeeded
        """
        try:
            if not self.db:
                await self._initialize()

            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.embeddings.encode(texts),
            )

            if self.backend == "chroma":
                collection = self.db.get_or_create_collection(
                    name="trustwise-data"
                )
                collection.add(
                    ids=[f"doc_{i}" for i in range(len(texts))],
                    embeddings=embeddings.tolist(),
                    documents=texts,
                    metadatas=metadata or [{}] * len(texts),
                )
            elif self.backend == "pinecone":
                vectors = [
                    (f"doc_{i}", embedding, meta)
                    for i, (embedding, meta) in enumerate(
                        zip(embeddings, metadata or [{}] * len(texts))
                    )
                ]
                await loop.run_in_executor(None, self.db.upsert, vectors)

            logger.info(f"Indexed {len(texts)} documents")
            return True
        except Exception as e:
            logger.error(f"Indexing failed: {e}")
            return False
