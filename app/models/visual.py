"""Visual model."""
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class VisualType(str, Enum):
    """Visual type."""

    CHART = "chart"
    IMAGE = "image"


class Visual(BaseModel):
    """Visual model."""

    id: UUID = Field(default_factory=uuid4, description="Unique ID")
    type: VisualType = Field(..., description="Type of visual")
    source_data: Dict = Field(
        ..., description="Source data or prompt used to generate the visual"
    )
    generated_content: str = Field(
        ..., description="Generated content (base64 or URL)"
    )
    caption: str = Field(..., description="Visual caption")
    alt_text: str = Field(..., description="Alt text for accessibility")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    width: Optional[int] = Field(None, description="Visual width in pixels")
    height: Optional[int] = Field(None, description="Visual height in pixels")
    mime_type: str = Field(
        default="image/png", description="MIME type of the visual"
    )
    metadata: Dict = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "type": "image",
                "source": {
                    "prompt": "A vintage black and white photograph of a bustling city street in the 1920s"
                },
                "content": "data:image/png;base64,...</base64-data>",
                "caption": "New York City's Broadway, circa 1925",
                "alt_text": "Black and white photograph showing cars and pedestrians on Broadway",
                "width": 800,
                "height": 600,
                "format": "png",
            }
        } 