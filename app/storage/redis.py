"""Redis storage implementation."""
import json
import logging
import zlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TypeVar
from uuid import UUID

import redis
from pydantic import BaseModel

from app.models.agent_memo import AgentMemo
from app.models.article_run import ArticleRun
from app.models.citation import Citation
from app.models.visual import Visual

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StorageError(Exception):
    """Base exception for storage-related errors."""

    pass


class RedisStorage:
    """Redis storage implementation."""

    def __init__(self, redis_client: redis.Redis) -> None:
        """Initialize the Redis storage.

        Args:
            redis_client (redis.Redis): Redis client instance
        """
        self.redis = redis_client
        self.default_ttl = timedelta(days=7)  # Default TTL for stored items

    def _generate_key(self, prefix: str, id_value: str | UUID) -> str:
        """Generate a Redis key with the given prefix and ID.

        Args:
            prefix (str): Key prefix
            id_value (str | UUID): ID value

        Returns:
            str: Generated Redis key
        """
        return f"{prefix}:{str(id_value)}"

    def _compress_data(self, data: Dict[str, Any]) -> bytes:
        """Compress data using zlib.

        Args:
            data (Dict[str, Any]): Data to compress

        Returns:
            bytes: Compressed data
        """
        json_data = json.dumps(data)
        return zlib.compress(json_data.encode())

    def _decompress_data(self, data: bytes) -> Dict[str, Any]:
        """Decompress data using zlib.

        Args:
            data (bytes): Data to decompress

        Returns:
            Dict[str, Any]: Decompressed data
        """
        json_data = zlib.decompress(data).decode()
        return json.loads(json_data)

    def _serialize_model(self, model: BaseModel) -> Dict[str, Any]:
        """Serialize a Pydantic model to a dictionary.

        Args:
            model (BaseModel): Model to serialize

        Returns:
            Dict[str, Any]: Serialized model
        """
        return json.loads(model.model_dump_json())

    def _deserialize_model(self, data: Dict[str, Any], model_class: type[T]) -> T:
        """Deserialize a dictionary to a Pydantic model.

        Args:
            data (Dict[str, Any]): Data to deserialize
            model_class (type[T]): Model class to use

        Returns:
            T: Deserialized model
        """
        return model_class.model_validate(data)

    def save_article_run(self, article_run: ArticleRun, ttl: Optional[timedelta] = None) -> None:
        """Save an article run to Redis.

        Args:
            article_run (ArticleRun): Article run to save
            ttl (Optional[timedelta], optional): Time to live. Defaults to None.

        Raises:
            StorageError: If the save operation fails
        """
        try:
            key = self._generate_key("article_run", article_run.id)
            data = self._serialize_model(article_run)
            compressed_data = self._compress_data(data)
            ttl_seconds = int(ttl.total_seconds()) if ttl else int(self.default_ttl.total_seconds())

            self.redis.setex(key, ttl_seconds, compressed_data)
            logger.debug("Saved article run %s", article_run.id)
        except Exception as e:
            logger.error("Failed to save article run %s: %s", article_run.id, e)
            raise StorageError(f"Failed to save article run {article_run.id}") from e

    def get_article_run(self, article_id: UUID) -> Optional[ArticleRun]:
        """Get an article run from Redis.

        Args:
            article_id (UUID): Article run ID

        Returns:
            Optional[ArticleRun]: Article run if found, None otherwise

        Raises:
            StorageError: If the retrieval operation fails
        """
        try:
            key = self._generate_key("article_run", article_id)
            data = self.redis.get(key)

            if data is None:
                logger.debug("Article run %s not found", article_id)
                return None

            decompressed_data = self._decompress_data(data)
            article_run = self._deserialize_model(decompressed_data, ArticleRun)
            logger.debug("Retrieved article run %s", article_id)
            return article_run
        except Exception as e:
            logger.error("Failed to get article run %s: %s", article_id, e)
            raise StorageError(f"Failed to get article run {article_id}") from e

    def save_agent_memo(
        self, memo: AgentMemo, article_id: UUID, ttl: Optional[timedelta] = None
    ) -> None:
        """Save an agent memo to Redis.

        Args:
            memo (AgentMemo): Agent memo to save
            article_id (UUID): Associated article run ID
            ttl (Optional[timedelta], optional): Time to live. Defaults to None.

        Raises:
            StorageError: If the save operation fails
        """
        try:
            # Save the memo itself
            memo_key = self._generate_key("agent_memo", memo.id)
            memo_data = self._serialize_model(memo)
            compressed_memo = self._compress_data(memo_data)
            ttl_seconds = int(ttl.total_seconds()) if ttl else int(self.default_ttl.total_seconds())

            # Save the memo ID to the article's memo list
            article_memos_key = self._generate_key("article_memos", article_id)

            with self.redis.pipeline() as pipe:
                pipe.setex(memo_key, ttl_seconds, compressed_memo)
                pipe.sadd(article_memos_key, str(memo.id))
                pipe.expire(article_memos_key, ttl_seconds)
                pipe.execute()

            logger.debug("Saved agent memo %s for article %s", memo.id, article_id)
        except Exception as e:
            logger.error("Failed to save agent memo %s: %s", memo.id, e)
            raise StorageError(f"Failed to save agent memo {memo.id}") from e

    def get_agent_memos(self, article_id: UUID) -> List[AgentMemo]:
        """Get all agent memos for an article run.

        Args:
            article_id (UUID): Article run ID

        Returns:
            List[AgentMemo]: List of agent memos

        Raises:
            StorageError: If the retrieval operation fails
        """
        try:
            article_memos_key = self._generate_key("article_memos", article_id)
            memo_ids = self.redis.smembers(article_memos_key)

            memos = []
            for memo_id in memo_ids:
                memo_key = self._generate_key("agent_memo", memo_id.decode())
                data = self.redis.get(memo_key)
                if data is not None:
                    decompressed_data = self._decompress_data(data)
                    memo = self._deserialize_model(decompressed_data, AgentMemo)
                    memos.append(memo)

            logger.debug("Retrieved %d agent memos for article %s", len(memos), article_id)
            return sorted(memos, key=lambda m: m.timestamp)
        except Exception as e:
            logger.error("Failed to get agent memos for article %s: %s", article_id, e)
            raise StorageError(f"Failed to get agent memos for article {article_id}") from e

    def save_citation(
        self, citation: Citation, article_id: UUID, ttl: Optional[timedelta] = None
    ) -> None:
        """Save a citation to Redis.

        Args:
            citation (Citation): Citation to save
            article_id (UUID): Associated article run ID
            ttl (Optional[timedelta], optional): Time to live. Defaults to None.

        Raises:
            StorageError: If the save operation fails
        """
        try:
            # Save the citation itself
            citation_key = self._generate_key("citation", citation.id)
            citation_data = self._serialize_model(citation)
            compressed_citation = self._compress_data(citation_data)
            ttl_seconds = int(ttl.total_seconds()) if ttl else int(self.default_ttl.total_seconds())

            # Save the citation ID to the article's citation list
            article_citations_key = self._generate_key("article_citations", article_id)

            with self.redis.pipeline() as pipe:
                pipe.setex(citation_key, ttl_seconds, compressed_citation)
                pipe.sadd(article_citations_key, str(citation.id))
                pipe.expire(article_citations_key, ttl_seconds)
                pipe.execute()

            logger.debug("Saved citation %s for article %s", citation.id, article_id)
        except Exception as e:
            logger.error("Failed to save citation %s: %s", citation.id, e)
            raise StorageError(f"Failed to save citation {citation.id}") from e

    def get_citations(self, article_id: UUID) -> List[Citation]:
        """Get all citations for an article run.

        Args:
            article_id (UUID): Article run ID

        Returns:
            List[Citation]: List of citations

        Raises:
            StorageError: If the retrieval operation fails
        """
        try:
            article_citations_key = self._generate_key("article_citations", article_id)
            citation_ids = self.redis.smembers(article_citations_key)

            citations = []
            for citation_id in citation_ids:
                citation_key = self._generate_key("citation", citation_id.decode())
                data = self.redis.get(citation_key)
                if data is not None:
                    decompressed_data = self._decompress_data(data)
                    citation = self._deserialize_model(decompressed_data, Citation)
                    citations.append(citation)

            logger.debug("Retrieved %d citations for article %s", len(citations), article_id)
            return sorted(citations, key=lambda c: c.publication_date or datetime.min)
        except Exception as e:
            logger.error("Failed to get citations for article %s: %s", article_id, e)
            raise StorageError(f"Failed to get citations for article {article_id}") from e

    def save_visual(
        self, visual: Visual, article_id: UUID, ttl: Optional[timedelta] = None
    ) -> None:
        """Save a visual to Redis.

        Args:
            visual (Visual): Visual to save
            article_id (UUID): Associated article run ID
            ttl (Optional[timedelta], optional): Time to live. Defaults to None.

        Raises:
            StorageError: If the save operation fails
        """
        try:
            # Save the visual itself
            visual_key = self._generate_key("visual", visual.id)
            visual_data = self._serialize_model(visual)
            compressed_visual = self._compress_data(visual_data)
            ttl_seconds = int(ttl.total_seconds()) if ttl else int(self.default_ttl.total_seconds())

            # Save the visual ID to the article's visual list
            article_visuals_key = self._generate_key("article_visuals", article_id)

            with self.redis.pipeline() as pipe:
                pipe.setex(visual_key, ttl_seconds, compressed_visual)
                pipe.sadd(article_visuals_key, str(visual.id))
                pipe.expire(article_visuals_key, ttl_seconds)
                pipe.execute()

            logger.debug("Saved visual %s for article %s", visual.id, article_id)
        except Exception as e:
            logger.error("Failed to save visual %s: %s", visual.id, e)
            raise StorageError(f"Failed to save visual {visual.id}") from e

    def get_visuals(self, article_id: UUID) -> List[Visual]:
        """Get all visuals for an article run.

        Args:
            article_id (UUID): Article run ID

        Returns:
            List[Visual]: List of visuals

        Raises:
            StorageError: If the retrieval operation fails
        """
        try:
            article_visuals_key = self._generate_key("article_visuals", article_id)
            visual_ids = self.redis.smembers(article_visuals_key)

            visuals = []
            for visual_id in visual_ids:
                visual_key = self._generate_key("visual", visual_id.decode())
                data = self.redis.get(visual_key)
                if data is not None:
                    decompressed_data = self._decompress_data(data)
                    visual = self._deserialize_model(decompressed_data, Visual)
                    visuals.append(visual)

            logger.debug("Retrieved %d visuals for article %s", len(visuals), article_id)
            return sorted(visuals, key=lambda v: v.created_at)
        except Exception as e:
            logger.error("Failed to get visuals for article %s: %s", article_id, e)
            raise StorageError(f"Failed to get visuals for article {article_id}") from e

    def delete_article_run(self, article_id: UUID) -> None:
        """Delete an article run and all associated data.

        Args:
            article_id (UUID): Article run ID

        Raises:
            StorageError: If the deletion operation fails
        """
        try:
            # Get all associated data keys
            article_key = self._generate_key("article_run", article_id)
            article_memos_key = self._generate_key("article_memos", article_id)
            article_citations_key = self._generate_key("article_citations", article_id)
            article_visuals_key = self._generate_key("article_visuals", article_id)

            # Get all memo, citation, and visual IDs
            memo_ids = self.redis.smembers(article_memos_key)
            citation_ids = self.redis.smembers(article_citations_key)
            visual_ids = self.redis.smembers(article_visuals_key)

            # Generate keys for all associated data
            memo_keys = [self._generate_key("agent_memo", id.decode()) for id in memo_ids]
            citation_keys = [self._generate_key("citation", id.decode()) for id in citation_ids]
            visual_keys = [self._generate_key("visual", id.decode()) for id in visual_ids]

            # Delete all keys in a single pipeline
            with self.redis.pipeline() as pipe:
                pipe.delete(article_key)
                pipe.delete(article_memos_key)
                pipe.delete(article_citations_key)
                pipe.delete(article_visuals_key)
                if memo_keys:
                    pipe.delete(*memo_keys)
                if citation_keys:
                    pipe.delete(*citation_keys)
                if visual_keys:
                    pipe.delete(*visual_keys)
                pipe.execute()

            logger.debug("Deleted article run %s and all associated data", article_id)
        except Exception as e:
            logger.error("Failed to delete article run %s: %s", article_id, e)
            raise StorageError(f"Failed to delete article run {article_id}") from e

    def cleanup_expired_data(self) -> None:
        """Clean up expired data from Redis.

        This is a no-op as Redis automatically removes expired keys.
        """
        pass  # Redis handles TTL expiration automatically 