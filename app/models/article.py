"""Article model module."""
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from app.models.agent import AgentRole
from app.models.base import ArticleStatus, BaseModelWithId


class ArticleRun(BaseModelWithId):
    """Article run model for managing article generation."""

    status: ArticleStatus = Field(default=ArticleStatus.PENDING)
    query: str = Field(..., description="User's original query or topic")
    output: Optional[str] = Field(None, description="Final generated article content")
    html_output: Optional[str] = Field(None, description="Final article content in HTML format")
    memos: List[UUID] = Field(
        default_factory=list,
        description="List of agent memo IDs in this article run",
    )
    citations: List[UUID] = Field(
        default_factory=list,
        description="List of citation IDs used in this article",
    )
    visuals: List[UUID] = Field(
        default_factory=list,
        description="List of visual IDs used in this article",
    )
    agent_assignments: Dict[AgentRole, bool] = Field(
        default_factory=dict,
        description="Map of agent roles to their completion status",
    )
    error: Optional[str] = Field(None, description="Error message if status is FAILED")
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the article run",
    )

    @field_validator("agent_assignments")
    @classmethod
    def validate_agent_assignments(cls, v: Dict[AgentRole, bool]) -> Dict[AgentRole, bool]:
        """Ensure all required agents are assigned.

        Args:
            v (Dict[AgentRole, bool]): Agent assignments map

        Returns:
            Dict[AgentRole, bool]: Validated agent assignments
        """
        # Initialize with all agents as not completed
        default_assignments = {role: False for role in AgentRole}
        default_assignments.update(v)
        return default_assignments

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "status": "in_progress",
                "query": "Analyze the impact of AI on global economics in 2024",
                "memos": [
                    "123e4567-e89b-12d3-a456-426614174001",
                    "123e4567-e89b-12d3-a456-426614174002",
                ],
                "citations": [
                    "123e4567-e89b-12d3-a456-426614174003",
                    "123e4567-e89b-12d3-a456-426614174004",
                ],
                "visuals": ["123e4567-e89b-12d3-a456-426614174005"],
                "agent_assignments": {
                    "economist": True,
                    "politics_neutral": False,
                    "editor": False,
                },
                "metadata": {
                    "estimated_completion_time": "2024-03-01T15:30:00Z",
                    "word_count": 1200,
                    "complexity_score": 0.75,
                },
            }
        } 