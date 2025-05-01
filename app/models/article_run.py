"""Article run model."""
from datetime import datetime, UTC
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.agent_memo import AgentMemo
from app.models.citation import Citation


class ArticleRunStatus(str, Enum):
    """Article run status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ArticleRun(BaseModel):
    """Article run model."""

    id: UUID = Field(..., description="Unique identifier for the article run")
    status: ArticleRunStatus = Field(
        default=ArticleRunStatus.PENDING, description="Current status"
    )
    user_query: str = Field(..., description="Original user query")
    final_output: Optional[str] = Field(None, description="Final article content")
    citations: List[Citation] = Field(default_factory=list, description="Citations used")
    agent_memos: List[AgentMemo] = Field(
        default_factory=list, description="Agent memos during generation"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update timestamp"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed") 