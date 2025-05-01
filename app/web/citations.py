"""Citation manager module."""
import json
import logging
from typing import Dict, List, Optional
from uuid import UUID

import redis
from pydantic import AnyHttpUrl

from app.models.citation import Citation

logger = logging.getLogger(__name__)


class CitationError(Exception):
    """Base exception for citation-related errors."""

    pass


class CitationNotFoundError(CitationError):
    """Exception raised when a citation is not found."""

    pass


class CitationManager:
    """Manager for handling citations with Redis storage."""

    def __init__(self, redis_client: redis.Redis) -> None:
        """Initialize the citation manager.

        Args:
            redis_client (redis.Redis): Redis client instance
        """
        self.redis = redis_client
        self.citation_key_prefix = "citation:"
        self.article_citations_key_prefix = "article:citations:"

    def _get_citation_key(self, citation_id: UUID) -> str:
        """Generate Redis key for a citation.

        Args:
            citation_id (UUID): Citation ID

        Returns:
            str: Redis key
        """
        return f"{self.citation_key_prefix}{str(citation_id)}"

    def _get_article_citations_key(self, article_id: UUID) -> str:
        """Generate Redis key for an article's citations.

        Args:
            article_id (UUID): Article ID

        Returns:
            str: Redis key
        """
        return f"{self.article_citations_key_prefix}{str(article_id)}"

    def create_citation(self, url: AnyHttpUrl, content: Dict[str, str], excerpt: str) -> Citation:
        """Create a new citation.

        Args:
            url (AnyHttpUrl): URL of the source
            content (Dict[str, str]): Content metadata (title, author, etc.)
            excerpt (str): The specific text excerpt used

        Returns:
            Citation: Created citation object

        Raises:
            CitationError: If citation creation fails
        """
        try:
            citation = Citation(
                url=url,
                title=content.get("title", str(url)),
                author=content.get("author"),
                publication_date=content.get("publication_date"),
                excerpt=excerpt,
            )

            # Store in Redis
            citation_key = self._get_citation_key(citation.id)
            self.redis.set(
                citation_key,
                citation.model_dump_json(),
                ex=86400,  # 24 hours TTL
            )

            return citation
        except Exception as e:
            logger.error(f"Failed to create citation: {e}")
            raise CitationError(f"Failed to create citation: {e}") from e

    def get_citation(self, citation_id: UUID) -> Optional[Citation]:
        """Retrieve a citation by ID.

        Args:
            citation_id (UUID): Citation ID

        Returns:
            Optional[Citation]: Citation object if found, None otherwise

        Raises:
            CitationNotFoundError: If citation is not found
        """
        try:
            citation_key = self._get_citation_key(citation_id)
            citation_data = self.redis.get(citation_key)

            if not citation_data:
                raise CitationNotFoundError(f"Citation {citation_id} not found")

            return Citation.model_validate_json(citation_data)
        except CitationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve citation {citation_id}: {e}")
            raise CitationError(f"Failed to retrieve citation: {e}") from e

    def get_citations_by_article(self, article_id: UUID) -> List[Citation]:
        """Get all citations for an article.

        Args:
            article_id (UUID): Article ID

        Returns:
            List[Citation]: List of citations

        Raises:
            CitationError: If retrieval fails
        """
        try:
            article_citations_key = self._get_article_citations_key(article_id)
            citation_ids = self.redis.smembers(article_citations_key)

            citations = []
            for citation_id in citation_ids:
                try:
                    citation = self.get_citation(UUID(citation_id.decode()))
                    if citation:
                        citations.append(citation)
                except CitationNotFoundError:
                    # Skip citations that no longer exist
                    continue

            return citations
        except Exception as e:
            logger.error(f"Failed to retrieve citations for article {article_id}: {e}")
            raise CitationError(f"Failed to retrieve citations: {e}") from e

    def update_citation(self, citation: Citation) -> None:
        """Update an existing citation.

        Args:
            citation (Citation): Citation object to update

        Raises:
            CitationNotFoundError: If citation doesn't exist
            CitationError: If update fails
        """
        try:
            citation_key = self._get_citation_key(citation.id)
            if not self.redis.exists(citation_key):
                raise CitationNotFoundError(f"Citation {citation.id} not found")

            citation.update_timestamp()
            self.redis.set(
                citation_key,
                citation.model_dump_json(),
                ex=86400,  # 24 hours TTL
            )
        except CitationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to update citation {citation.id}: {e}")
            raise CitationError(f"Failed to update citation: {e}") from e

    def add_citation_to_article(self, article_id: UUID, citation_id: UUID) -> None:
        """Associate a citation with an article.

        Args:
            article_id (UUID): Article ID
            citation_id (UUID): Citation ID

        Raises:
            CitationNotFoundError: If citation doesn't exist
            CitationError: If association fails
        """
        try:
            # Verify citation exists
            if not self.redis.exists(self._get_citation_key(citation_id)):
                raise CitationNotFoundError(f"Citation {citation_id} not found")

            article_citations_key = self._get_article_citations_key(article_id)
            self.redis.sadd(article_citations_key, str(citation_id))
            # Set TTL for article citations set
            self.redis.expire(article_citations_key, 86400)  # 24 hours
        except CitationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to add citation {citation_id} to article {article_id}: {e}")
            raise CitationError(f"Failed to add citation to article: {e}") from e

    def remove_citation_from_article(self, article_id: UUID, citation_id: UUID) -> None:
        """Remove a citation's association with an article.

        Args:
            article_id (UUID): Article ID
            citation_id (UUID): Citation ID

        Raises:
            CitationError: If removal fails
        """
        try:
            article_citations_key = self._get_article_citations_key(article_id)
            self.redis.srem(article_citations_key, str(citation_id))
        except Exception as e:
            logger.error(f"Failed to remove citation {citation_id} from article {article_id}: {e}")
            raise CitationError(f"Failed to remove citation from article: {e}") from e

    def delete_citation(self, citation_id: UUID) -> None:
        """Delete a citation.

        Args:
            citation_id (UUID): Citation ID

        Raises:
            CitationNotFoundError: If citation doesn't exist
            CitationError: If deletion fails
        """
        try:
            citation_key = self._get_citation_key(citation_id)
            if not self.redis.exists(citation_key):
                raise CitationNotFoundError(f"Citation {citation_id} not found")

            self.redis.delete(citation_key)
        except CitationNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete citation {citation_id}: {e}")
            raise CitationError(f"Failed to delete citation: {e}") from e 