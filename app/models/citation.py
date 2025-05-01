"""Citation model module."""
from datetime import datetime
from typing import Optional

from pydantic import AnyHttpUrl, Field

from app.models.base import BaseModelWithId


class Citation(BaseModelWithId):
    """Citation model for tracking sources."""

    url: AnyHttpUrl
    title: str
    author: Optional[str] = None
    publication_date: Optional[datetime] = None
    excerpt: str = Field(..., description="The specific text excerpt used from this source")
    accessed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "url": "https://example.com/article",
                "title": "Example Article",
                "author": "John Doe",
                "publication_date": "2024-03-01T12:00:00Z",
                "excerpt": "This is a relevant excerpt from the article...",
                "accessed_at": "2024-03-01T14:30:00Z",
            }
        } 