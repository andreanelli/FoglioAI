"""Article model."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ArticleSection(BaseModel):
    """Article section model."""

    title: str = Field(..., description="Section title")
    content: str = Field(default="", description="Section content")
    style_notes: Optional[str] = Field(None, description="Style notes for this section")


class ArticleOutline(BaseModel):
    """Article outline model."""

    headline: str = Field(..., description="Article headline")
    subheadline: Optional[str] = Field(None, description="Article subheadline")
    sections: List[ArticleSection] = Field(
        default_factory=list, description="Article sections"
    )


class Article(BaseModel):
    """Article model."""

    id: UUID = Field(..., description="Unique identifier for the article")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Article content in markdown format")
    topic: str = Field(..., description="Topic the article is about")
    sources: List[str] = Field(default_factory=list, description="List of sources used")
    outline: Optional[ArticleOutline] = Field(None, description="Article outline")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the article was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the article was last updated"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "The Impact of AI on Global Economics",
                "content": "This article discusses the impact of AI on global economics...",
                "topic": "AI and its impact on global economics",
                "sources": ["https://example.com/article1", "https://example.com/article2"],
                "outline": {
                    "headline": "AI Revolution Reshapes Global Economic Landscape",
                    "subheadline": "Experts Predict Unprecedented Changes in Industry and Commerce",
                    "sections": [
                        {
                            "title": "Introduction",
                            "content": "The dawn of artificial intelligence...",
                            "style_notes": "Opening in classic 1920s newspaper style"
                        }
                    ]
                },
                "created_at": "2024-02-15T10:00:00",
                "updated_at": "2024-02-15T10:00:00"
            }
        } 