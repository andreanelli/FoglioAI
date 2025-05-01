"""Article composition API endpoints."""
import logging
from typing import AsyncGenerator, Dict, Optional
from uuid import UUID
import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from sse_starlette.sse import EventSourceResponse

from app.models.article import Article
from app.models.article_run import ArticleRun
from app.models.compose import (
    ArticleError,
    ArticleProgress,
    ArticleStatusResponse,
    ComposeRequest,
    ComposeResponse,
    ComposeStatus,
    ComposeStatusResponse,
)
from app.pubsub.scratchpad import Message, MessageType
from app.services.compose import ArticleGenerationService
from app.services.template import template_renderer
from app.storage.article_run import get_article_run

logger = logging.getLogger(__name__)
router = APIRouter()

# Global service instance
service = ArticleGenerationService()

# Rate limit: 10 requests per minute
RATE_LIMIT = "10/minute"
# Timeout for article generation (5 minutes)
GENERATION_TIMEOUT = 300

# Rate limiter dependency that can be overridden in tests
def get_rate_limiter(times: int = 10, minutes: int = 1) -> RateLimiter:
    """Get rate limiter instance.

    Args:
        times (int, optional): Number of requests allowed. Defaults to 10.
        minutes (int, optional): Time window in minutes. Defaults to 1.

    Returns:
        RateLimiter: Rate limiter instance
    """
    return RateLimiter(times=times, minutes=minutes)

@router.post("/api/compose", response_model=ComposeResponse)
async def start_article_generation(
    request: ComposeRequest,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    fastapi_request: Optional[Request] = None,
) -> ComposeResponse:
    """Start article generation.

    Args:
        request (ComposeRequest): Article generation request
        rate_limiter (RateLimiter, optional): Rate limiter instance. Defaults to Depends(get_rate_limiter).
        fastapi_request (Optional[Request], optional): FastAPI request object. Defaults to None.

    Returns:
        ComposeResponse: Response with article ID

    Raises:
        HTTPException: If article generation fails to start or rate limit is exceeded
    """
    await rate_limiter(fastapi_request or "compose")  # Apply rate limiting
    try:
        article_id = await service.start_generation(request.topic, request.style_guide)
        return ComposeResponse(article_id=article_id)
    except Exception as e:
        logger.error("Failed to start article generation: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/compose/{article_id}", response_model=ArticleStatusResponse)
async def get_article_status(
    article_id: UUID,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    fastapi_request: Optional[Request] = None,
) -> ArticleStatusResponse:
    """Get article generation status.

    Args:
        article_id (UUID): ID of the article
        rate_limiter (RateLimiter, optional): Rate limiter instance. Defaults to Depends(get_rate_limiter).
        fastapi_request (Optional[Request], optional): FastAPI request object. Defaults to None.

    Returns:
        ArticleStatusResponse: Article status response

    Raises:
        HTTPException: If article not found or rate limit is exceeded
    """
    await rate_limiter(fastapi_request or "status")  # Apply rate limiting
    try:
        article_run = await get_article_run(article_id)
        if not article_run:
            raise HTTPException(status_code=404, detail="Article not found")
        return ArticleStatusResponse(
            article_id=article_id,
            status=article_run.status,
            error=article_run.error,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get article status: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/compose/{article_id}/html", response_class=HTMLResponse)
async def get_article_html(
    article_id: UUID,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    fastapi_request: Optional[Request] = None,
) -> str:
    """Get article HTML.

    Args:
        article_id (UUID): ID of the article
        rate_limiter (RateLimiter, optional): Rate limiter instance. Defaults to Depends(get_rate_limiter).
        fastapi_request (Optional[Request], optional): FastAPI request object. Defaults to None.

    Returns:
        str: Article HTML

    Raises:
        HTTPException: If article not found, not ready, or rate limit is exceeded
    """
    await rate_limiter(fastapi_request or "html")  # Apply rate limiting
    try:
        article_run = await get_article_run(article_id)
        if not article_run:
            raise HTTPException(status_code=404, detail="Article not found")
        if article_run.status != "completed":
            raise HTTPException(status_code=400, detail="Article not ready")
        return template_renderer.render_article(article_run.article)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get article HTML: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/compose/{article_id}/events")
async def subscribe_to_article_events(
    article_id: UUID,
    request: Request,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> EventSourceResponse:
    """Subscribe to article generation events.

    Args:
        article_id (UUID): ID of the article
        request (Request): FastAPI request object
        rate_limiter (RateLimiter, optional): Rate limiter instance. Defaults to Depends(get_rate_limiter).

    Returns:
        EventSourceResponse: SSE response with article events

    Raises:
        HTTPException: If the article generation times out or rate limit is exceeded
    """
    await rate_limiter(request or "events")  # Apply rate limiting

    async def event_generator() -> AsyncGenerator[Dict[str, str], None]:
        """Generate SSE events.

        Yields:
            AsyncGenerator[Dict[str, str], None]: SSE events
        """
        try:
            async with asyncio.timeout(GENERATION_TIMEOUT):
                async for message in service.subscribe_to_events(article_id):
                    if await request.is_disconnected():
                        logger.debug("Client disconnected, stopping event stream")
                        break

                    if message.type == MessageType.PROGRESS:
                        yield {
                            "event": "progress",
                            "data": ArticleProgress(
                                article_id=article_id,
                                agent_id=message.agent_id,
                                message=message.content.get("message", ""),
                            ).model_dump_json(),
                        }
                    elif message.type == MessageType.ERROR:
                        yield {
                            "event": "error",
                            "data": ArticleError(
                                article_id=article_id,
                                error=message.content.get("error", "Unknown error"),
                            ).model_dump_json(),
                        }
                    elif message.type == MessageType.COMPLETED:
                        yield {
                            "event": "completed",
                            "data": ComposeResponse(
                                article_id=article_id,
                            ).model_dump_json(),
                        }
        except asyncio.TimeoutError:
            logger.error("Article generation timed out for article %s", article_id)
            yield {
                "event": "error",
                "data": ArticleError(
                    article_id=article_id,
                    error="Article generation timed out",
                ).model_dump_json(),
            }

    return EventSourceResponse(event_generator()) 