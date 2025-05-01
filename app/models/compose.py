"""Article composition models."""
from enum import Enum
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ComposeStatus(str, Enum):
    """Article composition status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ComposeRequest(BaseModel):
    """Article composition request."""

    topic: str = Field(..., description="Topic to write about")
    style_guide: Dict[str, str] = Field(
        default_factory=dict, description="Style guidelines to follow"
    )


class ComposeResponse(BaseModel):
    """Article composition response."""

    article_id: UUID = Field(..., description="ID of the generated article")


class ComposeStatusResponse(BaseModel):
    """Article composition status response."""

    article_id: UUID = Field(..., description="ID of the article")
    status: ComposeStatus = Field(..., description="Current status")
    error: Optional[str] = Field(None, description="Error message if failed")


class ArticleProgress(BaseModel):
    """Article generation progress."""

    article_id: UUID = Field(..., description="ID of the article")
    agent_id: str = Field(..., description="ID of the agent reporting progress")
    message: str = Field(..., description="Progress message")


class ArticleError(BaseModel):
    """Article generation error."""

    article_id: UUID = Field(..., description="ID of the article")
    error: str = Field(..., description="Error message")


class ArticleStatusResponse(BaseModel):
    """Article status response."""

    article_id: UUID = Field(..., description="ID of the article")
    status: str = Field(..., description="Current status")
    error: Optional[str] = Field(None, description="Error message if failed") 