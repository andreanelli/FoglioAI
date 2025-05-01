"""Article run storage module."""
import logging
from datetime import timedelta
from typing import Optional
from uuid import UUID

from app.models.article_run import ArticleRun
from app.redis_client import redis_client
from app.storage.redis import RedisStorage

logger = logging.getLogger(__name__)

# Initialize Redis storage
storage = RedisStorage(redis_client.client)


def save_article_run(article_run: ArticleRun, ttl: Optional[timedelta] = None) -> None:
    """Save an article run to storage.

    Args:
        article_run (ArticleRun): Article run to save
        ttl (Optional[timedelta], optional): Time to live. Defaults to None.

    Raises:
        StorageError: If the save operation fails
    """
    storage.save_article_run(article_run, ttl)


def get_article_run(article_id: UUID) -> ArticleRun:
    """Get an article run from storage.

    Args:
        article_id (UUID): Article run ID

    Returns:
        ArticleRun: Article run

    Raises:
        StorageError: If the retrieval operation fails
        ValueError: If the article run does not exist
    """
    article_run = storage.get_article_run(article_id)
    if article_run is None:
        # Create a new article run if it doesn't exist
        article_run = ArticleRun(
            id=article_id,
            status="initialized",
            agent_outputs={},
            citations=[],
            visuals=[],
            errors=[],
            metadata={},
        )
        save_article_run(article_run)
        logger.info("Created new article run %s", article_id)

    return article_run


def delete_article_run(article_id: UUID) -> None:
    """Delete an article run and all associated data.

    Args:
        article_id (UUID): Article run ID

    Raises:
        StorageError: If the deletion operation fails
    """
    storage.delete_article_run(article_id)


def get_recent_article_runs(limit: int = 5) -> list:
    """Get recent article runs.

    Args:
        limit (int, optional): Maximum number of articles to return. Defaults to 5.

    Returns:
        list: List of recent article runs
    """
    # To be implemented based on the existing storage system
    # This placeholder implementation will need to be replaced with actual Redis queries
    # based on how article runs are stored

    # Example implementation using Redis:
    # redis_client = get_redis_client()
    # article_keys = redis_client.keys("article:*")
    # articles = []
    
    # for key in article_keys[:limit]:
    #     article_data = redis_client.json().get(key)
    #     if article_data and article_data.get("status") == "completed":
    #         articles.append(ArticleRun(**article_data))
    
    # Sort by created_at descending
    # articles.sort(key=lambda x: x.created_at, reverse=True)
    
    # Return at most 'limit' articles
    # return articles[:limit]
    
    # For now, return an empty list to avoid errors
    return [] 