"""Agent model module."""
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from app.models.base import BaseModelWithId


class AgentRole(str, Enum):
    """Agent roles in the system."""

    ECONOMIST = "economist"
    POLITICS_NEUTRAL = "politics_neutral"
    POLITICS_LEFT = "politics_left"
    POLITICS_RIGHT = "politics_right"
    HISTORIAN = "historian"
    GEOPOLITICS = "geopolitics"
    EDITOR = "editor"
    GRAPHIC_ARTIST = "graphic_artist"


class AgentMemo(BaseModelWithId):
    """Agent memo model for storing agent outputs."""

    agent_role: AgentRole
    article_id: UUID = Field(..., description="ID of the article run this memo belongs to")
    content: str = Field(..., description="The agent's analysis or contribution")
    citations: List[UUID] = Field(
        default_factory=list,
        description="List of citation IDs referenced in this memo",
    )
    visuals: List[UUID] = Field(
        default_factory=list,
        description="List of visual IDs referenced in this memo",
    )
    parent_memo_id: Optional[UUID] = Field(
        None, description="ID of the parent memo this is responding to (for reflections)"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the memo (e.g., confidence scores, bias analysis)",
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "agent_role": "economist",
                "article_id": "123e4567-e89b-12d3-a456-426614174000",
                "content": "Based on recent economic indicators...",
                "citations": [
                    "123e4567-e89b-12d3-a456-426614174001",
                    "123e4567-e89b-12d3-a456-426614174002",
                ],
                "visuals": ["123e4567-e89b-12d3-a456-426614174003"],
                "metadata": {
                    "confidence": 0.85,
                    "bias_score": 0.2,
                    "sources_quality": 0.9,
                },
            }
        } 