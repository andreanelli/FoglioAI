"""Main FastAPI application module."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.redis_client import redis_client

# Load settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events.

    Args:
        app (FastAPI): FastAPI application instance

    Yields:
        AsyncGenerator[None, None]: Async context manager
    """
    yield
    # Cleanup resources on shutdown
    redis_client.close()


# Initialize FastAPI app
app = FastAPI(
    title="FoglioAI",
    description="A vintage newspaper-style article generator powered by AI agents",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> JSONResponse:
    """Root endpoint.

    Returns:
        JSONResponse: Basic API information and available endpoints
    """
    return JSONResponse(
        content={
            "name": "FoglioAI API",
            "description": "A vintage newspaper-style article generator powered by AI agents",
            "version": "0.1.0",
            "available_endpoints": [
                {
                    "path": "/",
                    "description": "This information",
                },
                {
                    "path": "/health",
                    "description": "Health check endpoint",
                },
                {
                    "path": "/docs",
                    "description": "API documentation (Swagger UI)",
                },
                {
                    "path": "/redoc",
                    "description": "Alternative API documentation (ReDoc)",
                },
            ],
        }
    )


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint.

    Returns:
        JSONResponse: Service status information
    """
    # Check Redis connection
    redis_status = "healthy" if redis_client.check_connection() else "unhealthy"
    is_healthy = redis_status == "healthy"

    response = {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "foglioai",
        "version": "0.1.0",
        "environment": settings.environment,
        "dependencies": {
            "redis": {
                "status": redis_status,
                "host": settings.redis_host,
                "port": settings.redis_port,
            }
        },
    }

    return JSONResponse(
        content=response,
        status_code=status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    ) 