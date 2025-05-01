"""Web retrieval API endpoints."""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AnyHttpUrl, BaseModel, Field
from redis import Redis

from app.config import get_redis_client
from app.models.citation import Citation
from app.web import (
    CitationError,
    CitationManager,
    CitationNotFoundError,
    ContentExtractor,
    ExtractionError,
    FetchError,
    WebCache,
    WebFetcher,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/web", tags=["web"])


class WebFetchRequest(BaseModel):
    """Request model for web content fetching."""

    url: AnyHttpUrl = Field(..., description="URL to fetch content from")
    force_refresh: bool = Field(
        False, description="Force refresh the cache and fetch new content"
    )


class WebFetchResponse(BaseModel):
    """Response model for web content fetching."""

    url: AnyHttpUrl = Field(..., description="Source URL")
    title: str = Field(..., description="Article title")
    author: Optional[str] = Field(None, description="Article author")
    content: str = Field(..., description="Extracted article content")
    citation: Citation = Field(..., description="Generated citation")


class CitationResponse(BaseModel):
    """Response model for citation endpoints."""

    citations: List[Citation] = Field(..., description="List of citations")


def get_web_fetcher(redis: Redis = Depends(get_redis_client)) -> WebFetcher:
    """Get WebFetcher instance.

    Args:
        redis (Redis, optional): Redis client. Defaults to Depends(get_redis_client).

    Returns:
        WebFetcher: WebFetcher instance
    """
    return WebFetcher()


def get_content_extractor() -> ContentExtractor:
    """Get ContentExtractor instance.

    Returns:
        ContentExtractor: ContentExtractor instance
    """
    return ContentExtractor()


def get_web_cache(redis: Redis = Depends(get_redis_client)) -> WebCache:
    """Get WebCache instance.

    Args:
        redis (Redis, optional): Redis client. Defaults to Depends(get_redis_client).

    Returns:
        WebCache: WebCache instance
    """
    return WebCache(redis)


def get_citation_manager(redis: Redis = Depends(get_redis_client)) -> CitationManager:
    """Get CitationManager instance.

    Args:
        redis (Redis, optional): Redis client. Defaults to Depends(get_redis_client).

    Returns:
        CitationManager: CitationManager instance
    """
    return CitationManager(redis)


@router.post("/fetch", response_model=WebFetchResponse)
async def fetch_web_content(
    request: WebFetchRequest,
    web_fetcher: WebFetcher = Depends(get_web_fetcher),
    content_extractor: ContentExtractor = Depends(get_content_extractor),
    web_cache: WebCache = Depends(get_web_cache),
    citation_manager: CitationManager = Depends(get_citation_manager),
) -> WebFetchResponse:
    """Fetch and extract content from a web URL.

    Args:
        request (WebFetchRequest): Request parameters
        web_fetcher (WebFetcher, optional): WebFetcher instance. Defaults to Depends(get_web_fetcher).
        content_extractor (ContentExtractor, optional): ContentExtractor instance. Defaults to Depends(get_content_extractor).
        web_cache (WebCache, optional): WebCache instance. Defaults to Depends(get_web_cache).
        citation_manager (CitationManager, optional): CitationManager instance. Defaults to Depends(get_citation_manager).

    Returns:
        WebFetchResponse: Fetched and extracted content with citation

    Raises:
        HTTPException: If content fetching or extraction fails
    """
    try:
        # Check cache first
        if not request.force_refresh:
            cached_content = web_cache.get_cached_content(str(request.url))
            if cached_content:
                return WebFetchResponse(**cached_content)

        # Fetch and extract content
        html = web_fetcher.fetch_url(str(request.url))
        extracted = content_extractor.extract_article(html, str(request.url))

        # Create citation
        citation = citation_manager.create_citation(
            url=request.url,
            content=extracted,
            excerpt=extracted["content"][:500],  # Use first 500 chars as excerpt
        )

        response_data = {
            "url": request.url,
            "title": extracted["title"],
            "author": extracted.get("author"),
            "content": extracted["content"],
            "citation": citation,
        }

        # Cache the response
        web_cache.cache_content(str(request.url), response_data)

        return WebFetchResponse(**response_data)

    except (FetchError, ExtractionError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch content from {request.url}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch content")


@router.get("/citations/{article_id}", response_model=CitationResponse)
async def get_article_citations(
    article_id: UUID,
    citation_manager: CitationManager = Depends(get_citation_manager),
) -> CitationResponse:
    """Get all citations for an article.

    Args:
        article_id (UUID): Article ID
        citation_manager (CitationManager, optional): CitationManager instance. Defaults to Depends(get_citation_manager).

    Returns:
        CitationResponse: List of citations

    Raises:
        HTTPException: If retrieving citations fails
    """
    try:
        citations = citation_manager.get_citations_by_article(article_id)
        return CitationResponse(citations=citations)
    except CitationError as e:
        logger.error(f"Failed to get citations for article {article_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve citations")


@router.get("/citation/{citation_id}", response_model=Citation)
async def get_citation(
    citation_id: UUID,
    citation_manager: CitationManager = Depends(get_citation_manager),
) -> Citation:
    """Get a specific citation.

    Args:
        citation_id (UUID): Citation ID
        citation_manager (CitationManager, optional): CitationManager instance. Defaults to Depends(get_citation_manager).

    Returns:
        Citation: Citation object

    Raises:
        HTTPException: If citation is not found or retrieval fails
    """
    try:
        citation = citation_manager.get_citation(citation_id)
        if not citation:
            raise HTTPException(status_code=404, detail="Citation not found")
        return citation
    except CitationNotFoundError:
        raise HTTPException(status_code=404, detail="Citation not found")
    except CitationError as e:
        logger.error(f"Failed to get citation {citation_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve citation") 