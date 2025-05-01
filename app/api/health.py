"""Health check endpoints."""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.redis_client import redis_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint.

    Returns:
        JSONResponse: Service status information
    """
    settings = get_settings()
    
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