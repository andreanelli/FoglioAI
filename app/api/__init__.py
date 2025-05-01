"""API package."""
from app.api.compose import router as compose
from app.api.health import router as health
from app.api.web import router as web

__all__ = ["compose", "health", "web"] 