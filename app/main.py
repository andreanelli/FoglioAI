"""Main FastAPI application."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, web
from app.redis_client import redis_client

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
    description="Vintage newspaper-style article generator using AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(web.router, prefix="/api")


@app.get("/")
async def root() -> dict:
    """Root endpoint.

    Returns:
        dict: Basic API information and available endpoints
    """
    return {
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