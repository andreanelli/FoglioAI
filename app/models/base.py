"""Base models module."""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ArticleStatus(str, Enum):
    """Article run status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BaseModelWithId(BaseModel):
    """Base model with ID and timestamps."""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            UUID: str,
            datetime: lambda dt: dt.isoformat(),
        } 