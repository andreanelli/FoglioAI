"""Agent memo model."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.agent import AgentRole
from app.models.citation import Citation


class AgentMemo(BaseModel):
    """Agent memo model."""

    id: UUID = Field(default_factory=uuid4, description="Unique ID")
    agent_name: str = Field(..., description="Name of the agent")
    agent_role: AgentRole = Field(..., description="Role of the agent")
    article_id: UUID = Field(..., description="ID of the article run this memo belongs to")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    content: str = Field(..., description="Memo content")
    citations: List[Citation] = Field(
        default_factory=list, description="Citations used in the memo"
    )
    parent_memo_id: Optional[UUID] = Field(
        None, description="ID of the parent memo (for reflection responses)"
    )
    is_reflection: bool = Field(
        default=False, description="Whether this memo is a reflection on another memo"
    )
    confidence_score: float = Field(
        default=1.0,
        description="Agent's confidence in the memo content (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    ) 